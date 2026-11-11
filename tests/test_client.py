import json
import unittest
from email.message import Message
from urllib import error

from cosmicjs import Bucket, CosmicError


class Response:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ClientTests(unittest.TestCase):
    def opener(self, body):
        seen = []

        def open_request(req, timeout=30):
            seen.append(req)
            return Response(body)

        open_request.seen = seen
        return open_request

    def test_find_encodes_the_query(self):
        opener = self.opener(b'{"objects":[{"id":"1"}]}')
        bucket = Bucket("my-bucket", read_key="rk", opener=opener)
        result = bucket.find({"type": "posts"}, props=["title", "slug"], limit=2)
        req = opener.seen[0]
        self.assertEqual(req.get_method(), "GET")
        self.assertIn("/buckets/my-bucket/objects?", req.full_url)
        self.assertIn("read_key=rk", req.full_url)
        self.assertIn("query=%7B%22type%22%3A%22posts%22%7D", req.full_url)
        self.assertIn("props=title%2Cslug", req.full_url)
        self.assertIn("limit=2", req.full_url)
        self.assertEqual(result["objects"][0]["id"], "1")
        self.assertIsNone(req.get_header("Authorization"))

    def test_insert_sends_the_write_key(self):
        opener = self.opener(b'{"object":{"id":"abc"}}')
        bucket = Bucket("my-bucket", write_key="wk", opener=opener)
        created = bucket.insert_one({"title": "Hello", "type": "posts"})
        req = opener.seen[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer wk")
        self.assertEqual(json.loads(req.data.decode())["title"], "Hello")
        self.assertEqual(created["object"]["id"], "abc")

    def test_write_requires_a_key(self):
        bucket = Bucket("my-bucket", read_key="rk", opener=self.opener(b"{}"))
        with self.assertRaises(ValueError):
            bucket.insert_one({"title": "Hello", "type": "posts"})

    def test_http_error_raises(self):
        def open_request(req, timeout=30):
            raise error.HTTPError(
                req.full_url,
                401,
                "no",
                Message(),
                _Body(b'{"message":"bad key"}'),
            )

        bucket = Bucket("my-bucket", read_key="rk", opener=open_request)
        with self.assertRaises(CosmicError) as caught:
            bucket.find({"type": "posts"})
        self.assertEqual(caught.exception.status, 401)
        self.assertEqual(caught.exception.payload["message"], "bad key")


class _Body:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data

    def close(self):
        return None


if __name__ == "__main__":
    unittest.main()

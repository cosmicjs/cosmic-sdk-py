"""Small client for the Cosmic content API.

Reads and writes objects at https://api.cosmicjs.com/v3. Media upload is a
different host and is not wrapped here.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Sequence, Union
from urllib import error, parse, request

Props = Union[str, Sequence[str]]


class CosmicError(Exception):
    def __init__(self, status: int, payload: Any):
        self.status = status
        self.payload = payload
        super().__init__(f"HTTP {status}: {payload}")


class Bucket:
    def __init__(
        self,
        bucket_slug: str,
        read_key: Optional[str] = None,
        write_key: Optional[str] = None,
        api_url: str = "https://api.cosmicjs.com/v3",
        opener=None,
    ):
        if not bucket_slug:
            raise ValueError("bucket_slug is required")
        self.bucket_slug = bucket_slug
        self.read_key = read_key
        self.write_key = write_key
        self.api_url = api_url.rstrip("/")
        self._opener = opener or request.urlopen

    def find(
        self,
        query: Optional[Mapping[str, Any]] = None,
        *,
        props: Optional[Props] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        depth: Optional[int] = None,
        locale: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        params: dict[str, str] = {}
        if self.read_key:
            params["read_key"] = self.read_key
        body = dict(query or {})
        if locale:
            body["locale"] = locale
        if body:
            params["query"] = json.dumps(body, separators=(",", ":"))
        if props:
            params["props"] = props if isinstance(props, str) else ",".join(props)
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)
        if depth is not None:
            params["depth"] = str(depth)
        if status:
            params["status"] = status
        return self._request("GET", "/objects", params)

    def find_one(self, query: Mapping[str, Any], **kwargs) -> dict:
        data = self.find(query, limit=1, **kwargs)
        objects = data.get("objects") or []
        return {"object": objects[0] if objects else None}

    def insert_one(self, obj: Mapping[str, Any]) -> dict:
        return self._request("POST", "/objects", body=dict(obj), write=True)

    def update_one(self, object_id: str, updates: Mapping[str, Any]) -> dict:
        return self._request(
            "PATCH",
            f"/objects/{parse.quote(object_id)}",
            body=dict(updates),
            write=True,
        )

    def delete_one(self, object_id: str, trigger_webhook: bool = False) -> dict:
        params = {"trigger_webhook": "true"} if trigger_webhook else None
        return self._request(
            "DELETE",
            f"/objects/{parse.quote(object_id)}",
            params,
            write=True,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, str]] = None,
        body: Optional[Mapping[str, Any]] = None,
        write: bool = False,
    ) -> dict:
        query = parse.urlencode(params or {})
        url = f"{self.api_url}/buckets/{parse.quote(self.bucket_slug)}{path}"
        if query:
            url = f"{url}?{query}"
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if write:
            if not self.write_key:
                raise ValueError("write_key is required for this call")
            headers["Authorization"] = f"Bearer {self.write_key}"
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener(req, timeout=30) as response:
                raw = response.read().decode()
        except error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"message": raw}
            raise CosmicError(exc.code, payload) from None
        if not raw:
            return {}
        return json.loads(raw)

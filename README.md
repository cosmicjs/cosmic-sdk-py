# Cosmic Python SDK

Python client for the [Cosmic](https://www.cosmicjs.com) content API. It wraps object reads and writes on `https://api.cosmicjs.com/v3`. There is no dependency beyond the Python standard library.

The PyPI project named `cosmic-sdk` is unrelated. This package is `cosmicjs`.

```bash
pip install git+https://github.com/cosmicjs/cosmic-sdk-py.git
```

```python
import os
from cosmicjs import Bucket

cosmic = Bucket(
    bucket_slug=os.environ["BUCKET_SLUG"],
    read_key=os.environ["BUCKET_READ_KEY"],
    write_key=os.environ["BUCKET_WRITE_KEY"],
)

posts = cosmic.find({"type": "posts"}, props="title,slug,metadata", limit=20)
post = cosmic.find_one({"type": "posts", "slug": "hello"})
created = cosmic.insert_one({
    "title": "Hello",
    "type": "posts",
    "metadata": {"content": "Body"},
})
cosmic.update_one(created["object"]["id"], {"title": "Hello again"})
cosmic.delete_one(created["object"]["id"])
```

`find` accepts `props`, `limit`, `skip`, `depth`, `locale`, and `status`. Writes raise `ValueError` when `write_key` is missing, and `CosmicError` when the API returns an HTTP error.

Media upload is not included. The upload host and the `media` form field are documented at https://www.cosmicjs.com/docs/api/media.md.

From a checkout, install the working tree and run the tests:

```bash
pip install -e .
PYTHONPATH=src python -m unittest discover -s tests
```

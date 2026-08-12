import io
import json
import unittest
from urllib.error import HTTPError

from arbs.adapters import KalshiPublicClient, PolymarketPublicClient
from arbs.adapters.http import ApiError, JsonHttpClient


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return self.payload


class AdapterTests(unittest.TestCase):
    def test_kalshi_market_request(self):
        seen = []
        http = JsonHttpClient(opener=lambda request, **_: seen.append(request.full_url) or FakeResponse({"markets": []}))
        result = KalshiPublicClient(http).list_markets(limit=3)
        self.assertEqual(result.data, {"markets": []})
        self.assertIn("limit=3", seen[0])
        self.assertIn("status=open", seen[0])

    def test_polymarket_uses_keyset_endpoint(self):
        seen = []
        http = JsonHttpClient(opener=lambda request, **_: seen.append(request.full_url) or FakeResponse({"markets": []}))
        PolymarketPublicClient(http).list_markets(limit=3)
        self.assertIn("/markets/keyset?", seen[0])
        self.assertIn("active=true", seen[0])

    def test_retries_retryable_status(self):
        calls = []

        def opener(request, **_):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 503, "unavailable", {}, io.BytesIO())
            return FakeResponse({"ok": True})

        response = JsonHttpClient(opener=opener, sleeper=lambda _: None).get("https://example.test", "/x")
        self.assertTrue(response.data["ok"])
        self.assertEqual(len(calls), 2)

    def test_does_not_retry_client_error(self):
        def opener(request, **_):
            raise HTTPError(request.full_url, 404, "missing", {}, io.BytesIO())

        with self.assertRaises(ApiError):
            JsonHttpClient(opener=opener, sleeper=lambda _: None).get("https://example.test", "/x")


if __name__ == "__main__":
    unittest.main()


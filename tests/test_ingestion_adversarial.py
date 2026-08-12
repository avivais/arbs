import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from arbs.adapters.http import ApiError, JsonHttpClient
from arbs.ingest import main as ingest_main
from arbs.ingestion.schema import SnapshotValidationError, validate_snapshot


class Response:
    status = 200
    def __init__(self, body: bytes): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit=-1): return self.body if limit < 0 else self.body[:limit]


class HttpBoundsTests(unittest.TestCase):
    def test_invalid_bounds(self):
        with self.assertRaises(ValueError): JsonHttpClient(max_attempts=0)
        with self.assertRaises(ValueError): JsonHttpClient(timeout_seconds=0)
        with self.assertRaises(ValueError): JsonHttpClient(max_response_bytes=0)

    def test_oversized_and_invalid_json_do_not_retry(self):
        for body, limit in ((b"{}x", 2), (b"no", 10)):
            calls=[]
            def opener(*a, **k): calls.append(1); return Response(body)
            with self.assertRaises(ApiError): JsonHttpClient(opener=opener, max_response_bytes=limit).get("https://x", "/y")
            self.assertEqual(len(calls), 1)

    def test_retry_after_is_capped_and_attempts_exact(self):
        calls=[]; sleeps=[]; headers=Message(); headers["Retry-After"]="999"
        def opener(*a, **k):
            calls.append(1)
            if len(calls)<3: raise HTTPError("https://x/y",429,"rate",headers,None)
            return Response(b"{}")
        JsonHttpClient(opener=opener,sleeper=sleeps.append,max_attempts=3,max_retry_after_seconds=2).get("https://x","/y")
        self.assertEqual(len(calls),3); self.assertEqual(sleeps,[2,2])

    def test_transport_error_is_sanitized(self):
        def opener(*a, **k): raise URLError("secret-response-body")
        with self.assertRaises(ApiError) as ctx: JsonHttpClient(opener=opener,max_attempts=1).get("https://x","/y")
        self.assertNotIn("secret-response-body",str(ctx.exception))


class CliFailureTests(unittest.TestCase):
    def test_one_venue_failure_preserves_other_and_returns_partial(self):
        class K:
            def list_series(self, **kwargs): raise RuntimeError("kalshi down")
        class P:
            def list_sports(self):
                from arbs.adapters.http import JsonResponse
                return JsonResponse([],"https://poly.test",200,1,1)
        with tempfile.TemporaryDirectory() as temp, patch("arbs.ingest.KalshiPublicClient",return_value=K()), patch("arbs.ingest.PolymarketPublicClient",return_value=P()), redirect_stdout(io.StringIO()):
            code=ingest_main(["--output",temp]); self.assertEqual(code,3)  # no records => failed
            path=next(Path(temp).glob("*.jsonl")); self.assertEqual(validate_snapshot(path)["status"],"failed")

    def test_later_failure_preserves_valid_records(self):
        from arbs.adapters.http import JsonResponse
        class K:
            def list_series(self, **kwargs): return JsonResponse({"series":[{"ticker":"S"}],"cursor":""},"https://k",200,1,1)
            def list_series_markets(self,*a,**k): return JsonResponse({"markets":[{"ticker":"S-M"}],"cursor":""},"https://k",200,1,1)
        class P:
            def list_sports(self): raise RuntimeError("poly down")
        with tempfile.TemporaryDirectory() as temp, patch("arbs.ingest.KalshiPublicClient",return_value=K()), patch("arbs.ingest.PolymarketPublicClient",return_value=P()), redirect_stdout(io.StringIO()):
            code=ingest_main(["--output",temp]); self.assertEqual(code,2)
            result=validate_snapshot(next(Path(temp).glob("*.jsonl"))); self.assertEqual(result,{"schema_version":1,"status":"partial","records":2})


if __name__ == "__main__": unittest.main()

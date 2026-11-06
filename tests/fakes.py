"""Test doubles: scripted HTTP, fixed clock and ready-made services."""

import json
import os
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from woa.net import Response  # noqa: E402
from woa.services import Services  # noqa: E402
from woa.store import MemoryStore  # noqa: E402

LWA_CLIENT_ID = "amzn1.application-oa2-client.woa"
USER_ID = "amzn1.account.TESTUSER"
NOW = 1_800_000_000
DEVICE = {"id": "woa-0123456789abcdef", "name": "Gaming PC", "mac": "C8-7F-54-0B-30-C5",
          "created_at": NOW - 100}
EU = "https://api.eu.amazonalexa.com/v3/events"
NA = "https://api.amazonalexa.com/v3/events"


def load_event(name):
    with open(os.path.join(ROOT, "tests", "events", name)) as f:
        return json.load(f)


class FakeHttp:
    """Answers tokeninfo/token calls; gateway answers come from a queue per URL."""

    def __init__(self):
        self.calls = []
        self.gateway = {}  # url -> list of Response
        self.token_status = 200
        self.tokens = {"user-token": {"user_id": USER_ID, "aud": LWA_CLIENT_ID, "exp": 3000}}

    def queue(self, url, *responses):
        self.gateway.setdefault(url, []).extend(responses)

    def request(self, method, url, headers=None, json_body=None, form=None):
        self.calls.append({"method": method, "url": url, "headers": headers or {},
                           "json": json_body, "form": form})
        if url.startswith("https://api.amazon.com/auth/o2/tokeninfo"):
            token = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["access_token"][0]
            info = self.tokens.get(token)
            return Response(200, info) if info else Response(400, {"error": "invalid_token"})
        if url == "https://api.amazon.com/auth/o2/token":
            if self.token_status != 200:
                return Response(self.token_status, {"error": "invalid_grant"})
            n = sum(1 for c in self.calls if c["url"] == url)
            return Response(200, {"access_token": f"gw-token-{n}", "refresh_token": "refresh-1",
                                  "token_type": "bearer", "expires_in": 3600})
        if url in self.gateway and self.gateway[url]:
            return self.gateway[url].pop(0)
        return Response(202, None)

    def gateway_calls(self):
        return [c for c in self.calls if c["url"].endswith("/v3/events")]


def gateway_error(status, code):
    return Response(status, {"header": {"namespace": "System", "name": "Exception"},
                             "payload": {"code": code, "description": "test"}})


def make_services(with_device=True, with_grant=True, invoke_async=None):
    store = MemoryStore()
    http = FakeHttp()
    if with_device:
        store.put_device(USER_ID, dict(DEVICE))
    if with_grant:
        store.put_grant(USER_ID, {"access_token": "gw-token", "refresh_token": "refresh-0",
                                  "expires_at": NOW + 3000, "region": None})
    svc = Services(store, http, LWA_CLIENT_ID, "alexa-client", "alexa-secret",
                   now=lambda: NOW, sleep=lambda s: None, invoke_async=invoke_async)
    return svc

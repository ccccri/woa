"""Tiny HTTP client on top of urllib (no third-party dependencies)."""

import json
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT_SECONDS = 5


class Response:
    def __init__(self, status, body):
        self.status = status
        self.body = body  # parsed JSON, or None

    def __repr__(self):
        return f"Response({self.status}, {self.body!r})"


def _parse(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


class UrllibHttp:
    """The real HTTP client. Tests replace it with a fake that has the same API."""

    def request(self, method, url, headers=None, json_body=None, form=None):
        data = None
        headers = dict(headers or {})
        if json_body is not None:
            data = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                return Response(resp.status, _parse(resp.read()))
        except urllib.error.HTTPError as err:
            return Response(err.code, _parse(err.read()))
        except (urllib.error.URLError, TimeoutError, OSError):
            return Response(0, None)

"""Login with Amazon: identify users and exchange/refresh Alexa grant tokens."""

import hashlib
import logging
import urllib.parse

log = logging.getLogger(__name__)

TOKENINFO_URL = "https://api.amazon.com/auth/o2/tokeninfo"
TOKEN_URL = "https://api.amazon.com/auth/o2/token"


class AuthError(Exception):
    """The user's token is missing, expired or not issued for WOA."""


class GrantError(Exception):
    """The Alexa grant could not be exchanged or refreshed."""


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class UserResolver:
    """Maps an LWA access token to a stable Amazon user_id.

    The token must have been issued to our own LWA security profile
    (audience check), so tokens from other apps are rejected.
    Results are cached in DynamoDB until the token expires.
    """

    def __init__(self, store, http, client_id, now):
        self.store = store
        self.http = http
        self.client_id = client_id
        self.now = now

    def user_id(self, token):
        if not token or not isinstance(token, str):
            raise AuthError("missing token")
        key = token_hash(token)
        cached = self.store.get_token_user(key)
        if cached and cached["expires_at"] > self.now():
            return cached["user_id"]

        url = TOKENINFO_URL + "?" + urllib.parse.urlencode({"access_token": token})
        resp = self.http.request("GET", url)
        info = resp.body or {}
        if resp.status != 200 or "user_id" not in info:
            raise AuthError(f"tokeninfo failed with status {resp.status}")
        if info.get("aud") != self.client_id:
            raise AuthError("token was issued to another application")
        # LWA returns "exp" as seconds left; accept an absolute epoch too.
        exp = int(info.get("exp", 300))
        expires_at = exp if exp > 10**9 else int(self.now()) + min(exp, 3600)
        self.store.put_token_user(key, info["user_id"], expires_at)
        return info["user_id"]


class GrantClient:
    """Exchanges AcceptGrant codes and refreshes tokens for the Alexa Event Gateway.

    Uses the skill's "Alexa Skill Messaging" client id/secret
    (developer console > skill > Permissions > Send Alexa Events).
    """

    def __init__(self, http, client_id, client_secret, now):
        self.http = http
        self.client_id = client_id
        self.client_secret = client_secret
        self.now = now

    def _token_request(self, form):
        form = dict(form, client_id=self.client_id, client_secret=self.client_secret)
        resp = self.http.request("POST", TOKEN_URL, form=form)
        body = resp.body or {}
        if resp.status != 200 or "access_token" not in body:
            raise GrantError(body.get("error", f"status {resp.status}"))
        return {
            "access_token": body["access_token"],
            "refresh_token": body.get("refresh_token", form.get("refresh_token")),
            "expires_at": int(self.now()) + int(body.get("expires_in", 3600)),
        }

    def exchange(self, code):
        return self._token_request({"grant_type": "authorization_code", "code": code})

    def refresh(self, refresh_token):
        return self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})

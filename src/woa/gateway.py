"""Alexa Event Gateway client.

The gateway must match the region of the user's Alexa account. WOA runs a
single backend, so it tries the regions in order and remembers the one that
accepted the user's events (a wrong region answers 403 SKILL_NEVER_ENABLED).
"""

import logging
import time

from .lwa import GrantError

log = logging.getLogger(__name__)

GATEWAYS = {
    "EU": "https://api.eu.amazonalexa.com/v3/events",
    "NA": "https://api.amazonalexa.com/v3/events",
    "FE": "https://api.fe.amazonalexa.com/v3/events",
}
REFRESH_MARGIN_SECONDS = 120
RETRYABLE = {0, 429, 500, 503}
MAX_ATTEMPTS = 3


class NoGrant(Exception):
    """The user never completed AcceptGrant, or the grant was revoked."""


def _error_code(resp):
    try:
        return resp.body["payload"]["code"]
    except (TypeError, KeyError):
        return None


class Gateway:
    def __init__(self, store, http, grants, region_order=("EU", "NA", "FE"),
                 now=time.time, sleep=time.sleep):
        self.store = store
        self.http = http
        self.grants = grants  # lwa.GrantClient
        self.region_order = [r for r in region_order if r in GATEWAYS]
        self.now = now
        self.sleep = sleep

    def _grant(self, user_id, force_refresh=False):
        grant = self.store.get_grant(user_id)
        if not grant:
            raise NoGrant(user_id)
        if force_refresh or grant["expires_at"] - REFRESH_MARGIN_SECONDS <= self.now():
            try:
                fresh = self.grants.refresh(grant["refresh_token"])
            except GrantError as err:
                log.warning("grant refresh failed (%s), dropping grant", err)
                self.store.delete_grant(user_id)
                raise NoGrant(user_id) from err
            grant.update(fresh)
            self.store.put_grant(user_id, grant)
        return grant

    def _regions(self, grant):
        known = grant.get("region")
        if known in GATEWAYS:
            return [known] + [r for r in self.region_order if r != known]
        return list(self.region_order)

    def _post(self, url, token, body):
        resp = None
        for attempt in range(MAX_ATTEMPTS):
            if attempt:
                self.sleep(1)
            resp = self.http.request("POST", url, headers={"Authorization": f"Bearer {token}"},
                                     json_body=body)
            if resp.status not in RETRYABLE:
                break
        return resp

    def send(self, user_id, build):
        """Send the event returned by build(access_token). Returns True on 202.

        Raises NoGrant when the user has no usable grant.
        """
        grant = self._grant(user_id)
        refreshed = False
        for region in self._regions(grant):
            while True:
                token = grant["access_token"]
                resp = self._post(GATEWAYS[region], token, build(token))
                if resp.status == 401 and not refreshed:
                    grant = self._grant(user_id, force_refresh=True)
                    refreshed = True
                    continue
                break
            code = _error_code(resp)
            if resp.status in (200, 202):
                if grant.get("region") != region:
                    grant["region"] = region
                    self.store.put_grant(user_id, grant)
                return True
            if resp.status == 403 and code == "SKILL_NEVER_ENABLED_EXCEPTION":
                log.info("gateway %s does not know this user, trying next region", region)
                continue
            if resp.status == 403 and code == "SKILL_DISABLED_EXCEPTION":
                log.info("skill disabled by the user, dropping grant")
                self.store.delete_grant(user_id)
                raise NoGrant(user_id)
            log.warning("gateway %s rejected event: %s %s", region, resp.status, code)
            return False
        return False

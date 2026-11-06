"""Alexa Smart Home skill Lambda.

TurnOn follows the Alexa.WakeOnLANController workflow:
  1. reply synchronously with a DeferredResponse;
  2. send WakeUp to the Alexa Event Gateway (the Echo on the PC's LAN sends the magic packet);
  3. send the final Response (or ErrorResponse) to the gateway.
Steps 2-3 run in a second, asynchronous invocation of this same function.
"""

import logging

from . import alexa
from .gateway import NoGrant
from .lwa import AuthError, GrantError
from .services import services

log = logging.getLogger()
log.setLevel(logging.INFO)

WAKE_TASK = "woa.wake"
DEFERRAL_SECONDS = 5


def lambda_handler(event, context, svc=None):
    svc = svc or services()
    if event.get("task") == WAKE_TASK:
        return run_wake(svc, event)

    directive = event.get("directive") or {}
    head = directive.get("header") or {}
    ns, name = head.get("namespace"), head.get("name")
    log.info("directive %s.%s", ns, name)

    if ns == "Alexa.Discovery" and name == "Discover":
        return discover(svc, directive)
    if ns == "Alexa.Authorization" and name == "AcceptGrant":
        return accept_grant(svc, directive)
    if ns == "Alexa.PowerController" and name == "TurnOn":
        return turn_on(svc, directive)
    if ns == "Alexa.PowerController" and name == "TurnOff":
        return alexa.error_response(
            _endpoint_id(directive), head.get("correlationToken"),
            "NOT_SUPPORTED_IN_CURRENT_MODE", "WOA can only turn computers on.",
            extra={"currentDeviceMode": "OTHER"})
    if ns == "Alexa" and name == "ReportState":
        return report_state(svc, directive)
    return alexa.error_response(_endpoint_id(directive), head.get("correlationToken"),
                                "INVALID_DIRECTIVE", f"Unsupported directive {ns}.{name}")


def _endpoint_id(directive):
    return (directive.get("endpoint") or {}).get("endpointId")


def _endpoint_token(directive):
    return ((directive.get("endpoint") or {}).get("scope") or {}).get("token")


def _owned_device(svc, directive):
    """Return (user_id, device) or an ErrorResponse dict."""
    head = directive["header"]
    endpoint_id = _endpoint_id(directive)
    try:
        user_id = svc.users.user_id(_endpoint_token(directive))
    except AuthError as err:
        log.warning("auth failed: %s", err)
        return None, alexa.error_response(endpoint_id, head.get("correlationToken"),
                                          "INVALID_AUTHORIZATION_CREDENTIAL",
                                          "Account linking is no longer valid.")
    device = next((d for d in svc.store.list_devices(user_id) if d["id"] == endpoint_id), None)
    if device is None:
        return None, alexa.error_response(endpoint_id, head.get("correlationToken"),
                                          "NO_SUCH_ENDPOINT", "This computer was removed from WOA.")
    return (user_id, device), None


def discover(svc, directive):
    token = ((directive.get("payload") or {}).get("scope") or {}).get("token")
    try:
        user_id = svc.users.user_id(token)
    except AuthError as err:
        log.warning("discovery auth failed: %s", err)
        return alexa.discover_response([])
    return alexa.discover_response(svc.store.list_devices(user_id))


def accept_grant(svc, directive):
    payload = directive.get("payload") or {}
    code = (payload.get("grant") or {}).get("code")
    try:
        user_id = svc.users.user_id((payload.get("grantee") or {}).get("token"))
        grant = svc.grants.exchange(code)
    except (AuthError, GrantError) as err:
        log.warning("AcceptGrant failed: %s", err)
        return alexa.accept_grant_error("Could not complete authorization.")
    previous = svc.store.get_grant(user_id) or {}
    grant["region"] = previous.get("region")
    svc.store.put_grant(user_id, grant)
    return alexa.accept_grant_response()


def turn_on(svc, directive):
    found, error = _owned_device(svc, directive)
    if error:
        return error
    user_id, device = found
    correlation_token = directive["header"].get("correlationToken")
    if svc.store.get_grant(user_id) is None:
        return alexa.error_response(
            device["id"], correlation_token, "INTERNAL_ERROR",
            "Missing Alexa events permission. Disable and enable the skill again.")

    task = {"task": WAKE_TASK, "user_id": user_id, "endpoint_id": device["id"],
            "correlation_token": correlation_token}
    try:
        started = bool(svc.invoke_async and svc.invoke_async(task))
    except Exception:  # noqa: BLE001 - fall back to doing the work inline
        log.exception("async invoke failed")
        started = False
    if started:
        return alexa.deferred_response(correlation_token, DEFERRAL_SECONDS)

    # Fallback: wake now and answer synchronously.
    if _send_wake_up(svc, user_id, device["id"], correlation_token):
        return alexa.power_response(None, device["id"], correlation_token, svc.now())
    return alexa.error_response(device["id"], correlation_token, "ENDPOINT_UNREACHABLE",
                                "Alexa could not send the Wake on LAN request.")


def _send_wake_up(svc, user_id, endpoint_id, correlation_token):
    try:
        return svc.gateway.send(user_id, lambda token: alexa.wake_up_event(
            token, endpoint_id, correlation_token, svc.now()))
    except NoGrant:
        return False


def run_wake(svc, task):
    """Second half of TurnOn, run asynchronously."""
    user_id, endpoint_id = task["user_id"], task["endpoint_id"]
    correlation_token = task["correlation_token"]
    ok = _send_wake_up(svc, user_id, endpoint_id, correlation_token)
    if ok:
        final = lambda token: alexa.power_response(token, endpoint_id, correlation_token,
                                                   svc.now())
    else:
        final = lambda token: alexa.error_response(
            endpoint_id, correlation_token, "ENDPOINT_UNREACHABLE",
            "Alexa could not send the Wake on LAN request.", token=token)
    try:
        svc.gateway.send(user_id, final)
    except NoGrant:
        log.warning("no grant to send the final TurnOn response")
    log.info("wake %s", "sent" if ok else "failed")
    return {"ok": ok}


def report_state(svc, directive):
    found, error = _owned_device(svc, directive)
    if error:
        return error
    _, device = found
    return alexa.state_report(device["id"], directive["header"].get("correlationToken"),
                              token=_endpoint_token(directive), now=svc.now())

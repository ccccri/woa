"""HTTP API for the configuration page (Lambda Function URL, payload v2).

Every request carries "Authorization: Bearer <Login with Amazon token>".

  GET    /api/me             -> {"devices": [...], "linked": bool, "maxDevices": n}
  POST   /api/devices        {"name", "mac"} -> {"device", "synced"}
  DELETE /api/devices/<id>   -> {"deleted": true, "synced"}
  DELETE /api/me             -> {"deleted": true}   (removes all stored data)

"synced" tells whether Alexa was updated right away; otherwise the user
says "Alexa, discover devices".
"""

import base64
import json
import logging
import secrets

from . import alexa
from .gateway import NoGrant
from .lwa import AuthError
from .services import MAX_DEVICES, services
from .validation import normalize_mac, normalize_name

log = logging.getLogger()
log.setLevel(logging.INFO)

MAX_BODY_BYTES = 2048


def _reply(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json",
                                              "Cache-Control": "no-store"},
            "body": json.dumps(body)}


def _error(status, message):
    return _reply(status, {"error": message})


def _body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8", "replace")
    if len(raw) > MAX_BODY_BYTES:
        raise ValueError("Request too large")
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        raise ValueError("Invalid JSON") from None
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON")
    return data


def _public(device):
    return {"id": device["id"], "name": device["name"], "mac": device["mac"]}


def _sync(svc, user_id, build):
    try:
        return svc.gateway.send(user_id, build)
    except NoGrant:
        return False
    except Exception:  # noqa: BLE001 - syncing is best effort
        log.exception("sync failed")
        return False


def lambda_handler(event, context, svc=None):
    svc = svc or services()
    http = (event.get("requestContext") or {}).get("http") or {}
    method = http.get("method", "")
    path = (event.get("rawPath") or "/").rstrip("/") or "/"

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    auth = headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return _error(401, "Sign in with Amazon first")
    try:
        user_id = svc.users.user_id(auth[len("Bearer "):].strip())
    except AuthError:
        return _error(401, "Your session expired, sign in again")

    try:
        if path == "/api/me" and method == "GET":
            return _reply(200, {
                "devices": [_public(d) for d in svc.store.list_devices(user_id)],
                "linked": svc.store.get_grant(user_id) is not None,
                "maxDevices": MAX_DEVICES,
            })
        if path == "/api/devices" and method == "POST":
            return add_device(svc, user_id, _body(event))
        if path.startswith("/api/devices/") and method == "DELETE":
            return delete_device(svc, user_id, path[len("/api/devices/"):])
        if path == "/api/me" and method == "DELETE":
            return delete_account(svc, user_id)
    except ValueError as err:
        return _error(400, str(err))
    return _error(404, "Not found")


def add_device(svc, user_id, data):
    name = normalize_name(data.get("name"))
    mac = normalize_mac(data.get("mac"))
    devices = svc.store.list_devices(user_id)
    if len(devices) >= MAX_DEVICES:
        return _error(409, f"You can add at most {MAX_DEVICES} computers")
    for d in devices:
        if d["mac"] == mac:
            return _error(409, f"This MAC address is already used by \"{d['name']}\"")
        if d["name"].casefold() == name.casefold():
            return _error(409, "You already have a computer with this name")
    device = {"id": "woa-" + secrets.token_hex(8), "name": name, "mac": mac,
              "created_at": int(svc.now())}
    svc.store.put_device(user_id, device)
    synced = _sync(svc, user_id, lambda token: alexa.add_or_update_report(token, [device]))
    return _reply(201, {"device": _public(device), "synced": synced})


def delete_device(svc, user_id, device_id):
    if not svc.store.delete_device(user_id, device_id):
        return _error(404, "Computer not found")
    synced = _sync(svc, user_id, lambda token: alexa.delete_report(token, [device_id]))
    return _reply(200, {"deleted": True, "synced": synced})


def delete_account(svc, user_id):
    ids = [d["id"] for d in svc.store.list_devices(user_id)]
    if ids:
        _sync(svc, user_id, lambda token: alexa.delete_report(token, ids))
    svc.store.delete_user(user_id)
    return _reply(200, {"deleted": True})

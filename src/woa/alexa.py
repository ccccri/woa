"""Builders for Alexa Smart Home API v3 messages."""

import time
import uuid

MANUFACTURER = "WOA - Wake On Alexa"
MODEL = "Wake on LAN computer"
DESCRIPTION = "Computer woken up with Wake on LAN by your Echo"


def iso_time(epoch=None):
    t = time.time() if epoch is None else epoch
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + ".00Z"


def header(namespace, name, correlation_token=None):
    h = {"namespace": namespace, "name": name, "payloadVersion": "3",
         "messageId": str(uuid.uuid4())}
    if correlation_token:
        h["correlationToken"] = correlation_token
    return h


def scope(token):
    return {"type": "BearerToken", "token": token}


# Discovery ----------------------------------------------------------------

def discovery_endpoint(device):
    return {
        "endpointId": device["id"],
        "manufacturerName": MANUFACTURER,
        "description": DESCRIPTION,
        "friendlyName": device["name"],
        "displayCategories": ["COMPUTER"],
        "additionalAttributes": {"manufacturer": MANUFACTURER, "model": MODEL},
        "cookie": {},
        "capabilities": [
            {"type": "AlexaInterface", "interface": "Alexa", "version": "3"},
            {
                "type": "AlexaInterface",
                "interface": "Alexa.WakeOnLANController",
                "version": "3",
                "properties": {},
                "configuration": {"MACAddresses": [device["mac"]]},
            },
            {
                # WOA cannot read the power state: it only asks the Echo to wake the PC.
                "type": "AlexaInterface",
                "interface": "Alexa.PowerController",
                "version": "3",
                "properties": {
                    "supported": [{"name": "powerState"}],
                    "proactivelyReported": False,
                    "retrievable": False,
                },
            },
            {
                "type": "AlexaInterface",
                "interface": "Alexa.EndpointHealth",
                "version": "3",
                "properties": {
                    "supported": [{"name": "connectivity"}],
                    "proactivelyReported": False,
                    "retrievable": True,
                },
            },
        ],
    }


def discover_response(devices):
    return {"event": {
        "header": header("Alexa.Discovery", "Discover.Response"),
        "payload": {"endpoints": [discovery_endpoint(d) for d in devices]},
    }}


def add_or_update_report(token, devices):
    return {"event": {
        "header": header("Alexa.Discovery", "AddOrUpdateReport"),
        "payload": {"endpoints": [discovery_endpoint(d) for d in devices], "scope": scope(token)},
    }}


def delete_report(token, endpoint_ids):
    return {"event": {
        "header": header("Alexa.Discovery", "DeleteReport"),
        "payload": {"endpoints": [{"endpointId": e} for e in endpoint_ids], "scope": scope(token)},
    }}


# Authorization ------------------------------------------------------------

def accept_grant_response():
    return {"event": {"header": header("Alexa.Authorization", "AcceptGrant.Response"),
                      "payload": {}}}


def accept_grant_error(message):
    return {"event": {"header": header("Alexa.Authorization", "ErrorResponse"),
                      "payload": {"type": "ACCEPT_GRANT_FAILED", "message": message}}}


# Power / Wake on LAN ------------------------------------------------------

def _power_state(value, now):
    return {"namespace": "Alexa.PowerController", "name": "powerState", "value": value,
            "timeOfSample": iso_time(now), "uncertaintyInMilliseconds": 500}


def _connectivity(now):
    return {"namespace": "Alexa.EndpointHealth", "name": "connectivity",
            "value": {"value": "OK"}, "timeOfSample": iso_time(now),
            "uncertaintyInMilliseconds": 0}


def deferred_response(correlation_token, seconds):
    return {"event": {
        "header": header("Alexa", "DeferredResponse", correlation_token),
        "payload": {"estimatedDeferralInSeconds": seconds},
    }}


def wake_up_event(token, endpoint_id, correlation_token, now=None):
    return {
        "context": {"properties": [_power_state("OFF", now)]},
        "event": {
            "header": header("Alexa.WakeOnLANController", "WakeUp", correlation_token),
            "endpoint": {"scope": scope(token), "endpointId": endpoint_id},
            "payload": {},
        },
    }


def power_response(token, endpoint_id, correlation_token, now=None):
    """Final Response to TurnOn. 'token' is None for a synchronous reply."""
    endpoint = {"endpointId": endpoint_id}
    if token:
        endpoint = {"scope": scope(token), "endpointId": endpoint_id}
    return {
        "context": {"properties": [_power_state("ON", now), _connectivity(now)]},
        "event": {
            "header": header("Alexa", "Response", correlation_token),
            "endpoint": endpoint,
            "payload": {},
        },
    }


def state_report(endpoint_id, correlation_token, token=None, now=None):
    endpoint = {"endpointId": endpoint_id}
    if token:
        endpoint["scope"] = scope(token)
    return {
        "context": {"properties": [_connectivity(now)]},
        "event": {
            "header": header("Alexa", "StateReport", correlation_token),
            "endpoint": endpoint,
            "payload": {},
        },
    }


def error_response(endpoint_id, correlation_token, error_type, message,
                   token=None, extra=None):
    endpoint = {"endpointId": endpoint_id} if endpoint_id else None
    if endpoint and token:
        endpoint["scope"] = scope(token)
    payload = {"type": error_type, "message": message}
    payload.update(extra or {})
    event = {"header": header("Alexa", "ErrorResponse", correlation_token), "payload": payload}
    if endpoint:
        event["endpoint"] = endpoint
    return {"event": event}

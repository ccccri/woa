"""Wires configuration (environment variables) to the real services.

Handlers call services() to get them; tests build Services with fakes.
"""

import os
import time

from .gateway import Gateway
from .lwa import GrantClient, UserResolver
from .net import UrllibHttp

MAX_DEVICES = 20


class Services:
    def __init__(self, store, http, lwa_client_id, alexa_client_id, alexa_client_secret,
                 region_order=("EU", "NA", "FE"), now=time.time, sleep=time.sleep,
                 invoke_async=None):
        self.store = store
        self.http = http
        self.now = now
        self.users = UserResolver(store, http, lwa_client_id, now)
        self.grants = GrantClient(http, alexa_client_id, alexa_client_secret, now)
        self.gateway = Gateway(store, http, self.grants, region_order, now, sleep)
        # invoke_async(payload) -> bool: runs the skill Lambda again in the background.
        self.invoke_async = invoke_async


_cached = None


def _lambda_invoker():
    import json
    import boto3
    client = boto3.client("lambda")
    function_name = os.environ.get("AWS_LAMBDA_FUNCTION_NAME")

    def invoke(payload):
        resp = client.invoke(FunctionName=function_name, InvocationType="Event",
                             Payload=json.dumps(payload).encode())
        return resp.get("StatusCode") == 202

    return invoke


def services():
    global _cached
    if _cached is None:
        from .store import DynamoStore
        env = os.environ
        _cached = Services(
            store=DynamoStore(env["TABLE_NAME"]),
            http=UrllibHttp(),
            lwa_client_id=env["LWA_CLIENT_ID"],
            alexa_client_id=env.get("ALEXA_CLIENT_ID", ""),
            alexa_client_secret=env.get("ALEXA_CLIENT_SECRET", ""),
            region_order=tuple(r.strip() for r in env.get("GATEWAY_ORDER", "EU,NA,FE").split(",")),
            invoke_async=_lambda_invoker(),
        )
    return _cached

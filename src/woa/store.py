"""Persistence. One DynamoDB table, single-table design:

  pk = USER#<user_id>   sk = DEVICE#<endpoint_id>  -> name, mac
  pk = USER#<user_id>   sk = GRANT                 -> Alexa Event Gateway tokens
  pk = TOKEN#<sha256>   sk = USER                  -> cached user_id (expires via TTL)
"""

import time


def _user(user_id):
    return f"USER#{user_id}"


class DynamoStore:
    def __init__(self, table_name, resource=None):
        if resource is None:
            import boto3  # available in the Lambda runtime
            resource = boto3.resource("dynamodb")
        self.table = resource.Table(table_name)

    # Devices -----------------------------------------------------------
    def _query_user(self, user_id):
        from boto3.dynamodb.conditions import Key
        items, kwargs = [], {"KeyConditionExpression": Key("pk").eq(_user(user_id))}
        while True:
            page = self.table.query(**kwargs)
            items.extend(page.get("Items", []))
            if "LastEvaluatedKey" not in page:
                return items
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def list_devices(self, user_id):
        devices = [
            {"id": it["sk"][len("DEVICE#"):], "name": it["name"], "mac": it["mac"],
             "created_at": int(it.get("created_at", 0))}
            for it in self._query_user(user_id) if it["sk"].startswith("DEVICE#")
        ]
        return sorted(devices, key=lambda d: d["created_at"])

    def put_device(self, user_id, device):
        self.table.put_item(Item={
            "pk": _user(user_id), "sk": f"DEVICE#{device['id']}",
            "name": device["name"], "mac": device["mac"],
            "created_at": int(device.get("created_at", time.time())),
        })

    def delete_device(self, user_id, device_id):
        resp = self.table.delete_item(
            Key={"pk": _user(user_id), "sk": f"DEVICE#{device_id}"}, ReturnValues="ALL_OLD")
        return "Attributes" in resp

    # Grant -------------------------------------------------------------
    def get_grant(self, user_id):
        item = self.table.get_item(Key={"pk": _user(user_id), "sk": "GRANT"}).get("Item")
        if not item:
            return None
        return {
            "access_token": item["access_token"], "refresh_token": item["refresh_token"],
            "expires_at": int(item["expires_at"]), "region": item.get("region"),
        }

    def put_grant(self, user_id, grant):
        item = {"pk": _user(user_id), "sk": "GRANT", "access_token": grant["access_token"],
                "refresh_token": grant["refresh_token"], "expires_at": int(grant["expires_at"])}
        if grant.get("region"):
            item["region"] = grant["region"]
        self.table.put_item(Item=item)

    def delete_grant(self, user_id):
        self.table.delete_item(Key={"pk": _user(user_id), "sk": "GRANT"})

    # Whole account -----------------------------------------------------
    def delete_user(self, user_id):
        with self.table.batch_writer() as batch:
            for it in self._query_user(user_id):
                batch.delete_item(Key={"pk": it["pk"], "sk": it["sk"]})

    # Token cache -------------------------------------------------------
    def get_token_user(self, key):
        item = self.table.get_item(Key={"pk": f"TOKEN#{key}", "sk": "USER"}).get("Item")
        if not item:
            return None
        return {"user_id": item["user_id"], "expires_at": int(item["expires_at"])}

    def put_token_user(self, key, user_id, expires_at):
        self.table.put_item(Item={
            "pk": f"TOKEN#{key}", "sk": "USER", "user_id": user_id,
            "expires_at": int(expires_at), "ttl": int(expires_at) + 3600,
        })


class MemoryStore:
    """In-memory store with the same API, for tests and local experiments."""

    def __init__(self):
        self.devices = {}  # user_id -> {device_id: device}
        self.grants = {}
        self.tokens = {}

    def list_devices(self, user_id):
        return sorted((dict(d) for d in self.devices.get(user_id, {}).values()),
                      key=lambda d: d["created_at"])

    def put_device(self, user_id, device):
        d = dict(device)
        d.setdefault("created_at", int(time.time()))
        self.devices.setdefault(user_id, {})[d["id"]] = d

    def delete_device(self, user_id, device_id):
        return self.devices.get(user_id, {}).pop(device_id, None) is not None

    def get_grant(self, user_id):
        g = self.grants.get(user_id)
        return dict(g) if g else None

    def put_grant(self, user_id, grant):
        self.grants[user_id] = dict(grant)

    def delete_grant(self, user_id):
        self.grants.pop(user_id, None)

    def delete_user(self, user_id):
        self.devices.pop(user_id, None)
        self.grants.pop(user_id, None)

    def get_token_user(self, key):
        t = self.tokens.get(key)
        return dict(t) if t else None

    def put_token_user(self, key, user_id, expires_at):
        self.tokens[key] = {"user_id": user_id, "expires_at": int(expires_at)}

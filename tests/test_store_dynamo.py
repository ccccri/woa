"""DynamoStore against a mocked DynamoDB. Skipped when moto is not installed."""

import unittest

import fakes  # noqa: F401 - sets sys.path

try:
    import boto3
    from moto import mock_aws
except ImportError:  # pragma: no cover
    mock_aws = None

from woa.store import DynamoStore


@unittest.skipIf(mock_aws is None, "moto not installed")
class DynamoStoreTest(unittest.TestCase):
    def setUp(self):
        self.mock = mock_aws()
        self.mock.start()
        ddb = boto3.resource("dynamodb", region_name="eu-west-1")
        ddb.create_table(
            TableName="woa-data", BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"},
                                  {"AttributeName": "sk", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"},
                       {"AttributeName": "sk", "KeyType": "RANGE"}])
        self.store = DynamoStore("woa-data", resource=ddb)

    def tearDown(self):
        self.mock.stop()

    def test_roundtrip(self):
        s = self.store
        s.put_device("u1", {"id": "woa-1", "name": "PC", "mac": "C8-7F-54-0B-30-C5", "created_at": 2})
        s.put_device("u1", {"id": "woa-0", "name": "Laptop", "mac": "00-11-22-33-44-55", "created_at": 1})
        s.put_device("u2", {"id": "woa-9", "name": "Other", "mac": "00-11-22-33-44-66"})
        s.put_grant("u1", {"access_token": "a", "refresh_token": "r", "expires_at": 10, "region": None})
        s.put_token_user("hash", "u1", 100)
        self.assertEqual([d["id"] for d in s.list_devices("u1")], ["woa-0", "woa-1"])
        self.assertEqual(s.get_grant("u1")["refresh_token"], "r")
        self.assertIsNone(s.get_grant("u1")["region"])
        s.put_grant("u1", dict(s.get_grant("u1"), region="EU"))
        self.assertEqual(s.get_grant("u1")["region"], "EU")
        self.assertEqual(s.get_token_user("hash"), {"user_id": "u1", "expires_at": 100})
        self.assertTrue(s.delete_device("u1", "woa-1"))
        self.assertFalse(s.delete_device("u1", "woa-1"))
        s.delete_user("u1")
        self.assertEqual(s.list_devices("u1"), [])
        self.assertIsNone(s.get_grant("u1"))
        self.assertEqual(len(s.list_devices("u2")), 1)


if __name__ == "__main__":
    unittest.main()

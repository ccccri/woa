import json
import unittest

from fakes import EU, USER_ID, gateway_error, make_services

from woa import web_handler
from woa.validation import normalize_mac, normalize_name


def request(svc, method, path, body=None, token="user-token"):
    event = {"rawPath": path, "requestContext": {"http": {"method": method}},
             "headers": {"authorization": f"Bearer {token}"} if token else {}}
    if body is not None:
        event["body"] = json.dumps(body)
    resp = web_handler.lambda_handler(event, None, svc=svc)
    return resp["statusCode"], json.loads(resp["body"])


class ValidationTest(unittest.TestCase):
    def test_mac_formats(self):
        for raw in ("c8:7f:54:0b:30:c5", "C8-7F-54-0B-30-C5", "c87f.540b.30c5", "c87f540b30c5",
                    " c8 7f 54 0b 30 c5 "):
            self.assertEqual(normalize_mac(raw), "C8-7F-54-0B-30-C5")

    def test_bad_macs(self):
        for raw in (None, "", "c8:7f:54:0b:30", "zz:7f:54:0b:30:c5", "00:00:00:00:00:00",
                    "ff:ff:ff:ff:ff:ff", "01:00:5e:00:00:01", "c8:7f:54:0b:30:c5:00"):
            with self.assertRaises(ValueError):
                normalize_mac(raw)

    def test_names(self):
        self.assertEqual(normalize_name("  PC   di  Cri "), "PC di Cri")
        self.assertEqual(normalize_name("Computer Città"), "Computer Città")
        for raw in (None, "", "   ", "PC!", "my-pc", "x" * 65):
            with self.assertRaises(ValueError):
                normalize_name(raw)


class ApiTest(unittest.TestCase):
    def test_requires_token(self):
        status, _ = request(make_services(), "GET", "/api/me", token=None)
        self.assertEqual(status, 401)

    def test_rejects_invalid_token(self):
        status, _ = request(make_services(), "GET", "/api/me", token="stolen")
        self.assertEqual(status, 401)

    def test_me(self):
        status, body = request(make_services(), "GET", "/api/me")
        self.assertEqual(status, 200)
        self.assertTrue(body["linked"])
        self.assertEqual(body["devices"][0]["mac"], "C8-7F-54-0B-30-C5")

    def test_add_device_syncs_with_alexa(self):
        svc = make_services(with_device=False)
        status, body = request(svc, "POST", "/api/devices",
                               {"name": "Office PC", "mac": "00:11:22:33:44:55"})
        self.assertEqual(status, 201)
        self.assertTrue(body["synced"])
        self.assertEqual(body["device"]["mac"], "00-11-22-33-44-55")
        [call] = svc.http.gateway_calls()
        self.assertEqual(call["url"], EU)
        self.assertEqual(call["json"]["event"]["header"]["name"], "AddOrUpdateReport")
        self.assertEqual(len(svc.store.list_devices(USER_ID)), 1)

    def test_add_device_without_grant_is_saved_but_not_synced(self):
        svc = make_services(with_device=False, with_grant=False)
        status, body = request(svc, "POST", "/api/devices",
                               {"name": "Office PC", "mac": "00:11:22:33:44:55"})
        self.assertEqual(status, 201)
        self.assertFalse(body["synced"])

    def test_add_device_sync_failure_still_saves(self):
        svc = make_services(with_device=False)
        svc.http.queue(EU, gateway_error(500, "INTERNAL_SERVICE_EXCEPTION"),
                       gateway_error(500, "INTERNAL_SERVICE_EXCEPTION"),
                       gateway_error(500, "INTERNAL_SERVICE_EXCEPTION"))
        status, body = request(svc, "POST", "/api/devices",
                               {"name": "Office PC", "mac": "00:11:22:33:44:55"})
        self.assertEqual(status, 201)
        self.assertFalse(body["synced"])

    def test_duplicates_rejected(self):
        svc = make_services()
        status, _ = request(svc, "POST", "/api/devices",
                            {"name": "Other", "mac": "c8:7f:54:0b:30:c5"})
        self.assertEqual(status, 409)
        status, _ = request(svc, "POST", "/api/devices",
                            {"name": "gaming pc", "mac": "00:11:22:33:44:55"})
        self.assertEqual(status, 409)

    def test_invalid_input(self):
        svc = make_services()
        status, body = request(svc, "POST", "/api/devices", {"name": "PC", "mac": "nope"})
        self.assertEqual(status, 400)
        self.assertIn("MAC", body["error"])
        event = {"rawPath": "/api/devices", "requestContext": {"http": {"method": "POST"}},
                 "headers": {"Authorization": "Bearer user-token"}, "body": "{not json"}
        self.assertEqual(web_handler.lambda_handler(event, None, svc=svc)["statusCode"], 400)

    def test_device_limit(self):
        svc = make_services(with_device=False, with_grant=False)
        for i in range(20):
            status, _ = request(svc, "POST", "/api/devices",
                                {"name": f"PC {i}", "mac": f"00:11:22:33:44:{i:02x}"})
            self.assertEqual(status, 201)
        status, _ = request(svc, "POST", "/api/devices",
                            {"name": "One more", "mac": "00:11:22:33:55:00"})
        self.assertEqual(status, 409)

    def test_delete_device(self):
        svc = make_services()
        status, body = request(svc, "DELETE", "/api/devices/woa-0123456789abcdef")
        self.assertEqual(status, 200)
        self.assertTrue(body["synced"])
        self.assertEqual(svc.http.gateway_calls()[0]["json"]["event"]["header"]["name"],
                         "DeleteReport")
        status, _ = request(svc, "DELETE", "/api/devices/woa-0123456789abcdef")
        self.assertEqual(status, 404)

    def test_users_are_isolated(self):
        svc = make_services()
        svc.http.tokens["other-token"] = {"user_id": "amzn1.account.OTHER",
                                          "aud": svc.users.client_id, "exp": 3000}
        status, body = request(svc, "GET", "/api/me", token="other-token")
        self.assertEqual(body["devices"], [])
        status, _ = request(svc, "DELETE", "/api/devices/woa-0123456789abcdef",
                            token="other-token")
        self.assertEqual(status, 404)
        self.assertEqual(len(svc.store.list_devices(USER_ID)), 1)

    def test_delete_account(self):
        svc = make_services()
        status, _ = request(svc, "DELETE", "/api/me")
        self.assertEqual(status, 200)
        self.assertEqual(svc.store.list_devices(USER_ID), [])
        self.assertIsNone(svc.store.get_grant(USER_ID))

    def test_unknown_route(self):
        status, _ = request(make_services(), "GET", "/api/nothing")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()

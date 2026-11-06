import unittest

from fakes import (DEVICE, EU, NA, NOW, USER_ID, gateway_error, load_event,
                   make_services)

from woa import skill_handler


def handle(svc, name):
    return skill_handler.lambda_handler(load_event(name), None, svc=svc)


class DiscoveryTest(unittest.TestCase):
    def test_discovery_lists_devices_with_wol_capability(self):
        resp = handle(make_services(), "discover.json")
        header = resp["event"]["header"]
        self.assertEqual((header["namespace"], header["name"]),
                         ("Alexa.Discovery", "Discover.Response"))
        [endpoint] = resp["event"]["payload"]["endpoints"]
        self.assertEqual(endpoint["endpointId"], DEVICE["id"])
        self.assertEqual(endpoint["friendlyName"], "Gaming PC")
        self.assertEqual(endpoint["displayCategories"], ["COMPUTER"])
        caps = {c["interface"]: c for c in endpoint["capabilities"]}
        self.assertEqual(caps["Alexa.WakeOnLANController"]["configuration"],
                         {"MACAddresses": ["C8-7F-54-0B-30-C5"]})
        self.assertIn("Alexa.PowerController", caps)
        self.assertIn("Alexa", caps)

    def test_discovery_with_bad_token_returns_no_endpoints(self):
        svc = make_services()
        svc.http.tokens.clear()
        resp = handle(svc, "discover.json")
        self.assertEqual(resp["event"]["payload"]["endpoints"], [])

    def test_token_from_other_app_is_rejected(self):
        svc = make_services()
        svc.http.tokens["user-token"]["aud"] = "someone-else"
        resp = handle(svc, "discover.json")
        self.assertEqual(resp["event"]["payload"]["endpoints"], [])

    def test_user_lookup_is_cached(self):
        svc = make_services()
        handle(svc, "discover.json")
        handle(svc, "discover.json")
        tokeninfo = [c for c in svc.http.calls if "tokeninfo" in c["url"]]
        self.assertEqual(len(tokeninfo), 1)


class AcceptGrantTest(unittest.TestCase):
    def test_grant_is_exchanged_and_stored(self):
        svc = make_services(with_grant=False)
        resp = handle(svc, "accept_grant.json")
        self.assertEqual(resp["event"]["header"]["name"], "AcceptGrant.Response")
        token_call = [c for c in svc.http.calls if c["url"].endswith("/auth/o2/token")][0]
        self.assertEqual(token_call["form"]["grant_type"], "authorization_code")
        self.assertEqual(token_call["form"]["code"], "grant-code")
        self.assertEqual(token_call["form"]["client_id"], "alexa-client")
        grant = svc.store.get_grant(USER_ID)
        self.assertEqual(grant["refresh_token"], "refresh-1")
        self.assertEqual(grant["expires_at"], NOW + 3600)

    def test_failed_exchange_returns_accept_grant_failed(self):
        svc = make_services(with_grant=False)
        svc.http.token_status = 400
        resp = handle(svc, "accept_grant.json")
        self.assertEqual(resp["event"]["header"]["name"], "ErrorResponse")
        self.assertEqual(resp["event"]["payload"]["type"], "ACCEPT_GRANT_FAILED")
        self.assertIsNone(svc.store.get_grant(USER_ID))


class TurnOnTest(unittest.TestCase):
    def test_turn_on_defers_and_starts_async_wake(self):
        tasks = []
        svc = make_services(invoke_async=lambda t: tasks.append(t) or True)
        resp = handle(svc, "turn_on.json")
        self.assertEqual(resp["event"]["header"]["name"], "DeferredResponse")
        self.assertEqual(resp["event"]["header"]["correlationToken"], "corr-token")
        self.assertEqual(tasks, [{"task": "woa.wake", "user_id": USER_ID,
                                  "endpoint_id": DEVICE["id"],
                                  "correlation_token": "corr-token"}])
        self.assertEqual(svc.http.gateway_calls(), [])

    def test_async_wake_sends_wakeup_then_response(self):
        svc = make_services()
        result = skill_handler.lambda_handler(
            {"task": "woa.wake", "user_id": USER_ID, "endpoint_id": DEVICE["id"],
             "correlation_token": "corr-token"}, None, svc=svc)
        self.assertEqual(result, {"ok": True})
        wake, final = svc.http.gateway_calls()
        self.assertEqual(wake["url"], EU)
        self.assertEqual(wake["headers"]["Authorization"], "Bearer gw-token")
        event = wake["json"]["event"]
        self.assertEqual((event["header"]["namespace"], event["header"]["name"]),
                         ("Alexa.WakeOnLANController", "WakeUp"))
        self.assertEqual(event["header"]["correlationToken"], "corr-token")
        self.assertEqual(event["endpoint"]["scope"]["token"], "gw-token")
        self.assertEqual(wake["json"]["context"]["properties"][0]["value"], "OFF")
        self.assertEqual(final["json"]["event"]["header"]["name"], "Response")
        self.assertEqual(final["json"]["event"]["header"]["correlationToken"], "corr-token")
        self.assertEqual(svc.store.get_grant(USER_ID)["region"], "EU")

    def test_wrong_region_falls_back_and_is_remembered(self):
        svc = make_services()
        svc.http.queue(EU, gateway_error(403, "SKILL_NEVER_ENABLED_EXCEPTION"))
        skill_handler.run_wake(svc, {"user_id": USER_ID, "endpoint_id": DEVICE["id"],
                                     "correlation_token": "corr-token"})
        urls = [c["url"] for c in svc.http.gateway_calls()]
        self.assertEqual(urls, [EU, NA, NA])
        self.assertEqual(svc.store.get_grant(USER_ID)["region"], "NA")

    def test_expired_token_is_refreshed_before_sending(self):
        svc = make_services()
        grant = svc.store.get_grant(USER_ID)
        grant["expires_at"] = NOW - 1
        svc.store.put_grant(USER_ID, grant)
        skill_handler.run_wake(svc, {"user_id": USER_ID, "endpoint_id": DEVICE["id"],
                                     "correlation_token": "corr-token"})
        refresh = [c for c in svc.http.calls if c["url"].endswith("/auth/o2/token")][0]
        self.assertEqual(refresh["form"]["grant_type"], "refresh_token")
        self.assertEqual(refresh["form"]["refresh_token"], "refresh-0")
        self.assertTrue(svc.http.gateway_calls()[0]["headers"]["Authorization"]
                        .startswith("Bearer gw-token-"))

    def test_401_triggers_refresh_and_retry(self):
        svc = make_services()
        svc.http.queue(EU, gateway_error(401, "INVALID_ACCESS_TOKEN_EXCEPTION"))
        result = skill_handler.run_wake(svc, {"user_id": USER_ID, "endpoint_id": DEVICE["id"],
                                              "correlation_token": "corr-token"})
        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(svc.http.gateway_calls()), 3)

    def test_failed_wake_sends_error_response(self):
        svc = make_services()
        svc.http.queue(EU, gateway_error(400, "INVALID_REQUEST_EXCEPTION"))
        result = skill_handler.run_wake(svc, {"user_id": USER_ID, "endpoint_id": DEVICE["id"],
                                              "correlation_token": "corr-token"})
        self.assertEqual(result, {"ok": False})
        final = svc.http.gateway_calls()[-1]["json"]["event"]
        self.assertEqual(final["header"]["name"], "ErrorResponse")
        self.assertEqual(final["payload"]["type"], "ENDPOINT_UNREACHABLE")

    def test_disabled_skill_drops_grant(self):
        svc = make_services()
        svc.http.queue(EU, gateway_error(403, "SKILL_DISABLED_EXCEPTION"))
        skill_handler.run_wake(svc, {"user_id": USER_ID, "endpoint_id": DEVICE["id"],
                                     "correlation_token": "corr-token"})
        self.assertIsNone(svc.store.get_grant(USER_ID))

    def test_sync_fallback_when_async_invoke_fails(self):
        def broken(task):
            raise RuntimeError("no permission")
        svc = make_services(invoke_async=broken)
        resp = handle(svc, "turn_on.json")
        self.assertEqual(resp["event"]["header"]["name"], "Response")
        self.assertEqual(resp["context"]["properties"][0]["value"], "ON")
        self.assertEqual(len(svc.http.gateway_calls()), 1)

    def test_unknown_endpoint(self):
        svc = make_services(with_device=False, invoke_async=lambda t: True)
        resp = handle(svc, "turn_on.json")
        self.assertEqual(resp["event"]["payload"]["type"], "NO_SUCH_ENDPOINT")

    def test_missing_grant(self):
        svc = make_services(with_grant=False, invoke_async=lambda t: True)
        resp = handle(svc, "turn_on.json")
        self.assertEqual(resp["event"]["header"]["name"], "ErrorResponse")

    def test_invalid_token(self):
        svc = make_services(invoke_async=lambda t: True)
        svc.http.tokens.clear()
        resp = handle(svc, "turn_on.json")
        self.assertEqual(resp["event"]["payload"]["type"], "INVALID_AUTHORIZATION_CREDENTIAL")


class OtherDirectivesTest(unittest.TestCase):
    def test_turn_off_is_not_supported(self):
        resp = handle(make_services(), "turn_off.json")
        self.assertEqual(resp["event"]["header"]["name"], "ErrorResponse")
        self.assertEqual(resp["event"]["payload"]["type"], "NOT_SUPPORTED_IN_CURRENT_MODE")
        self.assertEqual(resp["event"]["header"]["correlationToken"], "corr-token")

    def test_report_state(self):
        resp = handle(make_services(), "report_state.json")
        self.assertEqual(resp["event"]["header"]["name"], "StateReport")
        self.assertEqual(resp["event"]["endpoint"]["endpointId"], DEVICE["id"])
        [prop] = resp["context"]["properties"]
        self.assertEqual(prop["namespace"], "Alexa.EndpointHealth")
        self.assertEqual(prop["value"], {"value": "OK"})

    def test_unknown_directive(self):
        resp = skill_handler.lambda_handler(
            {"directive": {"header": {"namespace": "Alexa.Foo", "name": "Bar"}}}, None,
            svc=make_services())
        self.assertEqual(resp["event"]["payload"]["type"], "INVALID_DIRECTIVE")


if __name__ == "__main__":
    unittest.main()

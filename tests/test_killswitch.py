import os
import unittest
from unittest import mock

import fakes  # noqa: F401 - sets sys.path

from woa import killswitch


class FakeLambda:
    def __init__(self):
        self.calls = []

    def put_function_concurrency(self, **kwargs):
        self.calls.append(kwargs)


class KillSwitchTest(unittest.TestCase):
    def test_stops_all_target_functions(self):
        client = FakeLambda()
        with mock.patch.dict(os.environ, {"TARGET_FUNCTIONS": "woa-skill, woa-web"}):
            result = killswitch.lambda_handler({"Records": []}, None, client=client)
        self.assertEqual(result, {"stopped": ["woa-skill", "woa-web"]})
        self.assertEqual(client.calls, [
            {"FunctionName": "woa-skill", "ReservedConcurrentExecutions": 0},
            {"FunctionName": "woa-web", "ReservedConcurrentExecutions": 0},
        ])

    def test_no_targets_does_nothing(self):
        client = FakeLambda()
        with mock.patch.dict(os.environ, {"TARGET_FUNCTIONS": ""}):
            self.assertEqual(killswitch.lambda_handler({}, None, client=client), {"stopped": []})
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()

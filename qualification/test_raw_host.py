import importlib.util
import queue
import unittest
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'run_native.py'
spec = importlib.util.spec_from_file_location('run_native', MODULE)
run_native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_native)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class AdvancingQueue:
    def __init__(self, clock, items=()):
        self.clock = clock
        self.items = list(items)

    def get(self, timeout):
        self.clock.now += min(0.4, timeout)
        if self.items:
            return self.items.pop(0)
        raise queue.Empty


class FakeRequestClient(run_native.DeadlineClientMixin):
    def __init__(self, clock, responses):
        self.counter = 0
        self.sent = []
        self.start_deadline(1.0, clock)
        self.responses = AdvancingQueue(clock, responses)

    def _send(self, value):
        self.sent.append(value)


class RawHostTests(unittest.TestCase):
    def test_unrelated_messages_cannot_extend_absolute_deadline(self):
        clock = FakeClock()
        client = FakeRequestClient(clock, [{'id': -1}, {'id': 99}, {'id': 42}])
        with self.assertRaises(TimeoutError):
            client.request('tools/call', {})
        self.assertEqual(clock.now, 1.0)

    def test_json_rpc_and_tool_errors_fail(self):
        self.assertIn('JSON-RPC error', run_native.response_error({'jsonrpc': '2.0', 'id': 1, 'error': {'message': 'bad'}}))
        self.assertIn('isError', run_native.response_error({'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': 'bad'}], 'isError': True}}))
        self.assertIn('failure', run_native.response_error({'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': '{"ok":false}'}]}}))
        self.assertIn('failure', run_native.response_error({'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': '{"status":"FAIL"}'}]}}))

    def test_invalid_and_missing_response_fail(self):
        self.assertIn('invalid or missing', run_native.response_error(None))
        self.assertIn('invalid or missing', run_native.response_error({'jsonrpc': '2.0', 'id': 1}))

    def test_empty_missing_and_malformed_content_fail(self):
        for result in ({}, {'content': None}, {'content': []}, {'content': {}}, {'content': ['text']}, {'content': [{}]}, {'content': [{'type': 'text'}]}, {'content': [{'type': 'text', 'text': 42}]}, {'content': [{'type': 'image', 'data': 'x'}]}):
            with self.subTest(result=result):
                self.assertIn('content', run_native.response_error({'jsonrpc': '2.0', 'id': 1, 'result': result}))

    def test_invalid_version_and_mismatched_id_fail(self):
        valid = {'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': 'ok'}]}}
        self.assertIn('invalid or missing', run_native.response_error({**valid, 'jsonrpc': '1.0'}))
        self.assertIn('mismatched', run_native.response_error(valid, expected_id=2))

    def test_response_success_means_transport_only(self):
        response = {'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': '{"ok":true,"errors":0}'}]}}
        self.assertIsNone(run_native.response_error(response))
        self.assertIn('test acceptance was not evaluated', run_native.SUCCESS_CLASSIFICATION)


if __name__ == '__main__':
    unittest.main()

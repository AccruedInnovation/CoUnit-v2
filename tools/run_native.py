"""Host-side MCP invocation for the checked-in native scripts.

RAW_TRANSPORT_SUCCESS means the bridge returned a non-error response. It does
not qualify or accept any test results contained in that response.
"""
from pathlib import Path
import argparse
import json
import os
import queue
import shutil
import sys
import time

DEFAULT_TIMEOUT = 180.0
FALLBACK_REPOSITORY = Path(r'D:\AI\CodesysNewLib\repo')
SUCCESS_CLASSIFICATION = 'RAW_TRANSPORT_SUCCESS: script response received; test acceptance was not evaluated.'


def resolve_bridge_repository(explicit=None, environ=None):
    environ = os.environ if environ is None else environ
    candidates = [explicit, environ.get('CODESYS_REPOSITORY_ROOT'), FALLBACK_REPOSITORY]
    for candidate in candidates:
        if candidate:
            root = Path(candidate).expanduser().resolve()
            if (root / 'CIScripts' / 'mcp_client.py').is_file():
                return root
    raise FileNotFoundError('Could not locate CIScripts/mcp_client.py; pass --bridge-repository or set CODESYS_REPOSITORY_ROOT')


def load_client(repository):
    root = str(repository)
    if root not in sys.path:
        sys.path.insert(0, root)
    from CIScripts.mcp_client import Client
    return Client


class DeadlineClientMixin:
    """Bound all requests, including inherited Client initialization, to one deadline."""
    def start_deadline(self, timeout, monotonic=time.monotonic):
        self._deadline_clock = monotonic
        self._deadline = monotonic() + timeout

    def request(self, method, params):
        self.counter += 1
        request_id = self.counter
        self._send({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params})
        while True:
            remaining = self._deadline - self._deadline_clock()
            if remaining <= 0:
                raise TimeoutError(f'MCP {method} request timed out')
            try:
                response = self.responses.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError(f'MCP {method} request timed out') from exc
            if not isinstance(response, dict):
                continue
            if response.get('id') == request_id:
                if 'error' in response:
                    raise RuntimeError('JSON-RPC error: ' + json.dumps(response['error'], ensure_ascii=False))
                if 'result' not in response:
                    raise RuntimeError(f'MCP {method} returned an invalid response')
                return response


def _script_failure(value):
    if isinstance(value, dict):
        if value.get('isError') is True or 'error' in value or value.get('ok') is False or value.get('success') is False:
            return True
        status = str(value.get('status', '')).casefold()
        if status in {'error', 'fail', 'failed', 'failure'}:
            return True
        return any(_script_failure(v) for v in value.values())
    if isinstance(value, list):
        return any(_script_failure(v) for v in value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return False
        return _script_failure(parsed)
    return False


def response_error(response, expected_id=None):
    if not isinstance(response, dict) or response.get('jsonrpc') != '2.0' or 'id' not in response or ('result' not in response and 'error' not in response):
        return 'invalid or missing JSON-RPC response'
    if expected_id is not None and response['id'] != expected_id:
        return 'mismatched JSON-RPC response id'
    if 'error' in response:
        return 'JSON-RPC error: ' + json.dumps(response['error'], ensure_ascii=False)
    result = response['result']
    if not isinstance(result, dict):
        return 'invalid tool response'
    content = result.get('content')
    if not isinstance(content, list) or not content or any(not isinstance(block, dict) or block.get('type') != 'text' or not isinstance(block.get('text'), str) for block in content):
        return 'invalid or missing MCP content'
    if result.get('isError') is True:
        return 'MCP tool returned isError'
    if _script_failure(result):
        return 'script returned an error/failure result'
    return None


def run(script, arguments, bridge_repository=None, timeout=DEFAULT_TIMEOUT, client_type=None, monotonic=time.monotonic):
    repository = resolve_bridge_repository(bridge_repository)
    BaseClient = client_type or load_client(repository)

    class BoundedClient(DeadlineClientMixin, BaseClient):
        def __init__(self):
            self.start_deadline(timeout, monotonic)
            try:
                super().__init__()
            except BaseException:
                try:
                    self.close()
                except Exception:
                    pass
                raise

    destination = Path(os.environ['LOCALAPPDATA']) / 'AccruedInnovation/CODESYS-MCP-ScriptRunner/user_scripts' / ('counit2_' + script.name)
    shutil.copyfile(script, destination)
    client = None
    primary_error = None
    response = None
    try:
        client = BoundedClient()
        response = client.call('run_codesys_script', {
            'script_path': str(destination), 'arguments': [], 'trace': False,
            'input_json': arguments.read_text(encoding='utf-8'),
            'max_output_characters': 2000,
        })
        print(json.dumps(response, ensure_ascii=False))
        error = response_error(response, client.counter)
        if error:
            raise RuntimeError(error)
        print(SUCCESS_CLASSIFICATION, file=sys.stderr)
        return response
    except BaseException as exc:
        primary_error = exc
        if response is None:
            print(json.dumps({'transport_error': str(exc)}, ensure_ascii=False))
        raise
    finally:
        if client is not None:
            try:
                client.close()
            except Exception as exc:
                if primary_error is None:
                    raise RuntimeError(f'bridge close failed: {exc}') from exc
                print(f'bridge close failed after primary error: {exc}', file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('script', type=Path)
    parser.add_argument('arguments', type=Path)
    parser.add_argument('--bridge-repository', type=Path)
    parser.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    try:
        run(args.script, args.arguments, args.bridge_repository, args.timeout)
    except Exception as exc:
        print(f'run_native failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

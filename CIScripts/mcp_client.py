import os
import json
import queue
import subprocess
import threading
from pathlib import Path

BRIDGE = os.environ.get('CODESYS_MCP_BRIDGE', r'C:\Program Files\CODESYS 3.5.22.20\CODESYS\CODESYS MCP Server\1.1.0.0\CodesysMCPBridge\CodesysMCPBridge.exe')


class Client:
    def __init__(self):
        self.process = subprocess.Popen([BRIDGE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        self.responses = queue.Queue()
        self.counter = 0
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=lambda: list(self.process.stderr), daemon=True).start()
        self.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'configuration-harmonization', 'version': '1'}})
        self._send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def _read(self):
        for line in self.process.stdout:
            try:
                self.responses.put(json.loads(line))
            except ValueError:
                pass

    def _send(self, value):
        self.process.stdin.write(json.dumps(value) + '\n')
        self.process.stdin.flush()

    def request(self, method, params):
        self.counter += 1
        self._send({'jsonrpc': '2.0', 'id': self.counter, 'method': method, 'params': params})
        while True:
            result = self.responses.get(timeout=180)
            if result.get('id') == self.counter:
                return result

    def call(self, name, arguments):
        return self.request('tools/call', {'name': name, 'arguments': arguments})

    def close(self):
        self.process.terminate()
        self.process.wait(timeout=5)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    client = Client()
    try:
        response = client.call(request['name'], request.get('arguments', {}))
        if len(sys.argv) > 2:
            Path(sys.argv[2]).write_text(json.dumps(response, indent=2), encoding='utf-8')
        print(json.dumps(response, ensure_ascii=False))
    finally:
        client.close()

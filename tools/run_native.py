"""Host-side MCP invocation for the checked-in native scripts."""
from pathlib import Path
import argparse
import json
import os
import shutil
import sys

VERSION = Path(__file__).resolve().parents[1]
REPO = VERSION if (VERSION / 'CIScripts').is_dir() else VERSION.parents[2]
sys.path.insert(0, str(REPO))
from CIScripts.mcp_client import Client

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('script', type=Path)
    parser.add_argument('arguments', type=Path)
    args = parser.parse_args()
    destination = Path(os.environ['LOCALAPPDATA']) / 'AccruedInnovation/CODESYS-MCP-ScriptRunner/user_scripts' / ('counit2_' + args.script.name)
    shutil.copyfile(args.script, destination)
    client = Client()
    try:
        response = client.call('run_codesys_script', {
            'script_path': str(destination), 'arguments': [], 'trace': False,
            'input_json': args.arguments.read_text(encoding='utf-8'),
            'max_output_characters': 2000,
        })
        print(json.dumps(response))
    finally:
        client.close()

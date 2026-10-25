"""Run the requested Framelink Figma MCP using the local .env credential.

No credentials are passed on the command line or written to frontend files.
Without a file key this lists server capabilities; pass --file-key to read a design.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--file-key')
parser.add_argument('--node-id')
args = parser.parse_args()
credential = None
for line in (root / '.env').read_text(encoding='utf-8-sig').splitlines():
    name, sep, value = line.partition('=')
    if sep and name.strip().lower() in {'figma_api_key', 'figma_access_token'}:
        credential = value.strip().strip('\"\'')
if not credential:
    raise SystemExit('Figma API key is missing from the local .env file.')
env = os.environ.copy()
env['FIGMA_API_KEY'] = credential
process = subprocess.Popen(
    ['cmd.exe', '/d', '/s', '/c', 'npx -y figma-developer-mcp@0.13.2 --stdio'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    text=True, encoding='utf-8', env=env, cwd=root,
)
messages = queue.Queue()

def receive():
    for line in process.stdout:
        try:
            messages.put(json.loads(line))
        except json.JSONDecodeError:
            pass  # Server startup diagnostics are not protocol messages.

threading.Thread(target=receive, daemon=True).start()

def send(value):
    process.stdin.write(json.dumps(value) + '\n')
    process.stdin.flush()

def request(identifier, method, params):
    send({'jsonrpc': '2.0', 'id': identifier, 'method': method, 'params': params})
    while True:
        message = messages.get(timeout=180)
        if message.get('id') == identifier:
            if 'error' in message:
                raise RuntimeError('Figma MCP request failed; verify local configuration.')
            return message.get('result', {})

try:
    initialized = request(1, 'initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'heistbox-frontend', 'version': '1.0'}})
    send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    capabilities = request(2, 'tools/list', {})
    print(json.dumps({'server': initialized.get('serverInfo'), 'tools': [{'name': tool['name'], 'inputSchema': tool.get('inputSchema')} for tool in capabilities.get('tools', [])]}, indent=2))
    if args.file_key:
        params = {'fileKey': args.file_key}
        if args.node_id:
            params['nodeId'] = args.node_id
        design = request(3, 'tools/call', {'name': 'get_figma_data', 'arguments': params})
        print(json.dumps(design, ensure_ascii=False).replace(credential, '[redacted]'))
finally:
    # Stop this tool's process tree, including its npx server child.
    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

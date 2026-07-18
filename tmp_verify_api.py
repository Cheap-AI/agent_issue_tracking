import json
import urllib.request

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/issues',
    data=json.dumps({'title': 'New issue', 'summary': 'A freshly created issue.'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST',
)

try:
    with urllib.request.urlopen(req) as resp:
        print(resp.status)
        print(resp.read().decode())
except Exception as exc:
    print(type(exc).__name__, exc)

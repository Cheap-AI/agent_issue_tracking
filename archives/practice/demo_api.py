import json
import urllib.request

payload = json.dumps({"title": "Sample Doc", "content": "Hello from the API"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/documents",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as response:
    print(response.status)
    print(response.read().decode())

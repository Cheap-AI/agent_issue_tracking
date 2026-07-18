import urllib.request

req = urllib.request.Request('http://127.0.0.1:8001/documents')
req.add_header('Origin', 'http://localhost:3002')
with urllib.request.urlopen(req) as response:
    print(response.status)
    print(response.read().decode())
    print(response.headers.get('access-control-allow-origin'))

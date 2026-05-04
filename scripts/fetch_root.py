import requests

resp = requests.get("http://127.0.0.1:8000/")
print(resp.status_code)
print(resp.text[:1000])

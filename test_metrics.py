import requests
import json
import time

res = requests.post("http://localhost:8000/scan-test", json={"file_name": "01-valid.iso"}, stream=True)
for line in res.iter_lines():
    print(line)

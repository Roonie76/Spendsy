import requests
import os
import json

# Get API key from .env
with open(".env", "r") as f:
    lines = f.readlines()
    key = None
    for line in lines:
        if line.startswith("GOOGLE_API_KEY="):
            key = line.split("=")[1].strip()
            break

if not key:
    print("API Key not found in .env")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
res = requests.get(url)
if res.status_code == 200:
    models = res.json().get("models", [])
    for m in models:
        print(f"Model: {m['name']} | Supported: {m['supportedGenerationMethods']}")
else:
    print(f"Failed to list models: {res.status_code} {res.text}")


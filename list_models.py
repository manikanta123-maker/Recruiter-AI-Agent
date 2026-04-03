import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        models = json.loads(resp.read().decode())
        if 'models' in models:
            for m in models['models']:
                print(m['name'])
        else:
            print(models)
except Exception as e:
    print(e)

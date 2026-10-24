import urllib.request, json, os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Shaik\Downloads\heistbox\.env")
k = os.getenv("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={k}"
with urllib.request.urlopen(url) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    for m in data.get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"])

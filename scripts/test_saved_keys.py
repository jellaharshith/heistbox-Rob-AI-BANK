import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

# 1. Test Apify
apify_token = os.getenv("APIFY_API_TOKEN", "")
if apify_token:
    try:
        req = urllib.request.Request(
            "https://api.apify.com/v2/users/me",
            headers={"Authorization": f"Bearer {apify_token}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            user_data = json.loads(resp.read().decode("utf-8")).get("data", {})
            print(f"[APIFY] SUCCESS! User: {user_data.get('username')} ({user_data.get('email')})")
    except Exception as e:
        print(f"[APIFY] FAILED: {e}")
else:
    print("[APIFY] Skipped: APIFY_API_TOKEN not set")

# 2. Test Cartesia
cartesia_key = os.getenv("CARTESIA_API_KEY", "").strip()
if cartesia_key:
    try:
        req = urllib.request.Request(
            "https://api.cartesia.ai/voices",
            headers={"X-API-Key": cartesia_key, "Cartesia-Version": "2024-06-10"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            voices = json.loads(resp.read().decode("utf-8"))
            print(f"[CARTESIA] SUCCESS! Found {len(voices)} voices.")
    except urllib.error.HTTPError as e:
        print(f"[CARTESIA] FAILED HTTP {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[CARTESIA] FAILED: {e}")
else:
    print("[CARTESIA] Skipped: CARTESIA_API_KEY not set")

# 3. Test Gemini
gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
if gemini_key:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            models = json.loads(resp.read().decode("utf-8"))
            print(f"[GEMINI] SUCCESS! Models available: {len(models.get('models', []))}")
    except urllib.error.HTTPError as e:
        print(f"[GEMINI] FAILED HTTP {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[GEMINI] FAILED: {e}")
else:
    print("[GEMINI] Skipped: GEMINI_API_KEY not set")

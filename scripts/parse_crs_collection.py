import json
import re

collection_path = r"C:\Users\Shaik\Downloads\heistbox\calhacks13-20261023-CRS-Sandbox (1).json"

with open(collection_path, "r", encoding="utf-8") as f:
    text = f.read()
    data = json.loads(text)

usernames = re.findall(r'"username":\s*"([^"]+)"', text)
passwords = re.findall(r'"password":\s*"([^"]+)"', text)
tokens = re.findall(r'"token":\s*"([^"]+)"', text)
print("Usernames:", set(usernames))
print("Passwords:", set(passwords))
print(f"Tokens found: {len(tokens)}")

# Look for saved responses or test scripts
sample_records = []
def scan_items(items):
    for it in items:
        if "item" in it:
            scan_items(it["item"])
        else:
            name = it.get("name", "")
            req = it.get("request", {})
            responses = it.get("response", [])
            for resp in responses:
                body = resp.get("body", "")
                if body and len(body) > 10:
                    sample_records.append((name, resp.get("status"), len(body), body[:200]))

scan_items(data.get("item", []))
print(f"Total saved responses with real sandbox payloads: {len(sample_records)}")
for name, status, length, sample in sample_records[:10]:
    print(f"  [{status}] {name} ({length} bytes): {sample[:80]}...")

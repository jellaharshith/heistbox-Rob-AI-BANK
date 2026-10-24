import json

collection_path = r"C:\Users\Shaik\Downloads\heistbox\calhacks13-20261023-CRS-Sandbox (1).json"
with open(collection_path, "r", encoding="utf-8") as f:
    data = json.load(f)

personas = []
for item in data.get("item", []):
    if "Test personas" in item.get("name", ""):
        for p in item.get("item", []):
            p_name = p.get("name", "")
            reqs = []
            for sub in p.get("item", []):
                req_obj = sub.get("request", {})
                body = req_obj.get("body", {}).get("raw", "")
                url = req_obj.get("url", "")
                if isinstance(url, dict):
                    url = url.get("raw", "")
                reqs.append({
                    "name": sub.get("name"),
                    "method": req_obj.get("method"),
                    "url": url,
                    "body": body[:300] if body else ""
                })
            personas.append({"persona": p_name, "requests": reqs})

print(f"Found {len(personas)} test personas in CRS sandbox:")
for p in personas[:5]:
    print(f"\nPersona: {p['persona']}")
    for r in p["requests"][:3]:
        print(f"  - {r['name']} ({r['method']} {r['url']})")
        if r['body']:
            print(f"    Body snippet: {r['body'][:120]}...")

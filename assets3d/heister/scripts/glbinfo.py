import json, struct, sys, os
p = os.environ["GLB"]
b = open(p, "rb").read()
magic, ver, length = struct.unpack("<4sII", b[:12])
off = 12; js = None
while off < len(b):
    cl, ct = struct.unpack("<II", b[off:off + 8]); data = b[off + 8:off + 8 + cl]
    if ct == 0x4E4F534A:
        js = json.loads(data)
    off += 8 + cl
print("file", os.path.getsize(p), "extensionsUsed", js.get("extensionsUsed"), "required", js.get("extensionsRequired"))
print("nodes", len(js["nodes"]), "meshes", len(js["meshes"]), "skins", [(s.get("name"), len(s["joints"])) for s in js.get("skins", [])], "materials", [m["name"] for m in js["materials"]])
print("images", [(i.get("name"), i.get("mimeType")) for i in js["images"]], "textures", len(js["textures"]))
for a in js.get("animations", []):
    paths = {}
    for c in a["channels"]:
        pth = c["target"]["path"]; paths[pth] = paths.get(pth, 0) + 1
    mx = 0
    for s in a["samplers"]:
        acc = js["accessors"][s["input"]]; mx = max(mx, acc["max"][0])
    print("ANIM", a["name"], "channels", len(a["channels"]), paths, "duration", round(mx, 3))
for i, m in enumerate(js["meshes"]):
    pr = m["primitives"][0]
    print("MESH", m.get("name"), "targets", len(pr.get("targets", [])), "tgtnames", (m.get("extras") or {}).get("targetNames", [])[:3], "attrs", list(pr["attributes"]))
for n in js["nodes"]:
    if "extras" in n:
        print("NODE", n["name"], n.get("extras"), "mesh" in n, "children" in n)


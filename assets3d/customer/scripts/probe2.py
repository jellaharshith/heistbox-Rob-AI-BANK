import bpy, numpy as np
bm=bpy.data.objects["Body_full"]; rig=bpy.data.objects["Armature_Customer"]
for b in rig.data.bones:
    if not b.name.split(":")[1].startswith(("LeftHand","RightHand")) or b.name.endswith("Index1"):
        print("BONE", b.name, tuple(round(x,3) for x in b.head_local), tuple(round(x,3) for x in b.tail_local), b.parent.name if b.parent else None)
print("GROUPS", [vg.name for vg in bm.vertex_groups if not vg.name.startswith(("joint","mixamo"))])
for g in ["helper-l-eye","helper-r-eye"]:
    gi=bm.vertex_groups[g].index
    pts=np.array([v.co[:] for v in bm.data.vertices if any(x.group==gi and x.weight>.5 for x in v.groups)])
    print(g, len(pts), pts.min(0).round(3), pts.max(0).round(3))
bg=bm.vertex_groups["body"].index
pts=np.array([v.co[:] for v in bm.data.vertices if any(x.group==bg and x.weight>.5 for x in v.groups)])
print("body", len(pts), pts.min(0).round(3), pts.max(0).round(3))
print("mods", [m.type for m in bm.modifiers], "uv", [u.name for u in bm.data.uv_layers])

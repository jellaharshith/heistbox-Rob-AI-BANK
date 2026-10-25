import bpy, os, sys, json
import numpy as np
path = os.environ["GLB"]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
O = bpy.data.objects
print("== objects")
tot = {}
for o in O:
    if o.type == 'MESH':
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        sk = len(o.data.shape_keys.key_blocks) - 1 if o.data.shape_keys else 0
        print(f"MESH {o.name:36s} tris {t:6d} verts {len(o.data.vertices):6d} shapekeys {sk:3d} groups {len(o.vertex_groups):3d} mats {[m.name for m in o.data.materials]} parent {o.parent.name if o.parent else None}/{o.parent_type}/{o.parent_bone}")
        lod = [x for x in ("LOD0", "LOD1", "LOD2") if x in o.name]
        if lod:
            tot[lod[0]] = tot.get(lod[0], 0) + t
        # max weights per vertex
        if o.vertex_groups:
            mx = max(len([g for g in v.groups if g.weight > 1e-4]) for v in o.data.vertices)
            print("   max influences", mx)
    elif o.type == 'ARMATURE':
        print("ARMATURE", o.name, "bones", len(o.data.bones), [b.name for b in o.data.bones][:6], "...")
    else:
        print(o.type, o.name)
print("LOD tri totals", tot)
print("== animations")
for a in bpy.data.actions:
    fr = a.frame_range
    print("ACTION", a.name, "frames", tuple(fr), "fcurves", sum(len(cb.fcurves) for l in a.layers for s in l.strips for cb in s.channelbags) if hasattr(a, "layers") else len(a.fcurves))
print("fps", bpy.context.scene.render.fps)
print("images", [(i.name, i.size[:]) for i in bpy.data.images])
sk_names = None
for o in O:
    if o.type == 'MESH' and o.data.shape_keys and "Body_LOD0" in o.name:
        sk_names = [k.name for k in o.data.shape_keys.key_blocks]
print("body shape keys", sk_names)

"""Stage 7: LOD1/LOD2 (decimated, UV/seam protected, weights + shape keys transferred) + LOD0 renames. s6 -> s7"""
import bpy, os, sys, math, json
import numpy as np
from mathutils import Vector, Matrix
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
from hlib import *
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s6.blend"))
O = bpy.data.objects; sc = bpy.context.scene
rig = O["CHAR_Heister"]
coll = bpy.data.collections["CHAR_Heister"]
base_names = {"Body": "CHAR_Heister_Body", "Mask": "CHAR_Heister_Mask", "Duffel": "CHAR_Heister_Duffel", "EyeL": "CHAR_Heister_EyeL", "EyeR": "CHAR_Heister_EyeR"}
lod0 = {k: O[v] for k, v in base_names.items()}
box = json.load(open(os.path.join(H, "scripts", "uvinfo.json")))["eye_box"]

def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

def link(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    coll.objects.link(o)

def protect_group(obj):
    me = obj.data
    uvd = me.uv_layers.active.data
    seen = {}
    for lp in me.loops:
        uv = (round(uvd[lp.index].uv.x, 4), round(uvd[lp.index].uv.y, 4))
        seen.setdefault(lp.vertex_index, set()).add(uv)
    seam = [v for v, s in seen.items() if len(s) > 1]
    bm = bmesh.new(); bm.from_mesh(me)
    bnd = [v.index for v in bm.verts if v.is_boundary]
    bm.free()
    vg = obj.vertex_groups.new(name="keep")
    vg.add(list(set(seam) | set(bnd)), 1.0, 'REPLACE')
    return len(set(seam) | set(bnd))

def make_lod(src, target, name, keys=True, weights=True, protect=True):
    c = src.copy(); c.data = src.data.copy(); c.name = name; c.data.name = name
    coll.objects.link(c)
    # drop shape keys, modifiers, groups
    if c.data.shape_keys:
        for kb in list(c.data.shape_keys.key_blocks)[::-1]:
            c.shape_key_remove(kb)
    c.modifiers.clear()
    for g in list(c.vertex_groups):
        c.vertex_groups.remove(g)
    c.parent = None
    nprot = protect_group(c) if protect else 0
    bpy.ops.object.select_all(action='DESELECT')
    c.select_set(True); bpy.context.view_layer.objects.active = c
    cur = tris(c)
    md = c.modifiers.new("dec", 'DECIMATE')
    md.decimate_type = 'COLLAPSE'; md.ratio = max(0.02, target / cur)
    if protect:
        md.vertex_group = "keep"; md.invert_vertex_group = True; md.vertex_group_factor = 1.0
    md.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=md.name)
    if protect:
        c.vertex_groups.remove(c.vertex_groups["keep"])
    print(name, "tris", cur, "->", tris(c), "protected verts", nprot)
    return c

def transfer_all(dst, src, keys=True):
    tr = Transfer(src)
    names = [g.name for g in src.vertex_groups]
    W = np.zeros((len(src.data.vertices), len(names)), np.float32)
    for v in src.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    idx, bar = tr.weights_for(dst)
    assign_weights(dst, Transfer.apply(W, idx, bar), names)
    if keys and src.data.shape_keys:
        kbs = src.data.shape_keys.key_blocks
        base = coords(src.data)
        deltas = {}
        for kb in list(kbs)[1:]:
            arr = np.zeros(len(base) * 3, np.float32); kb.data.foreach_get("co", arr)
            deltas[kb.name] = Transfer.apply(arr.reshape(-1, 3) - base, idx, bar).astype(np.float32)
        add_shape_keys(dst, deltas)

def finish(o, level, kind):
    md = o.modifiers.new("Armature", 'ARMATURE'); md.object = rig
    o.parent = rig
    o["lod"] = level
    o.data.materials.clear(); o.data.materials.append(lod0["Body"].data.materials[0])
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))

def make_eye(side, level, seg, rings):
    src = lod0["Eye" + side]
    c = np.mean([v.co[:] for v in src.data.vertices], axis=0)
    r = 0.0118
    verts = []; faces = []
    for ri in range(rings + 1):
        th = math.pi * ri / rings
        for s in range(seg):
            ph = 2 * math.pi * s / seg
            p = (r * math.sin(th) * math.cos(ph), r * math.cos(th), -r * math.sin(th) * math.sin(ph))  # pole along +Y
            verts.append((c[0] + p[0], c[1] + p[1], c[2] + p[2]))
    for ri in range(rings):
        for s in range(seg):
            a = ri * seg + s; b = ri * seg + (s + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    me = bpy.data.meshes.new(f"CHAR_Heister_Eye{side}_LOD{level}")
    me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(me.name, me)
    coll.objects.link(o)
    # planar UV (front, viewed from -Y)
    me.uv_layers.new(name="UVMap")
    uvd = me.uv_layers.active.data
    for lp in me.loops:
        p = np.array(me.vertices[lp.vertex_index].co[:]) - c
        uvd[lp.index].uv = (box[0] + box[2] * (0.5 + 0.5 * p[0] / r), box[1] + box[2] * (0.5 + 0.5 * p[2] / r))
    names = [g.name for g in lod0["Eye" + side].vertex_groups]
    vg = o.vertex_groups.new(name="mixamorig:Head"); vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    return o

# ---- LOD0 rename (suffix) and tag
for k, o in lod0.items():
    o.name = o.name + "_LOD0"; o.data.name = o.name
    o["lod"] = 0
LOD = {0: lod0}
# ---- LOD1 / LOD2
spec = {1: dict(Body=5000, Mask=200, Duffel=300, eye=(10, 6)), 2: dict(Body=1900, Mask=90, Duffel=150, eye=(6, 4))}
for lv, sp in spec.items():
    d = {}
    d["Body"] = make_lod(lod0["Body"], sp["Body"], f"CHAR_Heister_Body_LOD{lv}", protect=(lv == 1))
    transfer_all(d["Body"], lod0["Body"])
    d["Mask"] = make_lod(lod0["Mask"], sp["Mask"], f"CHAR_Heister_Mask_LOD{lv}", protect=(lv == 1))
    transfer_all(d["Mask"], lod0["Mask"])
    d["Duffel"] = make_lod(lod0["Duffel"], sp["Duffel"], f"CHAR_Heister_Duffel_LOD{lv}", protect=False)
    for side in "LR":
        d["Eye" + side] = make_eye(side, lv, *sp["eye"])
    LOD[lv] = d
    for k, o in d.items():
        finish(o, lv, k)
# duffel LODs: rigid bone parent like LOD0 (remove armature modifier)
src_d = lod0["Duffel"]
for lv in (1, 2):
    o = LOD[lv]["Duffel"]
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = src_d.parent_bone
    o.matrix_parent_inverse = src_d.matrix_parent_inverse.copy()
    o["lod"] = lv
# eyes LOD1/2 weights: head only (already single group); eye materials set in finish
# ---- face-key animation on LOD1/LOD2 meshes (reuse the LOD0 shape-key actions through NLA)
order = [t.name for t in lod0["Body"].data.shape_keys.animation_data.nla_tracks]
for lv in (1, 2):
    for kind in ("Body", "Mask"):
        key = LOD[lv][kind].data.shape_keys
        ad = key.animation_data or key.animation_data_create()
        for cname in order:
            act = bpy.data.actions[f"{cname}_{kind}Keys"]
            tr = ad.nla_tracks.new(); tr.name = cname
            st = tr.strips.new(cname, 1, act); st.name = cname
            try:
                st.action_slot = act.slots[0]
            except Exception as e:
                print("slot", e)
            st.extrapolation = 'NOTHING'
        ad.action = None
# ---- toggle groups: CHAR_Heister_Mask (empty at rig root, identity) > Mask LODs ; CHAR_Heister_Duffel (empty on the spine bone, identity world) > Duffel LODs
bpy.context.view_layer.update()
for pb in rig.pose.bones:
    pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
bpy.context.view_layer.update()
def group_empty(name, size):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'; e.empty_display_size = size
    coll.objects.link(e)
    return e
mask_objs = [LOD[lv]["Mask"] for lv in (0, 1, 2)]
duf_objs = [LOD[lv]["Duffel"] for lv in (0, 1, 2)]
Wm = {o.name: o.matrix_world.copy() for o in mask_objs + duf_objs}
em = group_empty("CHAR_Heister_Mask", 0.05)
em.parent = rig; em.matrix_parent_inverse = rig.matrix_world.inverted(); em.matrix_basis = Matrix.Identity(4)
for o in mask_objs:
    o.parent = em; o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_basis = em.matrix_world.inverted() @ Wm[o.name]
ed = group_empty("CHAR_Heister_Duffel", 0.08)
bone = src_d.parent_bone
ed.parent = rig; ed.parent_type = 'BONE'; ed.parent_bone = bone
pbd = rig.pose.bones[bone]
ed.matrix_parent_inverse = (rig.matrix_world @ pbd.matrix @ Matrix.Translation((0, pbd.bone.length, 0))).inverted()
ed.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
print("duffel group world", [round(x, 4) for x in ed.matrix_world.translation], "bone", bone)
for o in duf_objs:
    o.parent_type = 'OBJECT'; o.parent = ed; o.matrix_parent_inverse = Matrix.Identity(4); o.matrix_basis = ed.matrix_world.inverted() @ Wm[o.name]
bpy.context.view_layer.update()
for o in mask_objs + duf_objs:
    d = (o.matrix_world - Wm[o.name])
    assert max(abs(x) for r in d for x in r) < 1e-5, ("moved", o.name)
print("groups ok")
# ---- report
rep = {}
for lv in (0, 1, 2):
    objs = LOD[lv]
    rep[lv] = {k: tris(o) for k, o in objs.items()}
    print("LOD", lv, rep[lv], "TOTAL", sum(rep[lv].values()))
json.dump({str(k): v for k, v in rep.items()}, open(os.path.join(H, "scripts", "lod_report.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s7.blend"))



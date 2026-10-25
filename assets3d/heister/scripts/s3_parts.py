"""Stage 3: carve garments (hi-res, exact clipped borders) from body, decimate to low-poly, split skin,
transfer weights/shape keys.  Input heister_s2.blend -> heister_s3.blend"""
import bpy, bmesh, os, sys, json
import numpy as np
from mathutils import Vector
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
import hlib
from hlib import *
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s2.blend"))
body = bpy.data.objects["Body_hi"]; rig = bpy.data.objects["Rig"]
me = body.data
P = coords(me)
N = vertex_normals(me)
me.calc_loop_triangles()
TRIS = np.array([[t.vertices[0], t.vertices[1], t.vertices[2]] for t in me.loop_triangles], dtype=np.int64)
W, gnames = src_weight_matrix(body)
_bn = [i for i, n in enumerate(gnames) if n in rig.data.bones]
W = W[:, _bn]; gnames = [gnames[i] for i in _bn]
keys = np.load(os.path.join(H, "scripts", "facekeys_hi.npz"))
dom = np.array(gnames)[W.argmax(1)]
B = {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in rig.data.bones}
X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
n = len(P)
sm = smoothstep

def isd(*names):
    return np.isin(dom, names)

def both(nm):
    return [nm + "_l", nm + "_r"]

hem_z = B["pelvis"][0][2] + 0.04
neck_z = B["neck_01"][0][2]
foot_z = B["foot_l"][0][2]
hv = isd("head")
blink = np.linalg.norm(keys["eyeBlinkLeft"], axis=1)
eye_z = float(P[blink > 0.0008][:, 2].mean())
hc = P[hv].mean(axis=0)
head_top = float(Z[hv].max())
chin_z = eye_z - 0.118
print("hem", hem_z, "neck", neck_z, "foot", foot_z, "eye_z", eye_z, "hc", hc, "head_top", head_top)

FINGERS = ["index", "middle", "ring", "pinky"]
T = {}; arm_dom = {}
for s in "lr":
    ax = B["hand_" + s][0] - B["lowerarm_" + s][0]; ax = ax / np.linalg.norm(ax)
    T[s] = (P - B["hand_" + s][0]) @ ax
    names = ["clavicle_" + s, "upperarm_" + s, "lowerarm_" + s, "hand_" + s] + \
            [f"{f}_0{i}_{s}" for f in FINGERS + ["thumb"] for i in (1, 2, 3)]
    arm_dom[s] = isd(*names)

torso_dom = isd("pelvis", "spine_01", "spine_02", "spine_03", *both("thigh"), *both("calf"), *both("foot"), *both("ball"))
neckhead = isd("neck_01", "head")
neck_top = neck_z + 0.03

# ---------------- region fields (metres, >=0 inside)
F = {}
f = np.full(n, -1.0, dtype=np.float32)
f = np.where(torso_dom, Z - hem_z, f)
f = np.where(neckhead, neck_top - Z, f)
for s in "lr":
    f = np.where(arm_dom[s], -T[s], f)
F["Hoodie"] = f.astype(np.float32)

legdom = isd("pelvis", "spine_01", *both("thigh"), *both("calf"), *both("foot"), *both("ball"))
F["Pants"] = np.where(legdom, np.minimum((hem_z + 0.07) - Z, Z - (foot_z + 0.06)), -1.0).astype(np.float32)
F["Shoes"] = np.where(isd(*both("calf"), *both("foot"), *both("ball")), (foot_z + 0.075) - Z, -1.0).astype(np.float32)

f = np.full(n, -1.0, dtype=np.float32)
for s in "lr":
    f = np.where(isd("lowerarm_" + s), T[s] + 0.045, f)
    f = np.where(isd("hand_" + s), 0.1, f)
    for fn in FINGERS + ["thumb"]:
        chain = isd(f"{fn}_01_{s}", f"{fn}_02_{s}", f"{fn}_03_{s}")
        h1, t1 = B[f"{fn}_01_{s}"]
        d1 = (t1 - h1) / np.linalg.norm(t1 - h1)
        f = np.where(chain, (t1 - P) @ d1 + (0.004 if fn != "thumb" else 0.0), f)
F["Gloves"] = f.astype(np.float32)

s_back = np.clip((Y - (hc[1] - 0.03)) / 0.09, 0, 1)
beanie_thr = eye_z + 0.028 - 0.085 * s_back + 0.04 * sm(0.065, 0.09, np.abs(X)) * (1 - s_back)
F["Beanie"] = np.where(hv, Z - beanie_thr, -1.0).astype(np.float32)
mask_top = eye_z - 0.027 + 0.013 * (1 - sm(0.0, 0.04, np.abs(X)))
F["Mask"] = np.where(hv, np.minimum.reduce([mask_top - Z, Z - chin_z, (hc[1] - 0.012) - Y]), -1.0).astype(np.float32)

# ---------------- offsets
D = {}
D["Hoodie"] = 0.019 + 0.003 * (isd(*both("upperarm"), *both("lowerarm")))
cuff = np.zeros(n, dtype=np.float32)
for s in "lr":
    cuff = np.where(isd("lowerarm_" + s, "hand_" + s), sm(-0.07, -0.01, T[s]), cuff)
D["Hoodie"] = D["Hoodie"] - 0.011 * cuff
D["Pants"] = 0.011 + 0.003 * isd(*both("thigh")) + 0.012 * sm(foot_z + 0.35, foot_z + 0.06, Z) * isd(*both("calf"))
sole_low = float(Z[isd(*both("foot"), *both("ball"))].min())
D["Shoes"] = 0.005 + 0.009 * (1 - sm(sole_low, sole_low + 0.035, Z))
D["Gloves"] = np.full(n, 0.0035)
D["Beanie"] = 0.009 + 0.008 * (1 - sm(0, 0.035, F["Beanie"]))
D["Mask"] = np.full(n, 0.0045)
TARGET = {"Hoodie": 3300, "Pants": 2500, "Shoes": 900, "Gloves": 640, "Beanie": 600, "Mask": 330}

coll = bpy.data.collections.new("CHAR_Heister"); bpy.context.scene.collection.children.link(coll)
hi_coll = bpy.data.collections.new("HI_src"); bpy.context.scene.collection.children.link(hi_coll)

def move_to(o, c):
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    c.objects.link(o)

hi = {}; lo = {}
for name in ["Hoodie", "Pants", "Shoes", "Gloves", "Beanie", "Mask"]:
    o, pos0, nrm0, dd = clip_mesh(P, N, D[name], TRIS, F[name], name + "_hi")
    if name == "Shoes":
        # sneaker = convex hull of each foot (fills arch, merges toes), offset + longer toe box + thick sole
        pts = coords(o.data)
        bm = bmesh.new()
        for side in (1, -1):
            sel = pts[pts[:, 0] * side > 0]
            vs = [bm.verts.new(p.tolist()) for p in sel]
            res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
            bmesh.ops.delete(bm, geom=res["geom_interior"], context='VERTS')
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.normal_update()
        for v in bm.verts:
            v.co += v.normal * 0.0095
        ymin = min(v.co.y for v in bm.verts)
        zlo = min(v.co.z for v in bm.verts)
        for v in bm.verts:
            v.co.y -= 0.02 * float(smoothstep(ymin + 0.12, ymin, v.co.y))
            v.co.z -= 0.019 * float(1 - smoothstep(zlo + 0.002, zlo + 0.03, v.co.z))
        bm.to_mesh(o.data); bm.free(); o.data.update()
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        hull_lo = o.copy(); hull_lo.data = o.data.copy()
        bpy.context.scene.collection.objects.link(hull_lo)
        # hi-res = subdivided hull
        bpy.context.view_layer.objects.active = o
        md = o.modifiers.new("sub", 'SUBSURF'); md.levels = 2; md.render_levels = 2
        bpy.ops.object.modifier_apply(modifier=md.name)
        pos = None
    else:
        pos = pos0 + nrm0 * dd[:, None]
    if pos is not None:
        set_coords(o.data, pos)
    move_to(o, hi_coll); hi[name] = o
    if name == "Shoes":
        l = hull_lo; l.name = name; l.data.name = name
    else:
        l = o.copy(); l.data = o.data.copy(); l.name = name
        bpy.context.scene.collection.objects.link(l)
    nt = decimate_to(l, TARGET[name])
    if name == "Hoodie":
        relax_boundary(l, neck_z - 0.1, 25); relax_boundary(o, neck_z - 0.1, 25)
    move_to(l, coll); lo[name] = l
    print(name, "hi tris", len(o.data.polygons), "lo tris", nt)

# ---------------- skin: complement
fs = -np.maximum.reduce([F[k] for k in F])
fs = fs.astype(np.float32)
sk_hi, p0, n0, d0 = clip_mesh(P, N, np.zeros(n, dtype=np.float32), TRIS, fs, "Skin_hi")
move_to(sk_hi, hi_coll)
isl = islands(sk_hi.data)
Pk = coords(sk_hi.data)
parts = {}
for i_id in np.unique(isl):
    vs = np.where(isl == i_id)[0]
    c = Pk[vs].mean(axis=0)
    key = "head" if c[2] > 1.35 else ("handL" if c[0] > 0 else "handR")
    parts.setdefault(key, set()).update(vs.tolist())
print({k: len(v) for k, v in parts.items()})
SK_T = {"head": 2300, "handL": 330, "handR": 330}
skin_parts = []
for key, vs in parts.items():
    vm = np.zeros(len(Pk), dtype=bool); vm[list(vs)] = True
    bm = bmesh.new(); bm.from_mesh(sk_hi.data); bm.faces.ensure_lookup_table()
    kill = [fc for fc in bm.faces if not vm[fc.verts[0].index]]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    o = new_obj_from_bm(bm, "Skin_" + key); bm.free()
    nt = decimate_to(o, SK_T[key])
    print("skin", key, nt)
    skin_parts.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in skin_parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = skin_parts[0]
bpy.ops.object.join()
skin = bpy.context.view_layer.objects.active
skin.name = "Skin"; skin.data.name = "Skin"
move_to(skin, coll)
lo["Skin"] = skin

# ---------------- transfer weights + face keys
tr = Transfer(body)
for name, o in lo.items():
    idx, bar = tr.weights_for(o)
    Wd = Transfer.apply(W, idx, bar)
    assign_weights(o, Wd, gnames)
    if name in ("Skin", "Mask"):
        deltas = {k: Transfer.apply(keys[k], idx, bar).astype(np.float32) for k in keys.files}
        add_shape_keys(o, deltas)
cL = P[blink > 0.0008].mean(axis=0)
blinkR = np.linalg.norm(keys["eyeBlinkRight"], axis=1)
cR = P[blinkR > 0.0008].mean(axis=0)
json.dump({"eyeL": cL.tolist(), "eyeR": cR.tolist(), "eye_z": eye_z, "head_top": head_top, "chin_z": chin_z,
           "hem_z": float(hem_z), "hc": hc.tolist(), "neck_z": float(neck_z), "foot_z": float(foot_z)},
          open(os.path.join(H, "scripts", "landmarks.json"), "w"))
body.hide_viewport = True; body.hide_render = True
move_to(body, hi_coll); move_to(rig, coll)
tot = 0
for name, o in lo.items():
    t = sum(len(p.vertices) - 2 for p in o.data.polygons); tot += t
    print("LO", name, t)
print("LO TOTAL", tot)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s3.blend"))




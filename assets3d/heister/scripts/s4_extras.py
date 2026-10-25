"""Stage 4: ground-lift, extras (hood, drawstrings, cargo pockets, eyes, duffel + straps), mixamo rename, join, parent.
Input heister_s3.blend -> heister_s4.blend"""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
from hlib import *
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s3.blend"))
LM = json.load(open(os.path.join(H, "scripts", "landmarks.json")))
sc = bpy.context.scene
O = bpy.data.objects
rig = O["Rig"]; body_hi = O["Body_hi"]
LO = {k: O[k] for k in ["Skin", "Hoodie", "Pants", "Shoes", "Gloves", "Beanie", "Mask"]}
HI = {k: O[k + "_hi"] for k in ["Hoodie", "Pants", "Shoes", "Gloves", "Beanie", "Mask"]}
HI["Skin"] = O["Skin_hi"]

# ---------------------------------------------------------------- ground lift
zmin = min(min(v.co.z for v in LO[k].data.vertices) for k in LO)
lift = -zmin
print("lift", lift)
for o in list(O):
    if o.type == 'MESH':
        for v in o.data.vertices:
            v.co.z += lift
        if o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks:
                for d in kb.data:
                    d.co.z += lift
        o.data.update()
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for eb in rig.data.edit_bones:
    eb.head.z += lift; eb.tail.z += lift
bpy.ops.object.mode_set(mode='OBJECT')
for k in ("eyeL", "eyeR"):
    LM[k][2] += lift
for k in ("eye_z", "head_top", "chin_z", "hem_z", "neck_z", "foot_z"):
    LM[k] += lift
LM["hc"][2] += lift

# ---------------------------------------------------------------- helpers
PART = {"Skin": 1, "Hoodie": 2, "Pants": 3, "Shoes": 4, "Gloves": 5, "Beanie": 6, "Mask": 7, "Duffel": 8, "Eye": 9, "Cords": 10}
def setpart(o, pid):
    a = o.data.attributes.get("part") or o.data.attributes.new("part", "FLOAT", "POINT")
    a.data.foreach_set("value", [float(pid)] * len(o.data.vertices))
for _k, _o in LO.items():
    setpart(_o, PART[_k])
tr = Transfer(body_hi)
W_hi, gnames = src_weight_matrix(body_hi)
_bn = [i for i, n in enumerate(gnames) if n in rig.data.bones]
W_hi = W_hi[:, _bn]; gnames = [gnames[i] for i in _bn]

def mk(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    return o

def tube(path, radius, sides=6, cap=True):
    path = [Vector(p) for p in path]
    verts = []; faces = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        a = t.cross(Vector((0, 1, 0)))
        if a.length < 1e-3:
            a = t.cross(Vector((1, 0, 0)))
        a.normalize(); b = t.cross(a).normalized()
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            verts.append(p + (a * math.cos(ang) + b * math.sin(ang)) * radius)
    for i in range(len(path) - 1):
        for s in range(sides):
            a0 = i * sides + s; a1 = i * sides + (s + 1) % sides
            faces.append((a0, a1, a1 + sides, a0 + sides))
    if cap:
        verts.append(path[0]); verts.append(path[-1])
        c0 = len(verts) - 2; c1 = len(verts) - 1
        for s in range(sides):
            faces.append((c0, (s + 1) % sides, s))
            e = (len(path) - 1) * sides
            faces.append((c1, e + s, e + (s + 1) % sides))
    return verts, faces

def ellipsoid(center, radii, seg=10, rings=6):
    verts = []; faces = []
    for r in range(rings + 1):
        th = math.pi * r / rings
        for s in range(seg):
            ph = 2 * math.pi * s / seg
            verts.append((center[0] + radii[0] * math.sin(th) * math.cos(ph),
                          center[1] + radii[1] * math.sin(th) * math.sin(ph),
                          center[2] + radii[2] * math.cos(th)))
    for r in range(rings):
        for s in range(seg):
            a = r * seg + s; b = r * seg + (s + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    return verts, faces

def torus(center, R, r, segs, rsegs, sy=1.0, sz=1.0):
    verts = []; faces = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        for j in range(rsegs):
            b = 2 * math.pi * j / rsegs
            rr = R + r * math.cos(b)
            verts.append((center[0] + rr * math.cos(a), center[1] + rr * math.sin(a) * sy, center[2] + r * math.sin(b) * sz))
    for i in range(segs):
        for j in range(rsegs):
            a0 = i * rsegs + j; a1 = i * rsegs + (j + 1) % rsegs
            b0 = ((i + 1) % segs) * rsegs + j; b1 = ((i + 1) % segs) * rsegs + (j + 1) % rsegs
            faces.append((a0, b0, b1, a1))
    return verts, faces

def box(center, ax_u, ax_v, ax_w, size, taper=1.0):
    u, v, w = [Vector(a).normalized() for a in (ax_u, ax_v, ax_w)]
    verts = []
    for sw in (-1, 1):
        for sv in (-1, 1):
            for su in (-1, 1):
                f = taper if sw > 0 else 1.0
                verts.append(Vector(center) + u * (su * size[0] / 2 * f) + v * (sv * size[1] / 2 * f) + w * (sw * size[2] / 2))
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return verts, faces

def bm_join(parts, name):
    """merge (verts, faces) lists into a single object"""
    V = []; Fc = []
    for vs, fs in parts:
        off = len(V); V += [tuple(v) for v in vs]
        Fc += [tuple(i + off for i in f) for f in fs]
    return mk(name, V, Fc)

def surface_pt(obj, origin, direction):
    """raycast on object (object-space == world here)"""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bvh = BVHTree.FromBMesh(bm); bm.free()
    return bvh

hood_bvh_lo = surface_pt(LO["Hoodie"], None, None)
pants_bvh = surface_pt(LO["Pants"], None, None)

def ray(bvh, origin, d):
    loc, nor, idx, dist = bvh.ray_cast(Vector(origin), Vector(d).normalized())
    return loc, nor

# ---------------------------------------------------------------- hood (collar roll + bunched hood)
nz = LM["neck_z"]
neck_axis = np.array([0.0, -0.02])
hood_parts = []
_bm = bmesh.new(); _bm.from_mesh(LO["Hoodie"].data)
_bv = [v.co.copy() for v in _bm.verts if v.is_boundary and v.co.z > nz - 0.12]
_bm.free()
_cx, _cy = 0.0, -0.035
_bins = 32
_ring = [None] * _bins
for _v in _bv:
    _a = math.atan2(_v.y - _cy, _v.x - _cx); _i = int(((_a + math.pi) / (2 * math.pi)) * _bins) % _bins
    _ring[_i] = _v.copy() if _ring[_i] is None else (_ring[_i] + _v) / 2
for _i in range(_bins):
    if _ring[_i] is None:
        _p = _ring[(_i - 1) % _bins]; _n = None
        for _k in range(1, _bins):
            if _ring[(_i + _k) % _bins] is not None:
                _n = _ring[(_i + _k) % _bins]; break
        _ring[_i] = (_p + _n) / 2 if _p is not None else _n
for _it in range(4):
    _ring = [(_ring[(_i - 1) % _bins] + _ring[_i] * 2 + _ring[(_i + 1) % _bins]) / 4 for _i in range(_bins)]
_pts = []
for _p in _ring:
    _r = Vector((_p.x - _cx, _p.y - _cy, 0)); _r.normalize()
    _pts.append(_p + _r * 0.010 + Vector((0, 0, 0.012)))
_vs = []; _fs = []
_sides = 6
for _i, _p in enumerate(_pts):
    _t = (_pts[(_i + 1) % _bins] - _pts[(_i - 1) % _bins]).normalized()
    _out = Vector((_p.x - _cx, _p.y - _cy, 0)).normalized()
    _up = _t.cross(_out).normalized()
    for _s in range(_sides):
        _ang = 2 * math.pi * _s / _sides
        _vs.append(_p + _out * math.cos(_ang) * 0.021 + Vector((0, 0, 1)) * math.sin(_ang) * 0.017)
for _i in range(_bins):
    for _s in range(_sides):
        _a0 = _i * _sides + _s; _a1 = _i * _sides + (_s + 1) % _sides
        _b0 = ((_i + 1) % _bins) * _sides + _s; _b1 = ((_i + 1) % _bins) * _sides + (_s + 1) % _sides
        _fs.append((_a0, _b0, _b1, _a1))
hood_parts.append((_vs, _fs))
vs, fs = ellipsoid((0, _cy + 0.10, nz - 0.02), (0.085, 0.04, 0.07), 10, 6)
hood_parts.append((vs, fs))
hood = bm_join(hood_parts, "Hood")
_bm = bmesh.new(); _bm.from_mesh(hood.data); bmesh.ops.recalc_face_normals(_bm, faces=_bm.faces); _bm.to_mesh(hood.data); _bm.free()
for v in hood.data.vertices:  # push the hood pile down the back a little
    if v.co.y > 0.02:
        v.co.z -= 0.03 * (v.co.y - 0.02) / 0.1

# drawstrings
cords = []
for sx in (1, -1):
    pts = []
    for k, z in enumerate(np.linspace(nz + 0.03, nz - 0.20, 6)):
        x = sx * (0.036 + 0.004 * k / 5)
        loc, nor = ray(hood_bvh_lo, (x, -0.6, z), (0, 1, 0))
        if loc is None:
            loc = Vector((x, -0.13, z)); nor = Vector((0, -1, 0))
        pts.append(loc + nor * 0.008)
    vs, fs = tube(pts, 0.0032, 6)
    cords.append((vs, fs))
cord_obj = bm_join(cords, "Cords")

# cargo pockets
pk = []
for sx in (1, -1):
    zc = 0.66 + lift * 0 + 0.0
    zc = LM["foot_z"] + 0.62
    loc, nor = ray(pants_bvh, (sx * 1.0, -0.02, zc), (-sx, 0, 0))
    if loc is None:
        continue
    up = Vector((0, 0, 1)); up = (up - nor * up.dot(nor)).normalized()
    side = nor.cross(up).normalized()
    c = loc + nor * 0.014
    vs, fs = box(c, side, up, nor, (0.125, 0.15, 0.028), taper=0.94)
    pk.append((vs, fs))
    vs, fs = box(loc + nor * 0.019 + up * 0.066, side, up, nor, (0.135, 0.045, 0.036), taper=0.96)
    pk.append((vs, fs))
pocket_obj = bm_join(pk, "Pockets")

for _o in (hood, cord_obj, pocket_obj):
    _a = np.array([v.co[:] for v in _o.data.vertices]); print("EXTRA", _o.name, len(_a), _a.min(0).round(3), _a.max(0).round(3))
print("nz", nz, "lift", lift)
setpart(hood, 11); setpart(cord_obj, 10); setpart(pocket_obj, 12)
# assign weights from body for extras (nearest surface), then merge into garments
for o in (hood, cord_obj, pocket_obj):
    idx, bar = tr.weights_for(o)
    assign_weights(o, Transfer.apply(W_hi, idx, bar), gnames)

def join_into(target, others):
    bpy.ops.object.select_all(action='DESELECT')
    for o in others:
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active

# hi versions: subdivided hood + boxes bevelled, joined to hi garments (before join, copy)
def hi_copy(o, subsurf=0, bevel=0.0):
    c = o.copy(); c.data = o.data.copy(); c.name = o.name + "_hi"
    sc.collection.objects.link(c)
    bpy.context.view_layer.objects.active = c
    for oo in bpy.context.selected_objects:
        oo.select_set(False)
    c.select_set(True)
    if bevel > 0:
        md = c.modifiers.new("b", 'BEVEL'); md.width = bevel; md.segments = 2; md.limit_method = 'ANGLE'
        bpy.ops.object.modifier_apply(modifier=md.name)
    if subsurf:
        md = c.modifiers.new("s", 'SUBSURF'); md.levels = subsurf
        bpy.ops.object.modifier_apply(modifier=md.name)
    for g in list(c.vertex_groups):
        c.vertex_groups.remove(g)
    return c

hood_hi = hi_copy(hood, subsurf=2)
cord_hi = hi_copy(cord_obj, subsurf=1)
pocket_hi = hi_copy(pocket_obj, bevel=0.004)
for _k, _o in HI.items():
    setpart(_o, PART[_k])
setpart(hood_hi, 11); setpart(cord_hi, 10); setpart(pocket_hi, 12)
for nm, h in (("Hoodie", [hood_hi, cord_hi]), ("Pants", [pocket_hi])):
    HI[nm] = join_into(HI[nm], h)
LO["Hoodie"] = join_into(LO["Hoodie"], [hood, cord_obj])
LO["Pants"] = join_into(LO["Pants"], [pocket_obj])

# ---------------------------------------------------------------- eyes
eyes = {}
for side, key in (("L", "eyeL"), ("R", "eyeR")):
    c = np.array(LM[key]); c[1] += 0.0098
    vs, fs = ellipsoid(c, (0.0118, 0.0118, 0.0118), 12, 8)
    o = mk("Eye" + side, vs, fs)
    # rotate so the pole faces forward (-Y): rebuild with pole along Y
    me = o.data
    for v in me.vertices:
        p = v.co - Vector(c.tolist())
        v.co = Vector((p.x, p.z, -p.y)) + Vector(c.tolist())
        # pole now along Y
    me.update()
    eyes[side] = o
    for o2 in (o,):
        idx, bar = tr.weights_for(o2)
        W = np.zeros((len(o2.data.vertices), len(gnames)), dtype=np.float32)
        W[:, gnames.index("head")] = 1.0
        assign_weights(o2, W, gnames)

# ---------------------------------------------------------------- duffel + straps
hv = LO["Hoodie"]
back_y = max(v.co.y for v in hv.data.vertices)
dz = LM["hem_z"] + 0.22
_l, _n = ray(hood_bvh_lo, (0, 0.9, dz), (0, -1, 0))
dy = _l.y + 0.95 * 0.125 - 0.04
L_half = 0.26; Rr = 0.125
# capsule-like bag: rings along X
rings = 11; seg = 12
dverts = []; dfaces = []
for i in range(rings):
    u = -1 + 2 * i / (rings - 1)
    x = L_half * u
    prof = max(1 - abs(u) ** 5, 0.0) ** 0.2
    r = Rr * (0.18 + 0.82 * prof) if abs(u) < 1 else Rr * 0.18
    for s in range(seg):
        a = 2 * math.pi * s / seg
        dverts.append((x, dy + 0.95 * r * math.cos(a), dz + r * math.sin(a)))
for i in range(rings - 1):
    for s in range(seg):
        a0 = i * seg + s; a1 = i * seg + (s + 1) % seg
        dfaces.append((a0, a1, a1 + seg, a0 + seg))
c0 = len(dverts); dverts.append((-L_half - 0.012, dy, dz)); c1 = len(dverts); dverts.append((L_half + 0.012, dy, dz))
for s in range(seg):
    dfaces.append((c0, (s + 1) % seg, s))
    e = (rings - 1) * seg
    dfaces.append((c1, e + s, e + (s + 1) % seg))
parts = [(dverts, dfaces)]
# handles (two arcs on top)
for hx in (-0.09, 0.09):
    pts = []
    for t in np.linspace(0, math.pi, 7):
        pts.append((hx + 0.0, dy + 0.10 * (1 - math.cos(t)) * 0.0 + 0.0, dz + Rr * 0.98 + 0.055 * math.sin(t)))
    pts2 = [(hx, dy - 0.06 + 0.12 * (i / 6), dz + Rr * 0.9 + 0.07 * math.sin(math.pi * i / 6)) for i in range(7)]
    parts.append(tube(pts2, 0.011, 6))
# straps over the shoulders (backpack style loops projected on the hoodie)
def strap_path(sx):
    pts = []; nors = []
    # back: from bag top up to shoulder
    for z in np.linspace(dz + Rr * 0.7, LM["neck_z"] + 0.055, 6):
        x = sx * (0.095 + 0.04 * (z - dz) / 0.35)
        loc, nor = ray(hood_bvh_lo, (x, 0.9, z), (0, -1, 0))
        pts.append(loc + nor * 0.012 if loc else Vector((x, 0.1, z))); nors.append(nor.copy() if loc else Vector((0, 1, 0)))
    # shoulder top
    for t in (0.0, 0.5, 1.0):
        x = sx * (0.13 + 0.01 * t)
        loc, nor = ray(hood_bvh_lo, (x, -0.02 - 0.0 * t - 0.09 * t + 0.05, 1.9), (0, 0, -1))
        y = 0.04 - 0.09 * t
        loc, nor = ray(hood_bvh_lo, (x, y, 1.9), (0, 0, -1))
        pts.append(loc + nor * 0.012 if loc else Vector((x, y, nz + 0.1))); nors.append(nor.copy() if loc else Vector((0, 0, 1)))
    # front chest down
    for z in np.linspace(LM["neck_z"] + 0.02, LM["hem_z"] + 0.12, 6):
        x = sx * (0.115 + 0.01 * (LM["neck_z"] - z))
        loc, nor = ray(hood_bvh_lo, (x, -0.9, z), (0, 1, 0))
        pts.append(loc + nor * 0.012 if loc else Vector((x, -0.13, z))); nors.append(nor.copy() if loc else Vector((0, -1, 0)))
    return pts, nors

def ribbon(pts, nors, width, th=0.006):
    verts = []; faces = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        # surface normal approx: away from body axis in xy
        nrm = nors[i].normalized()
        side = t.cross(nrm).normalized()
        for sgn in (-1, 1):
            verts.append(p + side * sgn * width / 2)
            verts.append(p + side * sgn * width / 2 + nrm * th)
    for i in range(n - 1):
        a = i * 4
        b = a + 4
        faces += [(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2), (a + 1, b + 1, b + 3, a + 3), (a, a + 2, b + 2, b)]
    return verts, faces

for sx in (1, -1):
    pts, nors = strap_path(sx)
    parts.append(ribbon(pts, nors, 0.040, 0.007))
duffel = bm_join(parts, "CHAR_Heister_Duffel")
setpart(duffel, 8)
for _e in eyes.values():
    setpart(_e, 9)
idx, bar = tr.weights_for(duffel)
W = np.zeros((len(duffel.data.vertices), len(gnames)), dtype=np.float32)
W[:, gnames.index("spine_02")] = 1.0
assign_weights(duffel, W, gnames)
duffel_hi = hi_copy(duffel, subsurf=1, bevel=0.0)

# ---------------------------------------------------------------- mixamo rename
MAP = {"pelvis": "Hips", "spine_01": "Spine", "spine_02": "Spine1", "spine_03": "Spine2", "neck_01": "Neck", "head": "Head",
       "clavicle": "Shoulder", "upperarm": "Arm", "lowerarm": "ForeArm", "hand": "Hand",
       "thigh": "UpLeg", "calf": "Leg", "foot": "Foot", "ball": "ToeBase"}
def mixname(n):
    if n in ("pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head"):
        return "mixamorig:" + MAP[n]
    side = "Left" if n.endswith("_l") else "Right"
    base = n[:-2]
    if base in MAP:
        return f"mixamorig:{side}{MAP[base]}"
    for f, F_ in (("thumb", "Thumb"), ("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Pinky")):
        if base.startswith(f + "_0"):
            return f"mixamorig:{side}Hand{F_}{int(base[-1])}"
    raise KeyError(n)
rename = {b.name: mixname(b.name) for b in rig.data.bones if b.name != "Root"}
# Hips (pelvis) must be top-level: drop Root
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
eb = rig.data.edit_bones
for b in list(eb):
    if b.name == "Root":
        for ch in b.children:
            ch.parent = None
        eb.remove(b)
bpy.ops.object.mode_set(mode='OBJECT')
for b in rig.data.bones:
    b.name = rename[b.name]
    b.use_deform = True
rig.name = "CHAR_Heister"; rig.data.name = "CHAR_Heister_Armature"
print("bones", len(rig.data.bones))

def rename_groups(o):
    for g in o.vertex_groups:
        if g.name in rename:
            g.name = rename[g.name]

# ---------------------------------------------------------------- join body (skin active so shape keys survive)
for k in LO:
    pass
parts = [LO[k] for k in ("Hoodie", "Pants", "Shoes", "Gloves", "Beanie")]
# IsSkin group for LOD/key masking
for k, o in LO.items():
    vg = o.vertex_groups.new(name="IsSkin")
    vg.add(list(range(len(o.data.vertices))), 1.0 if k == "Skin" else 0.0, 'REPLACE')
body = join_into(LO["Skin"], parts)
body.name = "CHAR_Heister_Body"; body.data.name = "CHAR_Heister_Body"
mask = LO["Mask"]; mask.name = "CHAR_Heister_Mask"; mask.data.name = "CHAR_Heister_Mask"
for o in [body, mask, duffel] + list(eyes.values()):
    rename_groups(o)
eyes["L"].name = "CHAR_Heister_EyeL"; eyes["R"].name = "CHAR_Heister_EyeR"
for k, o in eyes.items():
    o.data.name = o.name

# hi: join everything into one HI object (bake source)
his = [HI[k] for k in ("Hoodie", "Pants", "Shoes", "Gloves", "Beanie", "Mask")]
hi_all = join_into(HI["Skin"], his)
hi_all.name = "HI_all"
for g in list(hi_all.vertex_groups):
    hi_all.vertex_groups.remove(g)
duffel_hi.name = "HI_duffel"

# collections / parenting
coll = bpy.data.collections["CHAR_Heister"]
hi_coll = bpy.data.collections["HI_src"]
for o in [body, mask, duffel] + list(eyes.values()):
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    coll.objects.link(o)
for o in [hi_all, duffel_hi]:
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    hi_coll.objects.link(o)
for o in [body, mask] + list(eyes.values()):
    md = o.modifiers.new("Armature", 'ARMATURE'); md.object = rig
    o.parent = rig
# duffel: rigid child of spine bone
bone = rig.data.bones["mixamorig:Spine1"]
for g in list(duffel.vertex_groups):
    duffel.vertex_groups.remove(g)
duffel.parent = rig; duffel.parent_type = 'BONE'; duffel.parent_bone = bone.name
duffel.matrix_parent_inverse = (rig.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))).inverted()
body_hi.hide_viewport = True; body_hi.hide_render = True
# smooth shading
for o in [body, mask, duffel, hi_all, duffel_hi] + list(eyes.values()):
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
json.dump(LM, open(os.path.join(H, "scripts", "landmarks_s4.json"), "w"))
for o in [body, mask, duffel] + list(eyes.values()):
    print("TRIS", o.name, sum(len(p.vertices) - 2 for p in o.data.polygons))
print("HI", sum(len(p.vertices) - 2 for p in hi_all.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s4.blend"))









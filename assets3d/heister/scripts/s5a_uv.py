"""Stage 5a: UVs. Body/mask UVs are transferred from the MakeHuman base UV (clean islands), extras are smart-projected,
every connected island gets uniform texel density (head boosted) and all islands are packed into one 0-1 atlas
(eyes get a reserved box). heister_s4 -> heister_s5a"""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
from hlib import coords
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s4.blend"))
O = bpy.data.objects
LM = json.load(open(os.path.join(H, "scripts", "landmarks_s4.json")))
eye_z = LM["eye_z"]
body = O["CHAR_Heister_Body"]; mask = O["CHAR_Heister_Mask"]; duffel = O["CHAR_Heister_Duffel"]
eyes = [O["CHAR_Heister_EyeL"], O["CHAR_Heister_EyeR"]]
src = O["Body_hi"]
lift = 0.0

def islands_uv(bm, uvl):
    parent = {f.index: f.index for f in bm.faces}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f1, f2 = e.link_faces
        def uvs(f):
            d = {}
            for l in f.loops:
                if l.edge == e:
                    d[l.vert.index] = (round(l[uvl].uv.x, 5), round(l[uvl].uv.y, 5))
                    nl = l.link_loop_next
                    d[nl.vert.index] = (round(nl[uvl].uv.x, 5), round(nl[uvl].uv.y, 5))
            return d
        a, b = uvs(f1), uvs(f2)
        if all(a[k] == b[k] for k in a if k in b):
            ra, rb = find(f1.index), find(f2.index)
            if ra != rb:
                parent[ra] = rb
    return {f.index: find(f.index) for f in bm.faces}

# ------------------------------------------------ source (MakeHuman) islands + per-island BVH
sme = src.data
sme.calc_loop_triangles()
SP = coords(sme)
suv = np.zeros((len(sme.loops), 2), dtype=np.float32)
sme.uv_layers.active.data.foreach_get("uv", suv.ravel())
bm = bmesh.new(); bm.from_mesh(sme)
sisl = islands_uv(bm, bm.loops.layers.uv.active)
bm.free()
tris = [(t.vertices[0], t.vertices[1], t.vertices[2]) for t in sme.loop_triangles]
tloops = [tuple(t.loops) for t in sme.loop_triangles]
tpoly = [t.polygon_index for t in sme.loop_triangles]
tisl = np.array([sisl[p] for p in tpoly])
uis = np.unique(tisl)
print("source islands", len(uis))
isl_tris = {}; isl_bvh = {}
for i in uis:
    ids = np.where(tisl == i)[0]
    isl_tris[i] = ids
    isl_bvh[i] = BVHTree.FromPolygons([tuple(p) for p in SP.tolist()], [tris[j] for j in ids])
all_bvh = BVHTree.FromPolygons([tuple(p) for p in SP.tolist()], tris)

def bary(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-14:
        return np.array([1.0, 0, 0])
    v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den
    w3 = np.clip(np.array([1 - v - w, v, w]), 0, None)
    return w3 / max(w3.sum(), 1e-9)

def transfer_uv(obj, face_mask):
    me = obj.data
    uvd = me.uv_layers.active.data
    for poly in me.polygons:
        if not face_mask[poly.index]:
            continue
        cen = Vector(np.mean([me.vertices[i].co[:] for i in poly.vertices], axis=0).tolist())
        loc, nor, fi, d = all_bvh.find_nearest(cen)
        isl = tisl[fi]
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            loc, nor, fj, d = isl_bvh[isl].find_nearest(p)
            tj = isl_tris[isl][fj]
            tv = tris[tj]
            w = bary(np.array(loc), SP[tv[0]], SP[tv[1]], SP[tv[2]])
            tl = tloops[tj]
            uvd[li].uv = tuple((suv[tl[0]] * w[0] + suv[tl[1]] * w[1] + suv[tl[2]] * w[2]).tolist())

for o in (body, mask, duffel) + tuple(eyes):
    for u in list(o.data.uv_layers):
        o.data.uv_layers.remove(u)
    o.data.uv_layers.new(name="UVMap")

def part_arr(o):
    a = np.zeros(len(o.data.vertices), dtype=np.float32)
    o.data.attributes["part"].data.foreach_get("value", a)
    return a
pb = part_arr(body)
fpart = np.array([int(round(pb[p.vertices[0]])) for p in body.data.polygons])
transfer_uv(body, np.isin(fpart, [1, 2, 3, 4, 5, 6]))
transfer_uv(mask, np.ones(len(mask.data.polygons), dtype=bool))

# smart project extras in body (cords/hood/pockets) and the duffel
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(body.data)
for f in bm.faces:
    f.select = bool(fpart[f.index] in (10, 11, 12))
bmesh.update_edit_mesh(body.data)
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, correct_aspect=True, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT')
duffel.select_set(True); bpy.context.view_layer.objects.active = duffel
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, correct_aspect=True, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------ island density normalisation (+ head boost), then pack
objs = [body, mask, duffel]
nisl = {}
for o in objs:
    bm = bmesh.new(); bm.from_mesh(o.data)
    uvl = bm.loops.layers.uv.active
    isl = islands_uv(bm, uvl)
    groups = {}
    for f in bm.faces:
        groups.setdefault(isl[f.index], []).append(f)
    nisl[o.name] = len(groups)
    for gid, fs in groups.items():
        a3 = sum(f.calc_area() for f in fs)
        auv = 0.0
        for f in fs:
            pts = [l[uvl].uv.copy() for l in f.loops]
            s = 0.0
            for i in range(len(pts)):
                x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
                s += x1 * y2 - x2 * y1
            auv += abs(s) / 2
        if auv < 1e-12 or a3 < 1e-9:
            continue
        zc = np.mean([l.vert.co.z for f in fs for l in f.loops])
        boost = 1.0
        if o.name.endswith("Body") and zc > eye_z - 0.16:
            boost = 1.8
        if o.name.endswith("Mask"):
            boost = 1.8
        k = math.sqrt(a3 / auv) * boost
        cx = np.mean([l[uvl].uv.x for f in fs for l in f.loops]); cy = np.mean([l[uvl].uv.y for f in fs for l in f.loops])
        for f in fs:
            for l in f.loops:
                u = l[uvl].uv
                l[uvl].uv = ((u.x - cx) * k, (u.y - cy) * k)
    bm.to_mesh(o.data); bm.free()
print("islands", nisl)

bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, scale=True, merge_overlap=False, margin_method='SCALED', margin=0.005, shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')

tot_uv = 0
for o in objs:
    uvd = o.data.uv_layers.active.data
    a = np.zeros(len(uvd) * 2, dtype=np.float32); uvd.foreach_get("uv", a)
    a = a.reshape(-1, 2) * 0.94
    uvd.foreach_set("uv", a.ravel())
    # coverage estimate
    me = o.data
    for p in me.polygons:
        pts = [a[li] for li in p.loop_indices]
        s = 0.0
        for i in range(len(pts)):
            s += pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
        tot_uv += abs(s) / 2
print("UV coverage (of unit square)", round(tot_uv, 3))
BOX = (0.945, 0.01, 0.05)
for o in eyes:
    me = o.data
    c = np.mean([v.co[:] for v in me.vertices], axis=0)
    uvd = me.uv_layers.active.data
    for lp in me.loops:
        p = np.array(me.vertices[lp.vertex_index].co[:]) - c
        r = 0.0118
        uvd[lp.index].uv = (BOX[0] + BOX[2] * (0.5 + 0.5 * p[0] / r), BOX[1] + BOX[2] * (0.5 + 0.5 * p[2] / r))
json.dump({"eye_box": BOX}, open(os.path.join(H, "scripts", "uvinfo.json"), "w"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s5a.blend"))

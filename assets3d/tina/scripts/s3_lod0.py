"""Stage 3: LOD0 low-poly pieces from the hi pieces, UV packing into the shared atlas. -> scripts/_stage3.blend"""
import sys
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina/scripts")
import bpy, bmesh, numpy as np
import mesh_utils as mu, tlib

ROOT = r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina"
bpy.ops.wm.open_mainfile(filepath=ROOT + "/scripts/_stage2.blend")
H = {n: bpy.data.objects["Tina_%sHi" % n] for n in ("Skin", "Blazer", "Blouse", "Trousers", "Shoes")}

TARGET = {"Skin": 4900, "Blazer": 3500, "Blouse": 330, "Trousers": 1900, "Shoes": 560}
DENS = {"Skin": 1.9, "Blazer": 1.1, "Blouse": 0.7, "Trousers": 0.8, "Shoes": 0.6}   # relative texel density


def face_keep_group(ob):
    vg = ob.vertex_groups.new(name="_keep")
    co = np.array([v.co[:] for v in ob.data.vertices])
    w = np.zeros(len(co))
    face = (co[:, 1] < -0.02) & (co[:, 2] > 1.40) & (np.abs(co[:, 0]) < 0.1)
    w[face] = 1.0
    hands = np.abs(co[:, 0]) > 0.3
    w[hands] = 0.35
    for i in np.nonzero(w > 0)[0]:
        vg.add([int(i)], float(w[i]), 'REPLACE')
    return vg


def make_lo(name, hi, target, keep=None):
    lo = mu.copy_object(hi, "Tina_%s_L0" % name)
    if keep:
        face_keep_group(lo)
    cur = mu.tri_count(lo)
    bpy.context.view_layer.objects.active = lo
    for o in bpy.context.selected_objects:
        o.select_set(False)
    lo.select_set(True)
    ratio = target / cur
    for it in range(4):
        m = lo.modifiers.new("dec", 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = float(np.clip(ratio, 0.02, 1.0))
        m.use_collapse_triangulate = True
        m.delimit = {'UV'}
        if keep:
            m.vertex_group = "_keep"
            m.vertex_group_factor = 4.0
        bpy.ops.object.modifier_apply(modifier=m.name)
        cur = mu.tri_count(lo)
        print(name, "iter", it, cur)
        if cur <= target:
            break
        ratio = target / cur * 0.97
    if lo.vertex_groups.get("_keep"):
        lo.vertex_groups.remove(lo.vertex_groups["_keep"])
    return lo


LO = {}
for n in H:
    LO[n] = make_lo(n, H[n], TARGET[n], keep=False)
    print(n, "LOD0 tris", mu.tri_count(LO[n]), "verts", len(LO[n].data.vertices), "groups", len(LO[n].vertex_groups))

# --- pack UVs of all main pieces jointly
for n, o in LO.items():
    mu.uv_scale_about_center(o, DENS[n] ** 0.5 * 0.5)
tmp = [mu.copy_object(o, "_tmp_" + o.name) for o in LO.values()]
for t, o in zip(tmp, LO.values()):
    # copy_object loses UV when shape_keys False? ensure uv exists
    assert len(t.data.uv_layers) > 0
loop_counts = [len(t.data.loops) for t in tmp]
J = mu.join(tmp, "_packtmp")
bpy.context.view_layer.objects.active = J
J.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT')
try:
    bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin=0.0035, scale=True, merge_overlap=False)
except Exception as e:
    print("pack err", e)
    bpy.ops.uv.pack_islands(margin=0.0035)
bpy.ops.object.mode_set(mode='OBJECT')
uvl = J.data.uv_layers.active
a = np.empty(len(uvl.data) * 2, dtype=np.float32); uvl.data.foreach_get("uv", a); a = a.reshape(-1, 2)
print("packed bbox", a.min(0), a.max(0))
a = a - a.min(0)
a = a / a.max()          # 0..1 square
a[:, 0] = a[:, 0] * (tlib.MAIN[2] - tlib.MAIN[0]) + tlib.MAIN[0]
a[:, 1] = a[:, 1] * (tlib.MAIN[3] - tlib.MAIN[1]) + tlib.MAIN[1]
off = 0
for o, cnt in zip(LO.values(), loop_counts):
    ul = o.data.uv_layers.active
    ul.data.foreach_set("uv", a[off:off + cnt].ravel())
    off += cnt
bpy.data.objects.remove(J)
# total island area coverage
print("done packing")
for o in LO.values():
    o.data.uv_layers.active.name = "UVMap"

# --- extras (LOD0)
sk_hi = H["Skin"]
EX = {"Hair": tlib.build_hair(sk_hi, 0), "Eyes": tlib.build_eyes(0), "Lashes": tlib.build_lashes(0),
      "Headset": tlib.build_headset(0)}
tot = sum(mu.tri_count(o) for o in LO.values()) + sum(mu.tri_count(o) for o in EX.values())
print("LOD0 approx total tris", tot, {k: mu.tri_count(v) for k, v in EX.items()})
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/scripts/_stage3.blend")


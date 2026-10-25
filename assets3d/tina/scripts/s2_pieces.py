"""Stage 2: hi-res pieces (skin, blazer, blouse, trousers, shoes) derived from the MPFB body. -> scripts/_stage2.blend"""
import sys, os
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
import bpy, bmesh, numpy as np
from mathutils import Vector
import mpfb_base as mb, mesh_utils as mu, preview_utils as pv

ROOT = r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina"
bpy.ops.wm.open_mainfile(filepath=ROOT + "/scripts/_stage1.blend")
body = bpy.data.objects["Tina_BodyHi"]
arm = bpy.data.objects["Tina_Armature"]
me = body.data
N = len(me.vertices)
co = np.empty(N * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
dom = np.array(mb.dominant_bone_map(body))
x, y, z = co[:, 0], co[:, 1], co[:, 2]
is_hand = np.array(["Hand" in d for d in dom])
is_head = np.array([d.endswith(":Head") for d in dom])
is_neck = np.array([d.endswith(":Neck") for d in dom])
is_arm = np.array([d.endswith(("Arm", "ForeArm", "Shoulder")) for d in dom])
is_spine = np.array([d.endswith(("Spine", "Spine1", "Spine2")) for d in dom])
is_hips = np.array([d.endswith(":Hips") for d in dom])
is_leg = np.array([d.endswith(("UpLeg", ":LeftLeg", ":RightLeg")) for d in dom])
is_foot = np.array([d.endswith(("Foot", "ToeBase")) for d in dom])


def refit_ref(ob):
    cod = np.empty(len(ob.data.vertices) * 3, dtype=np.float32); ob.data.vertices.foreach_get("co", cod); cod = cod.reshape(-1, 3)
    pos, nor, dist = mu.closest_points(body, cod)
    return pos


def make_shell(name, mask, thickness, smooth_it, min_dist, factor=0.5):
    ob = mu.submesh_by_verts(body, mask, name, mode='all')
    mu.offset_along_normals(ob, thickness)
    mu.smooth_shell(ob, smooth_it, factor)
    mu.push_outside(ob, body, min_dist)
    mu.smooth_shell(ob, 3, 0.4)
    mu.push_outside(ob, body, min_dist * 0.9)
    return ob


# wrist cut planes (perpendicular to the forearm axis at the wrist)
wrist_dot = np.full(N, -1.0, dtype=np.float32)   # signed distance beyond the wrist along the forearm (m), per side
for side in ("Left", "Right"):
    bh = arm.data.bones["mixamorig:%sHand" % side]
    bf = arm.data.bones["mixamorig:%sForeArm" % side]
    d = np.array(bh.head_local - bf.head_local); d /= np.linalg.norm(d)
    w = np.array(bh.head_local)
    sidemask = (x > 0) if side == "Left" else (x < 0)
    sd = (co - w) @ d
    zone0 = sidemask & (np.abs(x) > 0.2) & (is_arm | is_hand | (z > 0.95))
    wrist_dot[zone0] = sd[zone0]
arm_zone = (np.abs(x) > 0.2) & (is_arm | is_hand | (z > 0.95))
sleeve = (is_arm | is_hand) & arm_zone & (wrist_dot < 0.0)
skin_forearm = arm_zone & (wrist_dot > -0.035) & (is_hand | is_arm)
SK = mu.submesh_by_verts(body, is_head | is_neck | ((z > 1.345) & (np.abs(x) < 0.075)) | (is_hand & (wrist_dot >= -0.035)) | skin_forearm, "Tina_SkinHi", mode='all')

# --- blazer
is_uleg = np.array([d.endswith("UpLeg") for d in dom])
blz_mask = (z > 0.80) & ~is_neck & ~is_head & ~is_hand & ~(arm_zone & ~sleeve) & ~((x ** 2 + (y + 0.02) ** 2 < 0.068 ** 2) & (z > 1.30))
BZ = make_shell("Tina_BlazerHi", blz_mask, 0.026, 14, 0.021)
VB, VT, HW = 1.13, 1.40, 0.082
def line(zz):
    return HW * np.clip((zz - VB) / (VT - VB), 0, 1.2)
bm = bmesh.new(); bm.from_mesh(BZ.data); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
def face_in_v(f):
    c = f.calc_center_median()
    return c.y < 0.0 and VB < c.z < VT + 0.1 and abs(c.x) < line(c.z) and c.y < -0.03
kill = [f for f in bm.faces if face_in_v(f)]
kv = set(v for f in kill for v in f.verts)
bmesh.ops.delete(bm, geom=kill, context='FACES')
for v in kv:
    if v.is_valid and v.link_faces and VB - 0.01 < v.co.z:
        sgn = 1.0 if v.co.x >= 0 else -1.0
        v.co.x = sgn * float(line(v.co.z))
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context='VERTS')
bm.to_mesh(BZ.data); bm.free()
mu.add_rim(BZ, ref_coords=refit_ref(BZ))

# --- blouse (only the part near the neck/chest is visible)
bl_mask = (z > 1.10) & (z < 1.415) & (np.abs(x) < 0.16) & ~is_hand & ~(is_head & (y < -0.07)) & ~((y < -0.08) & (z > 1.355))
BL = make_shell("Tina_BlouseHi", bl_mask, 0.010, 4, 0.007)
_a = np.empty(len(BL.data.vertices) * 3, dtype=np.float32); BL.data.vertices.foreach_get("co", _a); _a = _a.reshape(-1, 3)
_a[:, 2] = np.minimum(_a[:, 2], 1.385)
BL.data.vertices.foreach_set("co", _a.ravel())
mu.add_rim(BL, ref_coords=refit_ref(BL))

# --- trousers
tr_mask = (z > 0.075) & (z < 0.87) & (np.abs(x) < 0.26) & ~is_hand & ~arm_zone
TR = make_shell("Tina_TrousersHi", tr_mask, 0.013, 8, 0.008)
mu.add_rim(TR, ref_coords=refit_ref(TR))

# --- shoes
sh_mask = is_foot & (z < 0.085)
SH = make_shell("Tina_ShoesHi", sh_mask, 0.009, 3, 0.006)
a = np.empty(len(SH.data.vertices) * 3, dtype=np.float32); SH.data.vertices.foreach_get("co", a); a = a.reshape(-1, 3)
a[:, 2] = np.maximum(a[:, 2], 0.0)
SH.data.vertices.foreach_set("co", a.ravel())
mu.add_rim(SH, ref_coords=refit_ref(SH))

for o in (SK, BZ, BL, TR, SH):
    print(o.name, len(o.data.vertices), mu.tri_count(o))

body.hide_render = True
body.hide_viewport = True
if __name__ == "__main__":
    for nm, col in (("Tina_SkinHi", (0.8, 0.6, 0.5)), ("Tina_BlazerHi", (0.03, 0.05, 0.15)), ("Tina_BlouseHi", (0.9, 0.9, 0.9)),
                    ("Tina_TrousersHi", (0.08, 0.08, 0.1)), ("Tina_ShoesHi", (0.02, 0.02, 0.02))):
        ob = bpy.data.objects[nm]
        m = bpy.data.materials.new("tmp_" + nm); m.diffuse_color = (*col, 1)
        ob.data.materials.append(m)
    pv.shot(ROOT + "/shots/s2_front.png", target=(0, 0, 0.85), eye=(0, -4.6, 0.9), res=(600, 900), lens=50, textured=False)
    pv.shot(ROOT + "/shots/s2_close.png", target=(0, 0, 1.3), eye=(0.5, -1.8, 1.4), res=(700, 700), lens=50, textured=False)
    for nm in ("Tina_BlazerHi", "Tina_BlouseHi", "Tina_TrousersHi", "Tina_ShoesHi", "Tina_SkinHi"):
        bpy.data.objects[nm].data.materials.clear()
    bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/scripts/_stage2.blend")





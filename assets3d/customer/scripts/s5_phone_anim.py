# Stage 5: phone prop + clips (NLA). Run: blender -b stage4.blend -P s5_phone_anim.py
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import bmesh
from mathutils import Euler, Quaternion
O = bpy.data.objects; sc = bpy.context.scene
sc.render.fps = 30; sc.render.fps_base = 1.0
rig = O["CHAR_Customer"]
col = bpy.data.collections["CHAR_Customer"]

# ================= PHONE =================
PW, PT, PH = 0.0715, 0.0078, 0.1467
def make_phone():
    bmx = bmesh.new()
    # rounded rect in XZ
    pts = []
    r = 0.0105; segs = 5
    cx, cz = PW / 2 - r, PH / 2 - r
    for (sx, sz, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for i in range(segs):
            a = math.radians(a0 + 90 * i / (segs - 1))
            pts.append((sx * cx + r * math.cos(a), sz * cz + r * math.sin(a)))
    vs = [bmx.verts.new((x, -PT / 2, z)) for x, z in pts]
    f = bmx.faces.new(vs)
    if f.normal.y > 0: f.normal_flip()
    ext = bmesh.ops.extrude_face_region(bmx, geom=[f])
    verts = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    for v in verts: v.co.y += PT
    bmx.normal_update()
    bmesh.ops.recalc_face_normals(bmx, faces=bmx.faces)
    # bevel edges
    bmesh.ops.bevel(bmx, geom=list(bmx.edges), offset=0.0012, segments=2, affect='EDGES')
    bmx.normal_update()
    # front face = most -Y normal, largest
    front = max(bmx.faces, key=lambda ff: (-ff.normal.y) * ff.calc_area())
    res = bmesh.ops.inset_region(bmx, faces=[front], thickness=0.0028, depth=0.0)
    screen = front
    # screen faces material 1
    for ff in bmx.faces: ff.material_index = 0
    screen.material_index = 1
    uv = bmx.loops.layers.uv.new("UVMap")
    for ff in bmx.faces:
        for l in ff.loops:
            if ff is screen:
                l[uv].uv = ((l.vert.co.x + PW / 2) / PW, (l.vert.co.z + PH / 2) / PH)
            else:
                l[uv].uv = (0.02, 0.02)
    # camera bump on back
    bump = bmesh.ops.create_cube(bmx, size=1.0)
    for v in bump["verts"]:
        v.co.x = v.co.x * 0.030 + (PW / 2 - 0.021); v.co.z = v.co.z * 0.030 + (PH / 2 - 0.021); v.co.y = v.co.y * 0.003 + (PT / 2 + 0.0008)
    for ff in bmx.faces:
        if all(v in bump["verts"] for v in ff.verts): ff.material_index = 0
    me = bpy.data.meshes.new("PROP_Phone"); bmx.to_mesh(me); bmx.free()
    for p in me.polygons: p.use_smooth = True
    return me
me = make_phone()
phone = bpy.data.objects.new("PROP_Phone", me)
pcol = bpy.data.collections.new("PROP_Phone"); sc.collection.children.link(pcol); pcol.objects.link(phone)
# materials
mb = bpy.data.materials.new("MAT_PhoneBody"); mb.use_nodes = True
pb = [n for n in mb.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
pb.inputs["Base Color"].default_value = (0.012, 0.013, 0.016, 1); pb.inputs["Metallic"].default_value = 0.85; pb.inputs["Roughness"].default_value = 0.28
# screen placeholder image 512x1024
W_, H_ = 512, 1024
yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
img = np.zeros((H_, W_, 3), np.float32)
g = yy / H_; img[..., 0] = 0.03 + 0.05 * g; img[..., 1] = 0.08 + 0.12 * g; img[..., 2] = 0.2 + 0.35 * g
def rect(x0, y0, x1, y1, c):
    img[y0:y1, x0:x1] = c
# status bar + face id brackets + face glyph
rect(60, 950, 160, 962, (0.9, 0.9, 0.9)); rect(380, 950, 452, 962, (0.9, 0.9, 0.9))
cxx, cyy, rr = 256, 520, 120
for (sx, sy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
    x0 = cxx + sx * rr; y0 = cyy + sy * rr
    rect(min(x0, x0 - sx * 50), y0 - 5 if sy < 0 else y0 - 5, max(x0, x0 - sx * 50), y0 + 5, (0.3, 1.0, 0.9))
    rect(x0 - 5, min(y0, y0 - sy * 50), x0 + 5, max(y0, y0 - sy * 50), (0.3, 1.0, 0.9))
rect(cxx - 40, cyy + 20, cxx - 28, cyy + 52, (0.3, 1.0, 0.9)); rect(cxx + 28, cyy + 20, cxx + 40, cyy + 52, (0.3, 1.0, 0.9))
rect(cxx - 4, cyy - 10, cxx + 4, cyy + 30, (0.3, 1.0, 0.9)); rect(cxx - 36, cyy - 45, cxx + 36, cyy - 36, (0.3, 1.0, 0.9))
rect(150, 250, 362, 262, (0.8, 0.85, 0.9))
im = bpy.data.images.new("T_PhoneScreen", W_, H_, alpha=True)
px = np.dstack([img, np.ones((H_, W_), np.float32)])
im.pixels.foreach_set(px.ravel()); im.update()
im.filepath_raw = os.path.join(ROOT, "textures", "T_PhoneScreen.png"); im.file_format = 'PNG'; im.save()
ms = bpy.data.materials.new("MAT_PhoneRuntime"); ms.use_nodes = True
nt = ms.node_tree; ps = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
ps.inputs["Base Color"].default_value = (0, 0, 0, 1); ps.inputs["Roughness"].default_value = 0.2
it = nt.nodes.new('ShaderNodeTexImage'); it.image = im; im.colorspace_settings.name = 'sRGB'
nt.links.new(it.outputs["Color"], ps.inputs["Emission Color"]); ps.inputs["Emission Strength"].default_value = 1.0
phone.data.materials.append(mb); phone.data.materials.append(ms)
phone.rotation_euler = (0, 0, 0)

# standalone export (before parenting)
os.makedirs(os.path.join(ROOT, "export"), exist_ok=True)
select_only(phone)
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "export", "PROP_Phone.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_cameras=False, export_lights=False)
print("PHONE tris", tri_count(me))

# ---------- bone-parent to right hand
bpy.context.view_layer.update()
def bhead(n): return np.array(rig.data.bones["mixamorig:" + n].head_local)
wrist = bhead("RightHand"); mid = bhead("RightHandMiddle1"); idx = bhead("RightHandIndex1"); pin = bhead("RightHandPinky1")
d = mid - wrist; d /= np.linalg.norm(d)
side = idx - pin; side /= np.linalg.norm(side)
n_ = np.cross(d, side)
body_c = np.array([0, -0.02, 1.2])
if np.dot(n_, body_c - wrist) < 0: n_ = -n_
n_ /= np.linalg.norm(n_)
print("HAND d", d.round(2), "side", side.round(2), "palmN", n_.round(2))
top = side   # phone top = index-finger side (fix pass: was -side, phone upside down for a natural hold)
# phone local axes: X=width, Z=height(top), -Y screen normal => Y = -n
zx = top; yx = -n_; xx_ = np.cross(yx, zx); xx_ /= np.linalg.norm(xx_)
yx = np.cross(zx, xx_)
R = Matrix(((xx_[0], yx[0], zx[0]), (xx_[1], yx[1], zx[1]), (xx_[2], yx[2], zx[2])))
center = wrist + d * 0.062 + n_ * (PT / 2 + 0.011)
Mw = R.to_4x4(); Mw.translation = Vector(center)
phone.parent = rig; phone.parent_type = 'BONE'; phone.parent_bone = "mixamorig:RightHand"
bone = rig.data.bones["mixamorig:RightHand"]
# parent matrix for bone parenting = armature_world @ bone matrix @ translate(0, length, 0)
bm_ = rig.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
phone.matrix_parent_inverse = bm_.inverted()
phone.matrix_world = Mw
for c in phone.users_collection: c.objects.unlink(phone)
col.objects.link(phone); bpy.data.collections.remove(pcol)
pcol2 = bpy.data.collections.new("PROP_Phone"); sc.collection.children.link(pcol2)

# ================= ANIMATION =================
bpy.context.view_layer.objects.active = rig
bn = {b.name.split(":")[1]: b for b in rig.data.bones}
Rr = {k: b.matrix_local.to_3x3() for k, b in bn.items()}
Rdir = {k: (b.tail_local - b.head_local).normalized() for k, b in bn.items()}
def dq(spec, bone):
    if isinstance(spec, Quaternion): return spec
    rx, ry, rz = spec[:3]; roll = spec[3] if len(spec) > 3 else 0.0
    e = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_matrix()
    if roll:
        e = e @ Matrix.Rotation(math.radians(roll), 3, Rdir[bone])
    return e
def basis(bone, spec):
    m = Rr[bone].inverted() @ (dq(spec, bone) if not isinstance(spec, Quaternion) else spec.to_matrix()) @ Rr[bone]
    return m.to_quaternion()

# finger grip around phone edge: curl about axis = cross(dir, palmN)
curl_axis = Vector(np.cross(d, n_)).normalized()
def curlq(deg): return Quaternion(curl_axis, math.radians(deg))
GRIP = {}
for f in ("Index", "Middle", "Ring", "Pinky"):
    for j, a in zip((1, 2, 3), (55, 70, 45)):
        GRIP["RightHand%s%d" % (f, j)] = curlq(a)
GRIP["RightHandThumb1"] = curlq(-18); GRIP["RightHandThumb2"] = curlq(-20)
# left hand relaxed curl
LCURL = {}
for f in ("Index", "Middle", "Ring", "Pinky"):
    for j, a in zip((1, 2, 3), (14, 20, 14)): LCURL["LeftHand%s%d" % (f, j)] = (a, 0, 0)

def bpose(over):
    P = {}
    P.update(over)
    return P
def keypose(frame, P, extra_loc=None):
    ad = rig.animation_data
    allb = list(rig.pose.bones)
    for pb in allb:
        short = pb.name.split(":")[1]
        spec = P.get(short)
        if spec is None: q = Quaternion((1, 0, 0, 0))
        else: q = basis(short, spec)
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    if extra_loc is not None:
        pb = rig.pose.bones["mixamorig:Hips"]
        v = Rr["Hips"].inverted() @ Vector(extra_loc)
        pb.location = v; pb.keyframe_insert("location", frame=frame)
    else:
        pb = rig.pose.bones["mixamorig:Hips"]; pb.location = (0, 0, 0); pb.keyframe_insert("location", frame=frame)

def pose(**kw):
    P = {}
    for k, v in kw.items(): P[k] = v
    return P
def merge(*ds):
    o = {}
    for x in ds: o.update(x)
    return o

# base arms-at-rest pose (relaxed). Right arm holds phone near waist.
REST_L = dict(LeftArm=(0, 4, 0), LeftForeArm=(-14, 0, 0), LeftHand=(0, 0, 0))
HOLD_R = dict(RightArm=(-14, -4, 0), RightForeArm=(-62, 0, 0), RightHand=(-10, 0, 0, 0))
def body(sway=0.0, breath=0.0, headyaw=0.0, headpitch=0.0, headroll=0.0, lean=0.0):
    return dict(Hips=(0, 0, sway * 1.6), Spine=(lean + breath * 0.4, 0, -sway * 0.8), Spine1=(breath * 0.6, 0, -sway * 0.6),
                Spine2=(breath, 0, -sway * 0.4), Neck=(headpitch * 0.4, headroll * 0.4, headyaw * 0.4),
                Head=(headpitch * 0.6, headroll * 0.6, headyaw * 0.6),
                LeftShoulder=(0, 0, 0), RightShoulder=(0, 0, 0),
                LeftUpLeg=(0, 0, 0), RightUpLeg=(0, 0, 0))
LEGS_REST = dict(LeftUpLeg=(0, 0, 0), RightUpLeg=(0, 0, 0))

shape_keys_objs = [O["CHAR_Customer_LOD0"], O["CHAR_Customer_LOD1"]]
def shape_val(name, frame, v):
    for o in shape_keys_objs:
        kb = o.data.shape_keys.key_blocks[name]; kb.value = v; kb.keyframe_insert("value", frame=frame)
def blink(f, dur=5, skip=False):
    for nm in ("eyeBlinkLeft", "eyeBlinkRight"):
        shape_val(nm, f - dur // 2 - 1, 0.0); shape_val(nm, f, 1.0); shape_val(nm, f + dur // 2 + 1, 0.0)

def start_clip(name):
    ad = rig.animation_data_create()
    act = bpy.data.actions.new(name); ad.action = act
    for o in shape_keys_objs:
        k = o.data.shape_keys; kad = k.animation_data_create()
        kad.action = bpy.data.actions.new(name + "_face")
    return act
def zero_keys():
    for o in shape_keys_objs:
        for kb in o.data.shape_keys.key_blocks:
            if kb.name != "Basis": kb.value = 0.0
def end_clip(name, nframes):
    ad = rig.animation_data
    tr = ad.nla_tracks.new(); tr.name = name
    st = tr.strips.new(name, 0, ad.action); st.name = name
    st.frame_start = 0; st.frame_end = nframes
    ad.action = None
    for o in shape_keys_objs:
        k = o.data.shape_keys; kad = k.animation_data
        t2 = kad.nla_tracks.new(); t2.name = name
        s2 = t2.strips.new(name + "_face", 0, kad.action); s2.name = name
        kad.action = None
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    zero_keys()

def smoothloop(act):
    pass
GR = dict(GRIP)
def full(P): return merge(GR, LCURL, REST_L, HOLD_R, P)

# ---- Customer_Idle: 60 frames, breathing + weight shift
start_clip("Customer_Idle")
for f in range(0, 61, 10):
    t = f / 60.0 * 2 * math.pi
    P = full(body(sway=math.sin(t) * 0.8, breath=math.sin(t) * 1.4, headyaw=math.sin(t) * 3, headpitch=-2 + math.sin(2 * t) * 1.0))
    P["RightArm"] = (-14 + math.sin(t) * 1.5, -4, 0); P["RightForeArm"] = (-62 + math.sin(t + 1) * 2, 0, 0)
    keypose(f, P)
blink(40); shape_val("mouthSmile", 0, 0.0); shape_val("mouthSmile", 60, 0.0)
end_clip("Customer_Idle", 60)

# ---- Customer_Wait: 120 frames impatient: look around, foot tap, glance at phone
start_clip("Customer_Wait")
WF = [(0, 0, 0, -2, 0), (15, 1, 22, 0, 2), (35, 1, 22, 0, 2), (55, -1, -20, 0, -2), (75, -1, -20, 0, -2), (95, 0, 0, 14, 0), (110, 0, 0, 10, 0), (120, 0, 0, -2, 0)]
for (f, sw, yaw, pit, roll) in WF:
    t = f / 120.0 * 2 * math.pi
    P = full(body(sway=sw, breath=math.sin(t * 2) * 1.2, headyaw=yaw, headpitch=pit, headroll=roll, lean=1.5))
    P["RightForeArm"] = (-62 - (10 if 90 <= f <= 112 else 0), 0, 0)
    P["LeftArm"] = (0, 4, 0)
    tap = 0
    if 15 <= f <= 75: tap = 18 if (f // 5) % 2 == 0 else 0
    P["RightLeg"] = (tap * 0.8, 0, 0); P["RightFoot"] = (-tap * 0.6, 0, 0)
    keypose(f, P)
for f in range(20, 75, 5):
    pass
for f in range(15, 76, 5):
    P = full(body(sway=1, breath=0, headyaw=-20 if f > 50 else 22, headpitch=0, headroll=0, lean=1.5))
    tap = 18 if (f // 5) % 2 == 0 else 0
    P["RightLeg"] = (tap * 0.8, 0, 0); P["RightFoot"] = (-tap * 0.6, 0, 0)
    P["LeftArm"] = (0, 4, 0)
    keypose(f, P)
blink(25); blink(85); blink(112)
end_clip("Customer_Wait", 120)

# ---- Customer_FaceID: 90 frames raise phone to face, hold, lower
start_clip("Customer_FaceID")
import json
SOL = json.load(open(os.path.join(ROOT, "faceid_solution.json")))   # from s5b_faceid_solve.py
RAISE = {k: tuple(v) for k, v in SOL.items() if k != "PhoneRollY"}
def faceid(f, hp=4.0, hy=0.0):
    # phone held at the face for the whole clip (first == last pose)
    P = full(body(sway=0, breath=math.sin(f / 90 * 2 * math.pi) * 1.0, headyaw=hy, headpitch=hp, lean=4.0))
    for k, v in RAISE.items(): P[k] = tuple(v)
    fa = list(P["RightForeArm"]); fa[0] += math.sin(f / 90 * 2 * math.pi) * 1.5; P["RightForeArm"] = tuple(fa)
    P["LeftArm"] = (0, 4, 0)
    keypose(f, P)
for f, hp, hy in ((0, 4, 0), (15, 5, 2), (30, 4, 0), (45, 5, 3), (60, 4, -3), (75, 5, 0), (90, 4, 0)):
    faceid(f, hp, hy)
shape_val("mouthSmile", 0, 0.0); shape_val("mouthSmile", 62, 0.0); shape_val("mouthSmile", 74, 0.5); shape_val("mouthSmile", 90, 0.0)
shape_val("browUp", 0, 0.0); shape_val("browUp", 25, 0.6); shape_val("browUp", 60, 0.6); shape_val("browUp", 85, 0.0); shape_val("browUp", 90, 0.0)
blink(20); blink(52)
end_clip("Customer_FaceID", 90)

# ---- Customer_Happy: 72 frames, smile, bounce, fist pump with left arm
start_clip("Customer_Happy")
for f, up, bounce in ((0, 0, 0), (9, 0.5, 0.02), (18, 1.0, 0.0), (27, 1.0, 0.025), (36, 1.0, 0.0), (45, 0.8, 0.02), (54, 0.4, 0.0), (63, 0.1, 0.01), (72, 0, 0)):
    P = full(body(sway=math.sin(f / 72 * 4 * math.pi) * 1.2, breath=1.0, headyaw=math.sin(f / 72 * 2 * math.pi) * 6, headpitch=-4 - 3 * up, lean=-2 * up))
    P["LeftArm"] = (0 - 70 * up, 4 - 20 * up, 0); P["LeftForeArm"] = (-14 - 100 * up, 0, 0)
    P["RightArm"] = (-14 - 20 * up, -4 - 10 * up, 0); P["RightForeArm"] = (-62 - 20 * up, 0, 0)
    keypose(f, P, extra_loc=(0, 0, bounce))
for nm, pts in (("mouthSmile", ((0, 0.0), (9, 0.8), (18, 1.0), (54, 1.0), (72, 0.0))), ("browUp", ((0, 0.0), (12, 0.6), (54, 0.6), (72, 0.0)))):
    for f, v in pts: shape_val(nm, f, v)
blink(30)
end_clip("Customer_Happy", 72)

sc.frame_start = 0; sc.frame_end = 120
col.hide_viewport = False
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "CHAR_Customer.blend"))
print("DONE5", [t.name for t in rig.animation_data.nla_tracks])






# Solve the right-arm pose that holds the phone 17.5 cm in front of the face, screen toward face.
# Run: blender -b CHAR_Customer.blend -P s5b_faceid_solve.py   (writes faceid_solution.json next to the blend)
import bpy, math, random, json, os, numpy as np
from mathutils import Euler, Matrix, Vector, Quaternion
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
O = bpy.data.objects; rig = O["CHAR_Customer"]; phone = O["PROP_Phone"]
for t in rig.animation_data.nla_tracks: t.mute = True
rig.animation_data.action = None
bn = {b.name.split(":")[1]: b for b in rig.data.bones}
Rr = {k: b.matrix_local.to_3x3() for k, b in bn.items()}
Rdir = {k: (b.tail_local - b.head_local).normalized() for k, b in bn.items()}
def basis(bone, spec):
    rx, ry, rz = spec[:3]; roll = spec[3] if len(spec) > 3 else 0
    e = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_matrix()
    if roll: e = e @ Matrix.Rotation(math.radians(roll), 3, Rdir[bone])
    return (Rr[bone].inverted() @ e @ Rr[bone]).to_quaternion()
# reference (hold) pose of the rest of the body = the FaceID values used in s5 (lean 4, head pitch 4)
def bodyspec(lean=4.0, hp=4.0, hy=0.0, breath=0.0):
    return dict(Spine=(lean + breath * 0.4, 0, 0), Spine1=(breath * 0.6, 0, 0), Spine2=(breath, 0, 0),
                Neck=(hp * 0.4, 0, hy * 0.4), Head=(hp * 0.6, 0, hy * 0.6))
# grip fingers (same recipe as s5)
wrist = np.array(bn["RightHand"].head_local); mid = np.array(bn["RightHandMiddle1"].head_local)
idx = np.array(bn["RightHandIndex1"].head_local); pin = np.array(bn["RightHandPinky1"].head_local)
d = mid - wrist; d /= np.linalg.norm(d); side = idx - pin; side /= np.linalg.norm(side)
n_ = np.cross(d, side)
if np.dot(n_, np.array([0, -0.02, 1.2]) - wrist) < 0: n_ = -n_
n_ /= np.linalg.norm(n_)
curl_axis = Vector(np.cross(d, n_)).normalized()
def curlq(deg): return Quaternion(curl_axis, math.radians(deg))
GRIP = {}
for f in ("Index", "Middle", "Ring", "Pinky"):
    for j, a in zip((1, 2, 3), (55, 70, 45)): GRIP["RightHand%s%d" % (f, j)] = curlq(a)
GRIP["RightHandThumb1"] = curlq(-18); GRIP["RightHandThumb2"] = curlq(-20)

def setp(P):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = Quaternion((1, 0, 0, 0)); pb.location = (0, 0, 0)
    for k, v in GRIP.items(): rig.pose.bones["mixamorig:" + k].rotation_quaternion = Matrix.to_quaternion(Rr[k].inverted() @ v.to_matrix() @ Rr[k])
    for k, v in P.items(): rig.pose.bones["mixamorig:" + k].rotation_quaternion = basis(k, v)
    bpy.context.view_layer.update()

NOSE0 = Vector((0.0, -0.174, 1.636))
headb = rig.data.bones["mixamorig:Head"]
nose_loc = headb.matrix_local.inverted() @ NOSE0
DIST = 0.175
LAT = Vector((0, 0, 0))
def face_frame():
    pbh = rig.pose.bones["mixamorig:Head"]
    mw = rig.matrix_world @ pbh.matrix
    nose = mw @ nose_loc
    fwd = (mw.to_3x3() @ headb.matrix_local.to_3x3().inverted() @ Vector((0, -1, 0))).normalized()
    return nose, fwd
BASIS0 = phone.matrix_basis.copy()
def evalp(p):
    phone.matrix_basis = BASIS0 @ Matrix.Rotation(math.radians(p[8]), 4, 'Y')
    P = dict(bodyspec())
    P["RightShoulder"] = (p[10], p[11], p[12])
    P["RightArm"] = tuple(p[0:3]); P["RightForeArm"] = (p[3], 0, p[4]); P["RightHand"] = (p[5], p[6], 0, p[7])
    setp(P)
    nose, fwd = face_frame()
    m = phone.matrix_world; M3 = m.to_3x3()
    ns = (M3 @ Vector((0, -1, 0))).normalized(); top = (M3 @ Vector((0, 0, 1))).normalized()
    sc = m.translation + ns * 0.0039
    rel = sc - nose
    dist = rel.dot(fwd)
    lateral = rel - fwd * dist
    toface = (nose - sc).normalized()
    cost = 6 * abs(dist - DIST) + 4 * (lateral - Vector((-0.045, 0, -0.01))).length + 0.8 * (1 - ns.dot(toface)) + 0.25 * (1 - ns.dot(-fwd))
    cost += 0.4 * max(0, 0.92 - top.z)
    elbow = rig.matrix_world @ rig.pose.bones["mixamorig:RightForeArm"].head
    wr = rig.matrix_world @ rig.pose.bones["mixamorig:RightHand"].head
    cost += 2 * max(0, elbow.z - (wr.z - 0.02)) + 3 * max(0, elbow.x + 0.13) + 1.0 * max(0, -0.12 - elbow.y)
    cost += 0.004 * (abs(p[5]) + abs(p[6]) + abs(p[7]) * 0.5) * 0.1
    cost += 0.002 * (abs(p[10]) + abs(p[11]) + abs(p[12]))
    return cost, dist, lateral, ns, toface, top, elbow, wr
lo = np.array([-170, -60, -110, -150, -80, -60, -60, -150, float(os.environ.get('PLO','-180')), 0, -15, -15, -15.]); hi = np.array([-10, 70, 110, -20, 80, 60, 60, 150, float(os.environ.get('PHI','180')), 0, 20, 15, 15.])
random.seed(2); np.random.seed(2)
best = None
for i in range(2500):
    p = lo + np.random.rand(13) * (hi - lo); c = evalp(p)[0]
    if best is None or c < best[0]: best = (c, p)
c0, p0 = best
for rnd in range(6):
    step = (hi - lo) * 0.08 / (rnd + 1)
    for i in range(1200):
        p = np.clip(p0 + np.random.randn(13) * step, lo, hi); c = evalp(p)[0]
        if c < c0: c0, p0 = c, p
    print("round", rnd, c0)
c, dist, lat, ns, toface, top, elbow, wr = evalp(p0)
print("SOLVED cost", c, "dist", dist, "lateral", tuple(lat), "n.toface", ns.dot(toface), "top", tuple(top), "elbow", tuple(elbow), "wrist", tuple(wr))
sol = dict(RightShoulder=[float(x) for x in p0[10:13]], RightArm=[float(x) for x in p0[0:3]], RightForeArm=[float(p0[3]), 0.0, float(p0[4])],
           RightHand=[float(p0[5]), float(p0[6]), 0.0, float(p0[7])], PhoneRollY=float(p0[8]))
json.dump(sol, open(os.path.join(ROOT, "faceid_solution.json"), "w"), indent=1)
print(sol)



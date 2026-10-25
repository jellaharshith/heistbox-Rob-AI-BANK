"""Stage 6: 8 clips as actions pushed to NLA tracks (30 fps). heister_s5d.blend -> heister_s6.blend"""
import bpy, os, sys, math
import numpy as np
from mathutils import Vector, Quaternion, Euler, Matrix
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, os.environ.get("ANIM_IN", "heister_s5d.blend")))
O = bpy.data.objects
sc = bpy.context.scene
sc.render.fps = 30; sc.render.fps_base = 1.0
rig = O["CHAR_Heister"]
body = O["CHAR_Heister_Body"]; mask = O["CHAR_Heister_Mask"]
REST = {b.name: b.matrix_local.to_quaternion() for b in rig.data.bones}
PB = rig.pose.bones
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
for pb in PB:
    pb.rotation_mode = 'QUATERNION'

def N(s):
    return "mixamorig:" + s
R = math.radians

def rd_to_basis(bone, rx=0, ry=0, rz=0):
    rd = Euler((R(rx), R(ry), R(rz)), 'XYZ').to_quaternion()
    r = REST[bone]
    return r.inverted() @ rd @ r

def loc_to_basis(bone, v):
    return REST[bone].inverted() @ Vector(v)

# ---------------------------------------------------------------- pose builders
LEFT = ["Left", "Right"]
def pose_frame(f, spec):
    """spec: dict bone-short -> (rx,ry,rz) or ('loc', (x,y,z)); applies to all pose bones (others reset)."""
    for pb in PB:
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = (0, 0, 0)
    for k, v in spec.items():
        if k.endswith(":loc"):
            b = N(k[:-4])
            PB[b].location = loc_to_basis(b, v)
        else:
            b = N(k)
            PB[b].rotation_quaternion = rd_to_basis(b, *v)

def key_pose(f, spec):
    pose_frame(f, spec)
    for pb in PB:
        pb.keyframe_insert("rotation_quaternion", frame=f)
        if pb.name == N("Hips"):
            pb.keyframe_insert("location", frame=f)

def add(spec, k, v):
    old = spec.get(k, (0, 0, 0))
    spec[k] = (old[0] + v[0], old[1] + v[1], old[2] + v[2])

def relaxed_arms(spec, amount=1.0):
    add(spec, "LeftArm", (0, 28 * amount, 0)); add(spec, "RightArm", (0, -28 * amount, 0))
    add(spec, "LeftForeArm", (-14 * amount, 0, 0)); add(spec, "RightForeArm", (-14 * amount, 0, 0))

def curl_hands(spec, amount):
    for side in LEFT:
        for fn in ("Index", "Middle", "Ring", "Pinky"):
            for i in (1, 2, 3):
                add(spec, f"{side}Hand{fn}{i}", (-amount * 55, 0, 0)) if False else None

def finger_curl(spec, amount, sides=("Left", "Right")):
    # fingers point forward/down in rest; curl about X so tips go up/back
    for side in sides:
        for fn in ("Index", "Middle", "Ring", "Pinky"):
            for i in (1, 2, 3):
                add(spec, f"{side}Hand{fn}{i}", (amount * 40, 0, 0))

# ---------------------------------------------------------------- clips
def idle(t):   # t in [0,1)
    w = 2 * math.pi * t
    s = {}
    relaxed_arms(s)
    add(s, "Spine1", (1.2 * math.sin(w), 0, 0)); add(s, "Spine2", (1.6 * math.sin(w), 0, 0))
    add(s, "LeftShoulder", (0, 0, 1.0 * math.sin(w))); add(s, "RightShoulder", (0, 0, -1.0 * math.sin(w)))
    add(s, "Head", (-1.5 * math.sin(w), 2.0 * math.sin(w * 1.0 + 0.8), 3 * math.sin(w)))
    s["Hips:loc"] = (0.006 * math.sin(w), 0, 0.003 * math.sin(2 * w))
    add(s, "Hips", (0, 1.2 * math.sin(w), 0))
    add(s, "Spine", (0, -1.2 * math.sin(w), 0))
    add(s, "LeftArm", (2 * math.sin(w), 0, 0)); add(s, "RightArm", (-2 * math.sin(w + 0.5), 0, 0))
    finger_curl(s, 0.35)
    return s

def gait(t, A, K, arm, elbow, lean, bob, sway, crouch=0.0, twist=6, hipdrop=2.0, foot_k=0.7):
    w = 2 * math.pi * t
    s = {}
    for side, ph, sg in (("Left", 0.0, 1), ("Right", math.pi, -1)):
        th = -A * math.sin(w + ph) - crouch * 0.55
        kn = K * max(0.0, math.cos(w + ph)) ** 1.4 + crouch * 1.0 + 4
        s[f"{side}UpLeg"] = (th, 0, 0)
        s[f"{side}Leg"] = (kn, 0, 0)
        s[f"{side}Foot"] = (-(th + kn) * foot_k, 0, 0)
        s[f"{side}ToeBase"] = (6 * max(0, -math.sin(w + ph)), 0, 0)
        # arms (opposite to same-side leg)
        s[f"{side}Arm"] = (arm * math.sin(w + ph) * 1.0, 28 * sg, 0)
        s[f"{side}ForeArm"] = (-(elbow + 0.3 * elbow * math.sin(w + ph)), 0, 0)
    s["Hips"] = (lean * 0.3, 0, twist * math.sin(w))
    s["Spine"] = (lean * 0.3, 0, -twist * 0.35 * math.sin(w))
    s["Spine1"] = (lean * 0.3, 0, -twist * 0.35 * math.sin(w))
    s["Spine2"] = (lean * 0.1, 0, -twist * 0.3 * math.sin(w))
    s["Head"] = (-lean * 0.7, 0, 0.8 * twist * math.sin(w) * 0.35)
    s["Hips:loc"] = (sway * math.sin(w), 0, -bob * 0.5 * (1 + math.cos(2 * w)) - crouch * 0.0042)
    add(s, "Hips", (0, hipdrop * math.sin(w), 0))
    finger_curl(s, 0.4)
    return s

# ------------------------------------------------------------------ foot-planted gait (analytic stance trajectory + numeric 3-DOF leg IK)
# In-place cycles; the game moves the root forward at speed v (m/s).  The planted foot moves BACKWARD relative to the root at exactly v
# (linear in the stance phase), so it does not slide on the ground.  Stance duty d, swing = hermite arc with end velocity -v.
GAIT = {
    #         v m/s, duty, swing lift (m), reach factor (knee bend), foot x, toe-down/toe-up pitch (deg), period s
    "Walk":  dict(v=1.2, d=0.56, lift=0.06, lf=0.975, fx=0.150, P0=15, P1=12, T=32 / 30),
    "Run":   dict(v=3.0, d=0.34, lift=0.18, lf=0.92, fx=0.125, P0=25, P1=10, T=24 / 30),
    "Sneak": dict(v=0.8, d=0.58, lift=0.05, lf=0.84, fx=0.160, P0=10, P1=8, T=48 / 30),
}
ANK0 = Vector((0.1806, -0.0227, 0.0984))   # rest ankle (left); right is mirrored in x
LEG_L = 0.80

def foot_target(u, g, side):
    d, v, T = g["d"], g["v"], g["T"]
    a = v * d * T / 2.0
    uu = (u + (0.0 if side == "Left" else 0.5) - (1 - d) / 2.0) % 1.0
    if uu < d:                       # stance: heel strike (front) -> toe off (back), speed exactly -v relative to root
        f = a - 2 * a * (uu / d); z = ANK0.z; pitch = 0.0
    else:                            # swing
        s = (uu - d) / (1 - d); Ts = (1 - d) * T
        m = -v * Ts
        h00 = 2 * s ** 3 - 3 * s ** 2 + 1; h10 = s ** 3 - 2 * s ** 2 + s; h01 = -2 * s ** 3 + 3 * s ** 2; h11 = s ** 3 - s ** 2
        f = h00 * (-a) + h10 * m + h01 * a + h11 * m
        pitch = g["P0"] * math.sin(2 * math.pi * s) if s < 0.5 else -g["P1"] * math.sin(2 * math.pi * (s - 0.5))
        # lowest sole point (heel -5 cm, ball +11.6 cm, tip +18.6 cm from ankle) must clear the ground by the swing lift
        pr = math.radians(pitch)
        zreq = max(ANK0.z * math.cos(pr) + fp * math.sin(pr) for fp in (-0.05, 0.116, 0.186))
        e = min(s, 1 - s) / 0.05
        marg = 0.04 * (3 * min(e, 1) ** 2 - 2 * min(e, 1) ** 3)      # clear the 3 cm "planted" band within ~1 frame of lift-off / before touch-down
        z = zreq + marg + g["lift"] * math.sin(math.pi * s) ** 0.6
    sx = 1 if side == "Left" else -1
    return Vector((sx * g["fx"], ANK0.y - f, z)), pitch, uu < d

def Rx(deg):
    return Quaternion((1, 0, 0), R(deg))

_warm = {}
def foot_ik(spec, u, g, key):
    """overwrite hips z, UpLeg/Leg/Foot of spec so ankles follow foot_target (3-DOF numeric solve on the evaluated rig)."""
    tg = {sd: foot_target(u, g, sd) for sd in ("Left", "Right")}
    for sd in ("Left", "Right"):
        spec[sd + "UpLeg"] = (0, 0, 0); spec[sd + "Leg"] = (0, 0, 0); spec[sd + "Foot"] = (0, 0, 0); spec[sd + "ToeBase"] = (0, 0, 0)
    loc = spec["Hips:loc"]
    spec["Hips:loc"] = (loc[0], loc[1], 0.0)
    pose_frame(0, spec); bpy.context.view_layer.update()
    reach = g["lf"] * LEG_L
    bounds = []
    for sd in ("Left", "Right"):
        hj = PB[N(sd + "UpLeg")].head.copy()
        t = tg[sd][0]
        dx, dy = hj.x - t.x, hj.y - t.y
        r2 = reach ** 2 - dx * dx - dy * dy
        bounds.append(t.z + math.sqrt(max(r2, 0.01)) - hj.z)
    k = 60.0
    zsoft = -math.log(sum(math.exp(-k * b) for b in bounds)) / k          # soft-min of the two reach bounds
    spec["Hips:loc"] = (loc[0], loc[1], zsoft)
    pose_frame(0, spec); bpy.context.view_layer.update()
    for sd in ("Left", "Right"):
        up, lg, ft = PB[N(sd + "UpLeg")], PB[N(sd + "Leg")], PB[N(sd + "Foot")]
        tgt = tg[sd][0]
        def ev(q):
            up.rotation_quaternion = rd_to_basis(N(sd + "UpLeg"), q[0], q[2], 0)
            lg.rotation_quaternion = rd_to_basis(N(sd + "Leg"), q[1], 0, 0)
            bpy.context.view_layer.update()
            return ft.head.copy() - tgt
        starts = [_warm.get((key, sd), (-10.0, 20.0, 0.0)), (-10.0, 20.0, 0.0), (-25.0, 50.0, 0.0), (10.0, 15.0, 0.0), (-5.0, 5.0, 0.0), (-30.0, 80.0, 0.0)]
        best = None
        def solve(q):
            lam = 1e-3
            for it in range(40):
                r0 = ev(q)
                if r0.length < 2e-4:
                    break
                J = np.zeros((3, 3))
                for j in range(3):
                    q2 = list(q); q2[j] += 0.5
                    J[:, j] = np.array((ev(q2) - r0)[:]) / 0.5
                Ja = J.T @ J + lam * np.eye(3)
                dq = np.clip(-np.linalg.solve(Ja, J.T @ np.array(r0[:])), -25, 25)
                qn = list(np.array(q) + dq)
                if ev(qn).length > r0.length * 1.5:
                    lam *= 10; continue
                q = qn; lam = max(lam * 0.3, 1e-6)
            return q, ev(q).length
        q = None
        for st in starts:
            q, res = solve(list(st))
            if res < 0.002:
                break
        res = ev(q).length
        if res > 0.005:
            print("IK residual %.1f mm at %s %s u=%.3f" % (res * 1000, key, sd, u))
        _warm[(key, sd)] = tuple(q)
        spec[sd + "UpLeg"] = (q[0], q[2], 0.0); spec[sd + "Leg"] = (q[1], 0, 0)
        # flat/pitched foot with fixed world yaw: D_foot = Rx(pitch)
        Dleg = lg.matrix.to_quaternion() @ REST[N(sd + "Leg")].inverted()
        rdq = Dleg.inverted() @ Rx(tg[sd][1])
        e = rdq.to_euler('XYZ')
        spec[sd + "Foot"] = (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
    return spec

def walk(t):
    s = gait(t, A=26, K=48, arm=20, elbow=22, lean=4, bob=0.03, sway=0.018)
    return foot_ik(s, t, GAIT["Walk"], "Walk")

def run(t):
    s = gait(t, A=48, K=100, arm=50, elbow=85, lean=14, bob=0.07, sway=0.02, twist=10, foot_k=0.5)
    return foot_ik(s, t, GAIT["Run"], "Run")

def sneak(t):
    s = gait(t, A=17, K=40, arm=8, elbow=40, lean=22, bob=0.012, sway=0.03, crouch=0, twist=4)
    add(s, "Head", (-16, 0, 0))
    s["Hips:loc"] = (s["Hips:loc"][0], 0.05, 0.0)
    return foot_ik(s, t, GAIT["Sneak"], "Sneak")

def talk(t):
    w = 2 * math.pi * t
    s = idle(t)
    # right-hand gesturing, head nods
    add(s, "RightArm", (-38 - 12 * math.sin(2 * w), -10, -8))
    add(s, "RightForeArm", (-52 - 22 * math.sin(2 * w + 1.0), 0, 0))
    add(s, "RightHand", (14 * math.sin(2 * w + 0.5), 0, 22 * math.sin(2 * w)))
    add(s, "LeftArm", (-12 + 6 * math.sin(2 * w + 2.0), -6, 0))
    add(s, "LeftForeArm", (-26 * (0.5 + 0.5 * math.sin(2 * w + 2.0)), 0, 0))
    add(s, "Head", (-3 + 4 * math.sin(2 * w + 0.4), 5 * math.sin(w), 3 * math.sin(2 * w)))
    add(s, "Neck", (2 * math.sin(2 * w), 0, 0))
    add(s, "Spine2", (0, 0, 3 * math.sin(w)))
    return s

def smooth(x):
    return x * x * (3 - 2 * x)

BRIBE_ARM = float(os.environ.get("BRIBE_ARM", -15)); BRIBE_FORE = float(os.environ.get("BRIBE_FORE", -45))
def bribe(t):   # one-shot: lean in, reach hand out with envelope, hold, flick, retract
    s = idle(t * 0.0)
    a = smooth(min(1, t / 0.28))                     # reach
    hold = 1.0 if t < 0.62 else 1 - smooth((t - 0.62) / 0.38)
    k = a * hold
    add(s, "RightArm", (BRIBE_ARM * k, -8 * k, -14 * k))
    add(s, "RightForeArm", (BRIBE_FORE * k, 0, 0))
    add(s, "RightHand", (-10 * k + 12 * math.sin(t * 40) * 0.5 * k * (1 if 0.4 < t < 0.62 else 0), 0, 0))
    add(s, "LeftArm", (-10 * k, 0, 0)); add(s, "LeftForeArm", (-20 * k, 0, 0))
    add(s, "Spine1", (10 * k, 0, 0)); add(s, "Spine2", (8 * k, 0, 6 * k)); add(s, "Hips", (6 * k, 0, 0))
    add(s, "Head", (-8 * k + 6 * math.sin(t * 2 * math.pi * 2) * k, 0, 0))
    for fn in ("Index", "Middle", "Ring", "Pinky"):
        for i in (1, 2, 3):
            add(s, f"RightHand{fn}{i}", (-25 * k, 0, 0))
    s["Hips:loc"] = (0, -0.03 * k, -0.02 * k)
    s["LeftUpLeg"] = (-6 * k, 0, 0); s["RightUpLeg"] = (-10 * k, 0, 0)
    s["LeftLeg"] = (8 * k, 0, 0); s["RightLeg"] = (14 * k, 0, 0)
    return s

def caught(t):  # one-shot: freeze, hands up, flinch down
    s = {}
    a = smooth(min(1, t / 0.35))
    flinch = math.exp(-((t - 0.12) / 0.07) ** 2) * (1 if t < 0.5 else 0)
    relaxed_arms(s, 1 - a)
    for side, sg in (("Left", 1), ("Right", -1)):
        add(s, f"{side}Arm", (-28 * a, -sg * 78 * a, 0))   # raise (swing arms out + up)
        add(s, f"{side}ForeArm", (-14 * a, -sg * 58 * a, 0))
        add(s, f"{side}Hand", (-20 * a, 0, 0))
    shiver = 0.6 * math.sin(t * 60) * a * (0.4 + 0.6 * smooth(min(1, max(0, (t - 0.4) / 0.3))))
    add(s, "Spine1", (-4 * a + 8 * flinch, 0, shiver)); add(s, "Spine2", (-6 * a + 6 * flinch, 0, -shiver))
    add(s, "Head", (-10 * a - 6 * flinch, 8 * a * math.sin(t * 9) * 0.0, 0))
    add(s, "Neck", (-6 * a, 0, 0))
    s["Hips:loc"] = (0, 0, -0.05 * a - 0.04 * flinch)
    s["LeftUpLeg"] = (-14 * a - 10 * flinch, 0, 0); s["RightUpLeg"] = (-14 * a - 10 * flinch, 0, 0)
    s["LeftLeg"] = (26 * a + 18 * flinch, 0, 0); s["RightLeg"] = (26 * a + 18 * flinch, 0, 0)
    s["LeftFoot"] = (-12 * a, 0, 0); s["RightFoot"] = (-12 * a, 0, 0)
    finger_curl(s, -0.6 * a)
    return s

def celebrate(t):   # loop: two hops, arms up, fist pumps
    w = 2 * math.pi * t
    hop = max(0.0, math.sin(2 * w)) ** 1.0
    crouch = max(0.0, -math.sin(2 * w)) * 0.8
    s = {}
    for side, sg in (("Left", 1), ("Right", -1)):
        up = 0.7 + 0.3 * math.sin(2 * w + (0 if sg > 0 else math.pi * 0.5))
        s[f"{side}Arm"] = (-35 * up, -sg * (115 * up + 10), 0)
        s[f"{side}ForeArm"] = (-70 + 25 * math.sin(2 * w), 0, 0)
        s[f"{side}UpLeg"] = (-10 - 22 * crouch + 14 * hop, 0, 0)
        s[f"{side}Leg"] = (20 + 46 * crouch + 18 * hop, 0, 0)
        s[f"{side}Foot"] = (-8 - 18 * crouch - 10 * hop, 0, 0)
    s["Hips:loc"] = (0.01 * math.sin(w), 0, 0.14 * hop - 0.12 * crouch)
    s["Spine1"] = (-4 + 5 * crouch, 0, 5 * math.sin(w))
    s["Spine2"] = (-8 + 4 * crouch, 0, -5 * math.sin(w))
    s["Head"] = (-12 + 4 * math.sin(2 * w), 6 * math.sin(w), 0)
    s["Hips"] = (0, 0, 4 * math.sin(w))
    finger_curl(s, 1.2)
    return s

# shape-key animation tables per clip: {key: [(norm_time, value), ...]} (loop clips start/end at 0)
def vis_seq(n, keys, amp=0.8):
    out = {}
    for i in range(n):
        k = keys[i % len(keys)]
        t0 = i / n; tm = (i + 0.5) / n
        out.setdefault(k, []).extend([(t0, 0.0), (tm, amp * (0.6 + 0.4 * ((i * 7) % 3) / 2)), ((i + 1) / n, 0.0)])
    return out

SHAPES = {
    "Idle": {"eyeBlinkLeft": [(0, 0), (0.30, 0), (0.32, 1), (0.345, 0), (0.80, 0), (0.82, 1), (0.84, 0), (1, 0)],
             "eyeBlinkRight": [(0, 0), (0.30, 0), (0.32, 1), (0.345, 0), (0.80, 0), (0.82, 1), (0.84, 0), (1, 0)],
             "browUp": [(0, 0), (0.5, 0.15), (1, 0)]},
    "Walk": {}, "Run": {"jawOpen": [(0, 0.12), (0.25, 0.3), (0.5, 0.12), (0.75, 0.3), (1, 0.12)]}, "Sneak": {"browDown": [(0, 0.5), (1, 0.5)]},
    "Talk": {**vis_seq(14, ["viseme_aa", "viseme_E", "viseme_O", "viseme_DD", "viseme_U", "viseme_FF", "viseme_I", "viseme_PP"]),
             "jawOpen": [(i / 28.0, v) for i, v in enumerate([0, .5, .1, .7, .2, .6, .1, .5, 0, .6, .2, .5, .1, .7, 0, .4, .2, .6, .1, .5, 0, .6, .2, .5, .1, .5, .2, .4])] + [(1.0, 0)],
             "eyeBlinkLeft": [(0, 0), (0.55, 0), (0.57, 1), (0.6, 0), (1, 0)], "eyeBlinkRight": [(0, 0), (0.55, 0), (0.57, 1), (0.6, 0), (1, 0)],
             "browUp": [(0, 0), (0.2, 0.4), (0.5, 0.1), (0.8, 0.5), (1, 0)], "mouthSmile": [(0, 0), (0.5, 0.2), (1, 0)]},
    "Bribe": {"mouthSmile": [(0, 0), (0.3, 0.7), (0.65, 0.7), (1, 0)], "browUp": [(0, 0), (0.3, 0.5), (0.65, 0.5), (1, 0)],
              "eyeBlinkLeft": [(0, 0), (0.7, 0), (0.75, 1), (0.8, 0), (1, 0)], "eyeBlinkRight": [(0, 0), (0.7, 0), (0.75, 1), (0.8, 0), (1, 0)]},
    "Caught": {"jawOpen": [(0, 0), (0.15, 0.9), (0.5, 0.6), (1, 0.5)], "browUp": [(0, 0), (0.12, 1.0), (1, 0.9)],
               "eyeBlinkLeft": [(0, 0), (0.1, 0), (0.15, 0.7), (0.4, 0), (1, 0)], "eyeBlinkRight": [(0, 0), (0.1, 0), (0.15, 0.7), (0.4, 0), (1, 0)]},
    "Celebrate": {"mouthSmile": [(0, 0.9), (1, 0.9)], "jawOpen": [(0, 0.2), (0.25, 0.7), (0.5, 0.2), (0.75, 0.7), (1, 0.2)], "browUp": [(0, 0.6), (1, 0.6)]},
}

CLIPS = [  # name, builder, frames, loop
    ("Idle", idle, 90, True), ("Walk", walk, 32, True), ("Run", run, 24, True), ("Sneak", sneak, 48, True),
    ("Talk", talk, 90, True), ("Bribe", bribe, 75, False), ("Caught", caught, 60, False), ("Celebrate", celebrate, 48, True),
]

# ---------------------------------------------------------------- build actions
def ensure_ad(idb):
    if idb.animation_data is None:
        idb.animation_data_create()
    return idb.animation_data

def key_value_blocks(owner_obj):
    k = owner_obj.data.shape_keys
    return k

_hidden = [o for o in O if o.type == 'MESH' and not o.hide_viewport]
for o in _hidden:
    o.hide_viewport = True      # speeds up depsgraph updates during the IK solve (restored below)
arm_ad = ensure_ad(rig)
sk_body = body.data.shape_keys; sk_mask = mask.data.shape_keys
sk_ads = [ensure_ad(sk_body), ensure_ad(sk_mask)]
tracks = {}

def push_nla(idb, act, name, start=1):
    ad = idb.animation_data
    ad.action = None
    tr = ad.nla_tracks.new(); tr.name = name
    st = tr.strips.new(name, start, act)
    st.name = name
    try:
        if len(act.slots):
            st.action_slot = act.slots[0]
    except Exception as e:
        print("slot assign", e)
    st.extrapolation = 'NOTHING' if True else 'HOLD'
    return tr

for name, fn, nframes, loop in CLIPS[::-1]:
    cname = "Heister_" + name
    # ---- armature action
    act = bpy.data.actions.new(cname)
    arm_ad.action = act
    for pb in PB:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    step = 1 if nframes <= 60 else 2
    # loops: frames 0..nframes (period = nframes frames, last key == first key -> seamless, duration = nframes/30 s)
    # one-shots: frames 1..nframes
    f0 = 0 if loop else 1
    f1 = nframes if loop else nframes
    span = (f1 - f0)
    frames = list(range(f0, f1 + 1, step))
    if frames[-1] != f1:
        frames.append(f1)
    for f in frames:
        t = (f - f0) / span
        if loop and f == f1:
            t = 0.0
        if f == frames[0]:
            for _ in range(2):            # warm-up: first depsgraph evaluation of a fresh pose can be stale
                pose_frame(f, fn(t)); bpy.context.view_layer.update()
            _warm.clear()
        key_pose(f, fn(t))
    act.use_fake_user = True
    try:
        act.use_frame_range = True; act.frame_start = f0; act.frame_end = f1
    except Exception:
        pass
    push_nla(rig, act, cname, start=f0)
    # ---- shape-key actions (body + mask)
    for sk, owner_ad in zip((sk_body, sk_mask), sk_ads):
        sact = bpy.data.actions.new(cname + "_" + ("Body" if sk is sk_body else "Mask") + "Keys")
        owner_ad.action = sact
        for kb in sk.key_blocks:
            kb.value = 0.0
        for key, seq in SHAPES.get(name, {}).items():
            if key not in sk.key_blocks:
                continue
            for tn, val in seq:
                f = f0 + tn * span
                sk.key_blocks[key].value = val
                sk.key_blocks[key].keyframe_insert("value", frame=f)
            sk.key_blocks[key].value = 0.0
        sact.use_fake_user = True
        try:
            if loop:
                sact.use_frame_range = True; sact.frame_start = f0; sact.frame_end = f1 - 1
        except Exception:
            pass
        push_nla(sk_body.id_data if False else (body if sk is sk_body else mask).data.shape_keys, sact, cname, start=f0)
        # NLA owner is the Key datablock (ID with animation_data)
    print("built", cname, nframes, "frames", "loop" if loop else "once")

bpy.ops.object.mode_set(mode='OBJECT')
for o in _hidden:
    o.hide_viewport = False
for pb in PB:
    pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
sc.frame_start = 1; sc.frame_end = 90
for ad in [arm_ad] + sk_ads:
    ad.action = None
print("NLA tracks armature", [t.name for t in arm_ad.nla_tracks])
print("NLA tracks body keys", [t.name for t in sk_ads[0].nla_tracks])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s6.blend"))





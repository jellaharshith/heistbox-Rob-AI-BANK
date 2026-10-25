"""Stage 6: 6 clips as NLA tracks (30 fps) on CHAR_Tina armature -> tina/CHAR_Tina.blend"""
import sys, math
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
import bpy
import nla_utils as nla, preview_utils as pv

ROOT = r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina"
bpy.ops.wm.open_mainfile(filepath=ROOT + "/scripts/_stage5.blend")
arm = bpy.data.objects["CHAR_Tina"]
nla.set_fps(30)
sc = bpy.context.scene
TAU = 2 * math.pi
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
M = "mixamorig:"
SIDES = (("Left", 1), ("Right", -1))


def sin(t, ph=0.0, k=1):
    return math.sin(TAU * (k * t + ph))


def relaxed_arms(d, drop=22, fwd=0, elbow=10):
    """arms hanging a bit closer to the body than the A-pose rest; fwd swings arms forward (deg)"""
    for side, s in SIDES:
        d[M + side + "Arm"] = [(Y, s * drop), (Z, -s * fwd)]
        d[M + side + "ForeArm"] = [(X, -elbow)]


def finger_curl(d, amount, thumb=0.5, sides=("Left", "Right"), spread_phase=None, t=0.0, wiggle=0.0):
    for side in sides:
        for fi, fn in enumerate(("Index", "Middle", "Ring", "Pinky")):
            for j in (1, 2, 3):
                a = amount * (0.6 + 0.2 * j)
                if wiggle:
                    a += wiggle * sin(t * 2, fi * 0.2 + (0.5 if side == "Right" else 0)) * (1 if j > 1 else 0.5)
                s = 1 if side == "Left" else -1
                d[M + side + "Hand" + fn + str(j)] = {"local": ((1, 0, 0), a)}
        for j in (1, 2, 3):
            d[M + side + "HandThumb" + str(j)] = {"local": ((1, 0, 0), amount * thumb)}


def idle(t):
    d = {}
    relaxed_arms(d, 20, 4, 14)
    b = sin(t)
    d[M + "Spine"] = [(X, 1.0 * b)]
    d[M + "Spine1"] = [(X, 1.4 * b)]
    d[M + "Spine2"] = [(X, 1.8 * b), (Z, 1.2 * sin(t, 0.25))]
    d[M + "Neck"] = [(X, -1.0 * b), (Z, 2.0 * sin(t, 0.1))]
    d[M + "Head"] = [(Z, 3.5 * sin(t, 0.0)), (Y, 1.5 * sin(t, 0.3)), (X, 1.0 * sin(t, 0.5, 2))]
    d[M + "LeftShoulder"] = [(Z, 0.0), (Y, 1.5 * b)]
    d[M + "RightShoulder"] = [(Y, -1.5 * b)]
    d[M + "Hips"] = {"loc": (0.004 * sin(t, 0.0), 0, 0.003 * b), "rot": [(Z, 1.0 * sin(t, 0.25))]}
    finger_curl(d, 14)
    return d


def talk(t):
    d = {}
    relaxed_arms(d, 18, 10, 20)
    b = sin(t, 0, 2)
    # left (+X) arm gestures in front while talking; right arm stays low
    g = 0.5 + 0.5 * sin(t, 0.0)
    d[M + "LeftArm"] = [(Y, 10 - 6 * g), (Z, -(38 + 14 * g))]
    d[M + "LeftForeArm"] = [(X, -(70 + 25 * g)), (Z, -8 * sin(t, 0.2))]
    d[M + "LeftHand"] = [(X, -10 + 18 * sin(t, 0.1, 2)), (Y, 8 * sin(t, 0.3))]
    d[M + "RightArm"] = [(Y, -22), (Z, 8)]
    d[M + "RightForeArm"] = [(X, -22 - 8 * sin(t, 0.5, 2))]
    d[M + "Spine1"] = [(X, 2 + 1.5 * b), (Z, 2.5 * sin(t, 0.0))]
    d[M + "Spine2"] = [(X, 1.5), (Z, 3 * sin(t, 0.0))]
    d[M + "Neck"] = [(X, 2 * sin(t, 0.0, 2)), (Z, 4 * sin(t, 0.25))]
    d[M + "Head"] = [(X, 3 + 4 * sin(t, 0.15, 2)), (Z, 5 * sin(t, 0.25)), (Y, 2 * sin(t, 0.0, 1))]
    finger_curl(d, 22, wiggle=4, t=t)
    d[M + "Hips"] = {"loc": (0.006 * sin(t, 0.0), 0, 0), "rot": [(Z, 1.5 * sin(t, 0.0))]}
    return d


def typing(t):
    d = {}
    for side, s in SIDES:
        d[M + side + "Arm"] = [(Y, s * 8), (Z, -s * 62)]
        d[M + side + "ForeArm"] = [(X, -(78 + 3 * sin(t, 0.0, 3) * 1)), (Z, s * 12)]
        d[M + side + "Hand"] = [(X, 22 + 5 * sin(t, 0.2 if s > 0 else 0.45, 4)), (Y, -s * 4)]
    d[M + "Spine"] = [(X, 4)]
    d[M + "Spine1"] = [(X, 5)]
    d[M + "Spine2"] = [(X, 4 + 0.8 * sin(t, 0, 3))]
    d[M + "Neck"] = [(X, 10)]
    d[M + "Head"] = [(X, 9 + 1.5 * sin(t, 0.3, 3)), (Z, 3 * sin(t, 0.0))]
    for side in ("Left", "Right"):
        off = 0.0 if side == "Left" else 0.37
        for fi, fn in enumerate(("Index", "Middle", "Ring", "Pinky")):
            for j in (1, 2, 3):
                a = 28 + 22 * max(0.0, sin(t, off + fi * 0.19, 6)) * (0.5 + 0.25 * j)
                d[M + side + "Hand" + fn + str(j)] = {"local": ((1, 0, 0), a)}
        for j in (1, 2, 3):
            d[M + side + "HandThumb" + str(j)] = {"local": ((1, 0, 0), 10 + 8 * max(0.0, sin(t, off + 0.5, 3)))}
    d[M + "Hips"] = {"loc": (0, 0, 0.0), "rot": [(Z, 0.0)]}
    return d


def smooth01(a, b, t):
    x = min(1.0, max(0.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)


def approve(t):
    """nod twice, thumbs-up style raised right hand, returns to the start pose (start == end)."""
    d = {}
    relaxed_arms(d, 20, 4, 14)
    up = smooth01(0.08, 0.30, t) * (1 - smooth01(0.72, 0.92, t))
    nod = max(0.0, sin(t, 0, 3)) * smooth01(0.2, 0.3, t) * (1 - smooth01(0.8, 0.9, t))
    d[M + "RightArm"] = [(Y, -(20 - 0 * up)), (Z, 62 * up), (X, 0)]
    d[M + "RightArm"] = [(Y, -(20 - 14 * up)), (Z, 52 * up)]
    d[M + "RightForeArm"] = [(X, -(14 + 100 * up))]
    d[M + "RightHand"] = [(X, 10 * up), (Z, 10 * up)]
    d[M + "Spine2"] = [(X, 2 * up), (Z, -4 * up)]
    d[M + "Neck"] = [(X, 3 * nod)]
    d[M + "Head"] = [(X, 14 * nod + 3 * up)]
    finger_curl(d, 14 + 55 * up, thumb=0.0 if False else 0.0, sides=("Right",))
    finger_curl(d, 14, sides=("Left",))
    for j in (1, 2, 3):
        d[M + "RightHandThumb" + str(j)] = {"local": ((1, 0, 0), -8 * up)}
    return d


def deny(t):
    """head shake x3 with a small waving hand; start == end."""
    d = {}
    relaxed_arms(d, 20, 4, 14)
    env = smooth01(0.05, 0.2, t) * (1 - smooth01(0.8, 0.95, t))
    shake = sin(t, 0, 3) * env
    d[M + "Head"] = [(Z, 22 * shake), (Y, 4 * shake)]
    d[M + "Neck"] = [(Z, 8 * shake)]
    d[M + "Spine2"] = [(Z, 3 * shake), (X, -2 * env)]
    d[M + "LeftArm"] = [(Y, 20 - 10 * env), (Z, -(40 * env))]
    d[M + "LeftForeArm"] = [(X, -(14 + 80 * env))]
    d[M + "LeftHand"] = [(Y, 28 * sin(t, 0, 3) * env), (X, -10 * env)]
    finger_curl(d, 8 + 0 * env, sides=("Left",))
    finger_curl(d, 14, sides=("Right",))
    return d


def alarm(t):
    """urgent: left hand to the headset ear, quick head snaps, tense jittery breathing (loop)."""
    d = {}
    relaxed_arms(d, 16, 6, 16)
    j = sin(t, 0, 6)
    d[M + "LeftArm"] = [(Y, 4), (Z, -30), (X, -10)]
    d[M + "LeftForeArm"] = [(X, -128), (Z, 14)]
    d[M + "LeftHand"] = [(X, -6 + 3 * j), (Z, 12)]
    d[M + "RightArm"] = [(Y, -26), (Z, 12)]
    d[M + "RightForeArm"] = [(X, -30)]
    d[M + "Spine"] = [(X, 2 + 1 * j)]
    d[M + "Spine2"] = [(X, 4 + 1.5 * sin(t, 0.1, 4)), (Z, 3 * sin(t, 0, 2))]
    d[M + "Neck"] = [(X, -2)]
    d[M + "Head"] = [(Z, -8 + 4 * sin(t, 0, 2)), (X, -4 + 2 * j), (Y, -5)]
    d[M + "Hips"] = {"loc": (0.003 * sin(t, 0, 6), 0, 0.004 * abs(sin(t, 0, 3))), "rot": []}
    finger_curl(d, 22 + 6 * j, sides=("Right",))
    finger_curl(d, 10, sides=("Left",))
    return d


CLIPS = [("Tina_Idle", idle, 120), ("Tina_Talk", talk, 120), ("Tina_Typing", typing, 90),
         ("Tina_Approve", approve, 90), ("Tina_Deny", deny, 90), ("Tina_Alarm", alarm, 60)]
for name, fn, frames in CLIPS:
    act = nla.make_clip(arm, name, fn, frames, step=3, loop=True)
    nla.push_to_nla(arm, act, name, start=1)
    print("clip", name, "frames 1..%d" % (frames + 1), "slots", [s.name_display for s in act.slots] if hasattr(act, "slots") else None)
nla.finalize(arm)
print(nla.list_tracks(arm))
sc.frame_start = 1
sc.frame_end = 121

# preview: evaluate each clip by temporarily soloing its action
if __name__ == "__main__" and "--noshots" not in sys.argv:
    ad = arm.animation_data
    for o in bpy.data.objects:
        if o.name.startswith("CHAR_Tina_LOD") and not o.name.endswith("0"):
            o.hide_render = True
    for name, fn, frames in CLIPS:
        act = bpy.data.actions[name]
        ad.action = act
        for tr in ad.nla_tracks:
            tr.mute = True
        for f, tag in ((1, "a"), (1 + frames // 4, "b"), (1 + frames // 2, "c")):
            sc.frame_set(f)
            pv.shot(ROOT + "/shots/clip_%s_%s.png" % (name, tag), target=(0, 0, 1.1), eye=(1.8, -2.6, 1.3), res=(360, 480), lens=45)
        ad.action = None
        for tr in ad.nla_tracks:
            tr.mute = False
    # montage
    import glob
    paths = []
    for name, fn, frames in CLIPS:
        for tag in "abc":
            paths.append(ROOT + "/shots/clip_%s_%s.png" % (name, tag))
    pv.montage(paths, 6, ROOT + "/shots/clips.png")
    # restore
    sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/scripts/_stage6.blend")

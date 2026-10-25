"""Measure upper-arm elevation per clip. blender -b <blend> -P measure_arms.py -- [out.json]
elev = angle between the upper-arm direction (UpperArm head -> ForeArm head, world) and the torso-down axis (Neck->Hips).
flex = forward/back component (sagittal plane), abd = sideways component (frontal plane), both in degrees from torso-down.
Also the clavicle (Shoulder bone) rotation magnitude vs rest."""
import bpy, math, sys, json
from mathutils import Vector
arm = bpy.data.objects["CHAR_Tina"]
ad = arm.animation_data
sc = bpy.context.scene
M = "mixamorig:"
out_path = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else None


def hw(name):
    return arm.matrix_world @ arm.pose.bones[name].head


def tw(name):
    return arm.matrix_world @ arm.pose.bones[name].tail


def measure():
    down = (hw(M + "Hips") - hw(M + "Neck")).normalized()
    fwd = Vector((0, -1, 0))
    right = down.cross(fwd).normalized()   # lateral axis
    fwd = right.cross(down).normalized()
    res = {}
    for side, sgn in (("Left", 1), ("Right", -1)):
        v = (hw(M + side + "ForeArm") - hw(M + side + "Arm")).normalized()
        elev = math.degrees(math.acos(max(-1, min(1, v.dot(down)))))
        f = math.degrees(math.atan2(v.dot(fwd), v.dot(down)))
        a = math.degrees(math.atan2(abs(v.dot(right)), v.dot(down)))
        sh = arm.pose.bones[M + side + "Shoulder"].rotation_quaternion.to_axis_angle()[1]
        res[side] = (elev, f, a, math.degrees(sh))
    return res


for tr in ad.nla_tracks:
    tr.mute = True
clips = {}
for tr in list(ad.nla_tracks):
    name = tr.name
    act = bpy.data.actions[name]
    ad.action = act
    try:
        ad.action_slot = act.slots[0]
    except Exception:
        pass
    n = int(round(act.frame_range[1] - act.frame_range[0]))
    best = {"Left": [0, 0, 0, 0], "Right": [0, 0, 0, 0]}
    first = last = None
    for f in range(1, n + 2, 2):
        sc.frame_set(f)
        r = measure()
        for s in r:
            for i in range(4):
                if abs(r[s][i]) > abs(best[s][i]) and (i != 1 or True):
                    best[s][i] = r[s][i]
        if first is None:
            first = r
    sc.frame_set(n + 1)
    last = measure()
    loopdiff = max(abs(first[s][0] - last[s][0]) for s in first)
    clips[name] = {"max_elev_L": round(best["Left"][0], 1), "max_elev_R": round(best["Right"][0], 1),
                   "flex_L": round(best["Left"][1], 1), "flex_R": round(best["Right"][1], 1),
                   "abd_L": round(best["Left"][2], 1), "abd_R": round(best["Right"][2], 1),
                   "clav_L": round(best["Left"][3], 1), "clav_R": round(best["Right"][3], 1), "loop_elev_diff": round(loopdiff, 2), "frames": n}
    print("CLIP", name, clips[name])
ad.action = None
if out_path:
    json.dump(clips, open(out_path, "w"), indent=1)

"""
nla_utils.py - author keyframed clips on an armature and push each one to its own NLA track (Blender 5.x slotted actions).

    import nla_utils as nla
    nla.set_fps(30)
    def sampler(t):                      # t in [0,1) over the clip
        return {"mixamorig:Head": [((1,0,0), 8*math.sin(2*math.pi*t))],   # list of (world_axis, degrees), applied in order
                "mixamorig:Hips": {"loc": (0,0,0.01)}}                    # optional location offset (metres, world)
    act = nla.make_clip(arm, "Tina_Idle", sampler, frames=120, step=3)    # frames 1..121, last key == first key (loop)
    nla.finalize(arm)                    # clears the active action, leaves only the NLA tracks

Public API
    set_fps(fps=30)
    world_rot_to_local_quat(arm, bone_name, axis_angles)   rotation about WORLD axes expressed in the bone's local frame (rest pose)
    make_clip(arm, name, sampler, frames, step=3, loop=True, start=1, interp='BEZIER') -> Action
    push_to_nla(arm, action, track_name=None, start=1)    -> NlaTrack  (assigns the action slot to the strip)
    finalize(arm)
    list_tracks(arm)
Conventions: action name == track name == strip name == clip name; every strip starts at frame `start` (parallel tracks).
Character front is -Y, left side +X, up +Z.
"""
import bpy, math
from mathutils import Matrix, Quaternion, Vector


def set_fps(fps=30):
    scn = bpy.context.scene
    scn.render.fps = fps
    scn.render.fps_base = 1.0


def _rest_basis(arm, bone_name):
    b = arm.data.bones[bone_name]
    return (arm.matrix_world @ b.matrix_local).to_3x3()


def world_rot_to_local_quat(arm, bone_name, axis_angles):
    R = Matrix.Identity(3)
    for axis, deg in axis_angles:
        R = Matrix.Rotation(math.radians(deg), 3, Vector(axis).normalized()) @ R
    B = _rest_basis(arm, bone_name)
    return (B.inverted() @ R @ B).to_quaternion()


def make_clip(arm, name, sampler, frames, step=3, loop=True, start=1, interp='BEZIER'):
    if arm.animation_data is None:
        arm.animation_data_create()
    ad = arm.animation_data
    act = bpy.data.actions.new(name)
    ad.action = act
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    keys = list(range(0, frames + 1, step))
    if keys[-1] != frames:
        keys.append(frames)
    touched = set()
    for k in keys:
        t = k / frames
        if loop and k == frames:
            t = 0.0
        pose = sampler(t)
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
        for bone, spec in pose.items():
            pb = arm.pose.bones[bone]
            if isinstance(spec, dict):
                if "loc" in spec:
                    B = _rest_basis(arm, bone)
                    pb.location = B.inverted() @ Vector(spec["loc"])
                    touched.add((bone, "location"))
                axa = spec.get("rot")
                if "local" in spec:      # (axis_xyz_local, degrees): rotate about the bone's own axis
                    ax, dg = spec["local"]
                    pb.rotation_quaternion = Quaternion(Vector(ax).normalized(), math.radians(dg))
                    touched.add((bone, "rotation_quaternion"))
            else:
                axa = spec
            if axa:
                pb.rotation_quaternion = world_rot_to_local_quat(arm, bone, axa)
                touched.add((bone, "rotation_quaternion"))
        f = start + k
        for bone, path in touched:
            arm.pose.bones[bone].keyframe_insert(path, frame=f)
    # make sure every touched channel has a key on every sample (keyframe_insert above runs for all touched)
    # interpolation
    for fc in _fcurves(act, arm):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
        # loop-friendly: no extrapolation drift
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    return act


def _fcurves(act, arm):
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
    except Exception:
        pass
    if not out:
        try:
            out = list(act.fcurves)
        except Exception:
            pass
    return out


def push_to_nla(arm, action, track_name=None, start=1):
    ad = arm.animation_data
    track = ad.nla_tracks.new()
    track.name = track_name or action.name
    strip = track.strips.new(action.name, int(start), action)
    strip.name = action.name
    try:
        if strip.action_slot is None and len(action.slots):
            strip.action_slot = action.slots[0]
    except Exception as e:
        print("slot:", e)
    return track


def finalize(arm):
    ad = arm.animation_data
    if ad:
        ad.action = None
        try:
            ad.action_slot = None
        except Exception:
            pass
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)


def list_tracks(arm):
    ad = arm.animation_data
    res = []
    for tr in ad.nla_tracks:
        for st in tr.strips:
            res.append((tr.name, st.action.name if st.action else None, st.frame_start, st.frame_end))
    return res

import bpy
O = bpy.data.objects
rig = O["CHAR_Heister"]
print("frame", bpy.context.scene.frame_current, "rig anim", rig.animation_data, [ (t.name, t.mute, [ (s.frame_start, s.frame_end, s.blend_type, s.extrapolation) for s in t.strips]) for t in rig.animation_data.nla_tracks][:3])
for pb in list(rig.pose.bones)[:8]:
    print(pb.name, tuple(round(x, 3) for x in pb.rotation_quaternion), tuple(round(x, 3) for x in pb.location))
for o in O:
    if o.type == 'MESH':
        print(o.name, "hide_render", o.hide_render, "viewport", o.hide_viewport, "mods", [(m.type, m.object.name if getattr(m, 'object', None) else None) for m in o.modifiers], "parent", o.parent.name if o.parent else None)

import bpy
b = bpy.data.objects['Human']; rig = bpy.data.objects['Human.rig']
print("rig loc", rig.location, rig.rotation_euler, rig.scale, rig.parent, rig.matrix_world.translation)
print("mesh matrix", b.matrix_world.translation, b.parent_type)
zs = [v.co.z for v in b.data.vertices]
body_g = b.vertex_groups['body'].index
zb = [v.co.z for v in b.data.vertices if any(g.group==body_g for g in v.groups)]
print("z all", min(zs), max(zs), "z body", min(zb), max(zb))
ys = [v.co.y for v in b.data.vertices if any(g.group==body_g for g in v.groups)]
xs = [v.co.x for v in b.data.vertices if any(g.group==body_g for g in v.groups)]
print("body x", min(xs), max(xs), "y", min(ys), max(ys))
print([ (m.type, m.name) for m in b.modifiers])
print(bpy.context.scene.unit_settings.scale_length)

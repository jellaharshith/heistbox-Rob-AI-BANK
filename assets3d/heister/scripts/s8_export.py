"""Stage 8: final .blend + GLB export. s7 -> CHAR_Heister.blend + export/CHAR_Heister.glb"""
import bpy, os, sys, json
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s7.blend"))
O = bpy.data.objects; sc = bpy.context.scene
props = bpy.ops.export_scene.gltf.get_rna_type().properties
names = [p.identifier for p in props]
def enum(p):
    return [i.identifier for i in props[p].enum_items]
print("anim modes", enum("export_animation_mode"))
kw = dict(filepath=os.path.join(H, "export", "CHAR_Heister.glb"), export_format='GLB', use_selection=False,
          export_cameras=False, export_lights=False, export_apply=False, export_morph=True, export_morph_normal=True,
          export_skins=True, export_def_bones=True, export_animations=True, export_animation_mode='NLA_TRACKS',
          export_extras=True, export_yup=True, export_image_format='AUTO', export_force_sampling=True, export_frame_range=False)
kw = {k: v for k, v in kw.items() if k in names}
missing = [k for k in ("export_nla_strips", "export_optimize_animation_size") if k in names]
print("extra opts available", missing)
if "export_optimize_animation_size" in names:
    kw["export_optimize_animation_size"] = False
if "export_anim_slide_to_zero" in names:
    kw["export_anim_slide_to_zero"] = False
# clear any active actions so NLA tracks drive export
for o in O:
    for idb in (o, getattr(o.data, "shape_keys", None) if o.type == 'MESH' else None):
        if idb is not None and idb.animation_data:
            idb.animation_data.action = None
for o in O:
    if o.type in ('MESH', 'ARMATURE'):
        o.hide_set(False); o.hide_render = False; o.hide_viewport = False
sc.render.fps = 30
for o in O:
    if o.type == "ARMATURE":
        for pb in o.pose.bones:
            pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
for k in bpy.data.shape_keys:
    for kb in k.key_blocks:
        kb.value = 0.0
bpy.ops.export_scene.gltf(**kw)
print("exported", os.path.getsize(kw["filepath"]))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "CHAR_Heister.blend"))


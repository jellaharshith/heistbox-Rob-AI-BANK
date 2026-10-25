import bpy, os
ROOT=r"C:\Users\Shaik\Downloads\heistbox\assets3d\customer"
O=bpy.data.objects
print("ENUM", [i.identifier for i in bpy.ops.export_scene.gltf.get_rna_type().properties["export_animation_mode"].enum_items])
for n in ("CHAR_Customer_LOD1","CHAR_Customer_LOD2"):
    O[n].hide_viewport=False; O[n].hide_set(False)
for o in bpy.context.scene.objects: o.select_set(False)
for n in ("CHAR_Customer","CHAR_Customer_LOD0","CHAR_Customer_LOD1","CHAR_Customer_LOD2","PROP_Phone"):
    O[n].select_set(True)
for ad in [O["CHAR_Customer"].animation_data]:
    for t in ad.nla_tracks: t.mute=False
bpy.context.view_layer.objects.active=O["CHAR_Customer"]
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT,"export","CHAR_Customer.glb"), export_format='GLB', use_selection=True,
    export_yup=True, export_apply=False, export_animations=True, export_animation_mode='NLA_TRACKS', export_morph=True,
    export_skins=True, export_def_bones=True, export_cameras=False, export_lights=False,
    export_force_sampling=True, export_optimize_animation_size=True, export_image_format='AUTO')
print("EXPORTED")



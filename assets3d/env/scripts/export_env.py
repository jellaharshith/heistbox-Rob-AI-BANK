import bpy
ROOT = r"C:\Users\Shaik\Downloads\heistbox\assets3d\env"
bpy.ops.wm.open_mainfile(filepath=ROOT + r"\ENV_BankHall.blend")
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in ('MESH', 'EMPTY'):
        o.select_set(True)
bpy.context.view_layer.objects.active = next(o for o in bpy.data.objects if o.type == 'MESH')
bpy.ops.export_scene.gltf(filepath=ROOT + r"\export\ENV_Bank.glb", export_format='GLB', use_selection=True,
    export_cameras=False, export_lights=False, export_yup=True, export_apply=True, export_animations=False,
    export_image_format='AUTO', export_texcoords=True, export_normals=True, export_tangents=False)
print("EXPORTED")

import bpy, os, numpy as np
from mathutils import Vector
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "CHAR_Heister.blend"))
O = bpy.data.objects; sc = bpy.context.scene
for o in O:
    if o.type == 'MESH' and ("LOD1" in o.name or "LOD2" in o.name):
        o.hide_render = True
    ad = o.animation_data
    if ad:
        for t in ad.nla_tracks:
            t.mute = True
for k in bpy.data.shape_keys:
    if k.animation_data:
        for t in k.animation_data.nla_tracks:
            t.mute = True
rig = O["CHAR_Heister"]
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
S = 420
sc.render.resolution_x = S; sc.render.resolution_y = S
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.25, 0.27, 0.3)
cd = bpy.data.cameras.new("c"); cd.type = 'ORTHO'; cd.ortho_scale = 0.3
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
d = Vector((0.35, -1, 0.05)).normalized()
cam.location = Vector((0, -0.12, 1.69)) + d * 5; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
# hide the mask & beanie so the mouth is visible
O["CHAR_Heister_Mask_LOD0"].hide_render = os.environ.get("HIDE_MASK", "1") == "1"
poses = [{}, {"jawOpen": 1.0}, {"viseme_O": 1.0}, {"mouthSmile": 1.0, "browUp": 1.0}, {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0}, {"viseme_FF": 1.0, "browDown": 1.0}]
tiles = []
for p in poses:
    for ob in (O["CHAR_Heister_Body_LOD0"], O["CHAR_Heister_Mask_LOD0"]):
        for kb in ob.data.shape_keys.key_blocks:
            kb.value = p.get(kb.name, 0.0)
    bpy.context.view_layer.update()
    fp = os.path.join(H, "shots", "_k.png"); sc.render.filepath = fp
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(fp); tiles.append(np.array(im.pixels[:], np.float32).reshape(S, S, 4)); bpy.data.images.remove(im)
sheet = np.concatenate([np.concatenate(tiles[:3], 1), np.concatenate(tiles[3:], 1)], 0)
im = bpy.data.images.new("s", S * 3, S * 2, alpha=True); im.pixels.foreach_set(sheet.ravel())
im.filepath_raw = os.path.join(H, "shots", "keys.png"); im.file_format = 'PNG'; im.save()
print("WROTE")

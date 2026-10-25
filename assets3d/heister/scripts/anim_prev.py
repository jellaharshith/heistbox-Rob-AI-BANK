import bpy, os, sys, math, numpy as np
from mathutils import Vector
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
env = os.environ
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, env.get("PREV_IN", "heister_s6.blend")))
O = bpy.data.objects; sc = bpy.context.scene
rig = O["CHAR_Heister"]
sc.render.engine = 'BLENDER_WORKBENCH'
size = int(env.get("R_SIZE", "420"))
sc.render.resolution_x = size; sc.render.resolution_y = size
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.show_object_outline = False
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.25, 0.27, 0.3)
cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = float(env.get("R_EXT", "2.3"))
cam = bpy.data.objects.new("c", cam_d); sc.collection.objects.link(cam); sc.camera = cam
view = env.get("R_VIEW", "three")
dirs = {"front": (0, -1, 0), "three": (0.75, -0.65, 0.15), "side": (1, 0, 0)}
d = Vector(dirs[view]).normalized()
spec = env.get("PREV", "Walk:1,9,17,25").split(";")
tiles = []
ad = rig.animation_data
for item in spec:
    clip, frs = item.split(":")
    act = bpy.data.actions["Heister_" + clip]
    ad.action = act
    try:
        ad.action_slot = act.slots[0]
    except Exception as e:
        print("slot", e)
    for fr in [int(x) for x in frs.split(",")]:
        sc.frame_set(fr)
        bpy.context.view_layer.update()
        ctr = Vector((0, -0.05, 0.95)) + Vector((0, 0, 0.0))
        cam.location = ctr + d * 6
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(H, "shots", "_t.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(p)
        tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4))
        bpy.data.images.remove(img)
n = len(tiles); cols = min(n, int(env.get("COLS", "6"))); rows = (n + cols - 1) // cols
sheet = np.ones((rows * size, cols * size, 4), np.float32)
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    sheet[(rows - 1 - r) * size:(rows - r) * size, c * size:(c + 1) * size] = t
im = bpy.data.images.new("sheet", cols * size, rows * size, alpha=True)
im.pixels.foreach_set(sheet.ravel())
out = env.get("R_OUT", os.path.join(H, "shots", "anim.png"))
im.filepath_raw = out; im.file_format = 'PNG'; im.save()
print("WROTE", out)

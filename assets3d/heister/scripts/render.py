"""Workbench contact-sheet renderer. env: R_OUT (png path), R_HIDE (comma names to hide), R_VIEWS (e.g. front,side,back,three),
R_COLOR (MATERIAL|TEXTURE|OBJECT|SINGLE), R_FOCUS ('full'|'head'|'hand'|'feet'|'x,y,z,size'), R_SIZE (px per tile), R_WIRE (1)"""
import bpy, os, math, sys
import numpy as np
from mathutils import Vector
env = os.environ
out = env.get("R_OUT", r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister\shots\sheet.png")
hide = [n for n in env.get("R_HIDE", "").split(",") if n]
views = env.get("R_VIEWS", "front,side,back,three").split(",")
size = int(env.get("R_SIZE", "512"))
focus = env.get("R_FOCUS", "full")
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x = size; sc.render.resolution_y = size
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = env.get("R_COLOR", "MATERIAL")
sc.display.shading.show_cavity = False
sc.display.shading.show_object_outline = False
if env.get("R_WIRE") == "1":
    sc.display.shading.show_wireframes = True if hasattr(sc.display.shading, "show_wireframes") else False
try:
    sc.view_settings.view_transform = 'Standard'
except Exception:
    pass
for o in bpy.data.objects:
    if o.name in hide or any(h.endswith('*') and o.name.startswith(h[:-1]) for h in hide):
        o.hide_render = True; o.hide_viewport = True
PAL = {"Skin": (0.8, 0.55, 0.45, 1), "Hoodie": (0.15, 0.2, 0.35, 1), "Pants": (0.35, 0.4, 0.2, 1), "Shoes": (0.9, 0.9, 0.9, 1),
       "Gloves": (0.05, 0.05, 0.05, 1), "Beanie": (0.7, 0.1, 0.1, 1), "Mask": (0.1, 0.1, 0.1, 1), "Duffel": (0.6, 0.45, 0.1, 1),
       "Eye": (1, 1, 1, 1)}
for o in bpy.data.objects:
    for k, c in PAL.items():
        if o.name.startswith(k):
            o.color = c
for o in bpy.data.objects:
    if o.type == "MESH":
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
if env.get("R_NOMOD") == "1":
    for o in bpy.data.objects:
        for m in o.modifiers:
            m.show_viewport = False; m.show_render = False
if env.get("R_REST", "1") == "1":
    for o in list(bpy.data.objects) + list(bpy.data.shape_keys):
        ad = o.animation_data
        if ad:
            for tr in ad.nla_tracks:
                tr.mute = True
    for o in bpy.data.objects:
        if o.type == 'ARMATURE':
            for pb in o.pose.bones:
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    for k in bpy.data.shape_keys:
        for kb in k.key_blocks:
            kb.value = 0.0
    bpy.context.view_layer.update()
# world
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.25, 0.27, 0.3)
vis = [o for o in bpy.data.objects if o.type == 'MESH' and not o.hide_render]
if focus == 'full':
    pts = [o.matrix_world @ Vector(c) for o in vis for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (mn + mx) / 2; ext = max((mx - mn).z * 1.1, 0.5)
else:
    v = [float(x) for x in focus.split(",")]
    ctr = Vector(v[:3]); ext = v[3]
cam_d = bpy.data.cameras.new("c"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ext
cam = bpy.data.objects.new("c", cam_d); sc.collection.objects.link(cam); sc.camera = cam
dirs = {"front": (0, -1, 0), "back": (0, 1, 0), "side": (1, 0, 0), "left": (-1, 0, 0), "three": (0.7, -0.7, 0.35), "three2": (-0.7, -0.7, 0.35),
        "top": (0, 0, 1), "threeb": (0.7, 0.7, 0.35)}
tiles = []
for vname in views:
    d = Vector(dirs[vname]).normalized()
    cam.location = ctr + d * 6
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    p = out.replace(".png", f"_{vname}.png")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(p)
    a = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)
    tiles.append(a)
    bpy.data.images.remove(img)
    os.remove(p)
n = len(tiles)
cols = min(n, 4); rows = (n + cols - 1) // cols
sheet = np.ones((rows * size, cols * size, 4), dtype=np.float32)
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    sheet[(rows - 1 - r) * size:(rows - r) * size, c * size:(c + 1) * size] = t
im = bpy.data.images.new("sheet", cols * size, rows * size, alpha=True)
im.pixels = sheet.ravel().tolist()
im.filepath_raw = out; im.file_format = 'PNG'; im.save()
print("WROTE", out)


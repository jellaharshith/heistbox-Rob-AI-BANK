# usage: blender -b file.blend -P rend.py -- out_prefix [hideRegex] [frame] [mode]
import bpy, sys, math, mathutils, re
args = sys.argv[sys.argv.index("--")+1:]
out = args[0]; hide = args[1] if len(args)>1 and args[1]!="-" else None
frame = int(args[2]) if len(args)>2 else None
mode = args[3] if len(args)>3 else "WORKBENCH"
sc = bpy.context.scene
import os
clip = os.environ.get("CLIP")
if clip:
    for o in sc.objects:
        for ad in [o.animation_data, (o.data.shape_keys.animation_data if o.type=='MESH' and o.data.shape_keys else None)]:
            if ad:
                for tr in ad.nla_tracks: tr.mute = (tr.name != clip)
if frame is not None: sc.frame_set(frame)
if hide:
    for o in sc.objects:
        if re.search(hide, o.name): o.hide_render = True; o.hide_set(True)
sc.render.resolution_x = 640; sc.render.resolution_y = 800
sc.render.image_settings.file_format = 'PNG'
try: sc.render.engine = 'BLENDER_WORKBENCH'
except Exception: sc.render.engine='BLENDER_WORKBENCH'
if mode=="TEX":
    sc.display.shading.light='STUDIO'; sc.display.shading.color_type='TEXTURE'
else:
    sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'
sc.display.shading.show_cavity=False
if sc.world is None: sc.world = bpy.data.worlds.new("w")
sc.world.color=(0.35,0.37,0.4)
sc.view_settings.view_transform='Standard'
cam = bpy.data.objects.new("rc", bpy.data.cameras.new("rc")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'
meshes=[o for o in sc.objects if o.type=='MESH' and not o.hide_render and o.visible_get()]
mn=mathutils.Vector((1e9,)*3); mx=mathutils.Vector((-1e9,)*3)
for o in meshes:
    for c in o.bound_box:
        w=o.matrix_world@mathutils.Vector(c)
        for i in range(3): mn[i]=min(mn[i],w[i]); mx[i]=max(mx[i],w[i])
ctr=(mn+mx)/2; h=(mx.z-mn.z)
views = {"front":(0,-1,0),"side":(1,0,0),"back":(0,1,0),"34":(0.7,-0.7,0)}
sel = args[4].split(",") if len(args)>4 else ["front","side"]
zoom = {"face":1}
for name in sel:
    if name.startswith("face"):
        d = mathutils.Vector(views["front"] if name=="face" else views["34"]).normalized()
        c = mathutils.Vector((ctr.x, ctr.y, mx.z-0.13)); cam.data.ortho_scale=0.45
    elif name=="hand":
        d = mathutils.Vector(views["front"]); c=ctr; cam.data.ortho_scale=h
    else:
        d = mathutils.Vector(views[name]).normalized(); c=ctr; cam.data.ortho_scale=h*1.08
    cam.location = c + d*6
    cam.rotation_euler = (-d).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath = f"{out}_{name}.png"
    bpy.ops.render.render(write_still=True)
print("RENDERED")


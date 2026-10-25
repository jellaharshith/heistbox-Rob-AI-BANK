import bpy, sys, math
from mathutils import Vector
# usage: blender -b <file.blend or none> -P render_shots.py -- <outprefix> [glb]
argv = sys.argv[sys.argv.index("--") + 1:]
out = argv[0]
SH = r"C:\Users\Shaik\Downloads\heistbox\assets3d\mech\shots\\"
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print(e)
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if False else sc.render.engine
sc.render.resolution_x = 900; sc.render.resolution_y = 600
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (0.05, 0.055, 0.07, 1); bg.inputs[1].default_value = 1.0

def light(name, loc, energy, color=(1, 1, 1), size=3):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.size = size; d.color = color
    o = bpy.data.objects.new(name, d); o.location = loc; sc.collection.objects.link(o)
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o

def cam(loc, target, lens=50):
    cd = bpy.data.cameras.new("C"); cd.lens = lens
    co = bpy.data.objects.new("C", cd); co.location = loc; sc.collection.objects.link(co)
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    return co

def shot(name, loc, target, lens=50, frame=1):
    sc.frame_set(frame)
    cam(loc, target, lens)
    sc.render.filepath = SH + name
    bpy.ops.render.render(write_still=True)

ob = bpy.data.objects
def set_clip(obj, clip, frame):
    """evaluate clip at frame by muting other tracks"""
    for t in obj.animation_data.nla_tracks:
        t.mute = (t.name != clip)

for o in ob:
    if o.animation_data: o.animation_data_clear()
    if o.name == "CHAR_Sentinel": o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0); o.scale = (1, 1, 1)
    if o.name.endswith("_Door"): o.rotation_euler = (0, 0, 0)
light("K",(-3, -4, 5), 800, (1, 0.95, 0.9)); light("F", (4, -3, 2), 400, (0.6, 0.8, 1.0)); light("B", (0, 4, 4), 300)

if argv[1] == "doors":
    # lay doors out in a row for review
    for k, x in (("L", -2.6), ("M", 0.0), ("R", 2.6)):
        d = ob[f"VAULT_{k}_Door"]
        d.location = (x - 1.1, 0, 1.1)
    for n in ("PROP_Shredder", "FX_Laser", "FX_LockdownStrip_L", "FX_LockdownStrip_M", "FX_LockdownStrip_R"):
        ob[n].hide_render = True
    shot(out + "_doors_front", (0, -7.5, 1.4), (0, 0, 1.1), 40)
    for k in "LMR":
        d = ob[f"VAULT_{k}_Door"]
        bpy.ops.object.select_all(action='DESELECT')
        for o in ob:
            if o.name.startswith("VAULT_") and o.name != d.name: o.hide_render = True
        c = d.location + Vector((1.1, 0, 0))
        shot(f"{out}_door{k}", (c.x - 1.2, -3.0, c.z + 0.3), (c.x, 0, c.z), 50)
        for o in ob: o.hide_render = False
        for n in ("PROP_Shredder", "FX_Laser", "FX_LockdownStrip_L", "FX_LockdownStrip_M", "FX_LockdownStrip_R"):
            ob[n].hide_render = True
    # open pose
    for k in "LMR":
        d = ob[f"VAULT_{k}_Door"]; d.rotation_euler = (0, 0, math.radians(-100 if k != "M" else -50))
    shot(out + "_doors_open", (0, -8.5, 3.5), (0, 0, 1.1), 40)
elif argv[1] == "sentinel":
    for o in ob:
        if o.name != "CHAR_Sentinel" and o.type == 'MESH': o.hide_render = True
    shot(out + "_sentinel_front", (0, -2.6, 1.3), (0, 0, 1.0), 50)
    shot(out + "_sentinel_side", (2.4, -1.4, 1.5), (0, 0, 1.0), 50)
elif argv[1] == "props":
    for o in ob:
        if o.name.startswith("VAULT_") or o.name == "CHAR_Sentinel": o.hide_render = True
    ob["PROP_Shredder"].location = (0, 0, 0)
    ob["FX_Laser"].location = (-0.56, 0, 1.5)
    shot(out + "_shredder", (-2.2, -3.0, 1.9), (-0.6, 0, 0.9), 45)

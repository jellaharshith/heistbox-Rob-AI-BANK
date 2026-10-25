import bpy, sys, math
from mathutils import Vector
blend = sys.argv[sys.argv.index("--") + 1]; out = sys.argv[sys.argv.index("--") + 2]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
eng = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next(e for e in eng if 'EEVEE' in e)
sc.render.resolution_x, sc.render.resolution_y = 1400, 600
if sc.world is None: sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
bg = next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (0.3, 0.32, 0.36, 1); bg.inputs[1].default_value = 1
names = ["PROP_CashSmall", "PROP_CashHeist", "PROP_Megaphone", "PROP_WantedPoster", "PROP_Terminal"] + [o.name for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("PROP_")]
x = -2.0
for n in names:
    o = bpy.data.objects.get(n)
    if o and o.name in [c.name for c in sc.collection.all_objects]:
        o.location.x = x
        if n == "PROP_CashSmall": o.location.z = 0.0
        x += 0.8
ld = bpy.data.lights.new("S", 'SUN'); ld.energy = 3
lo = bpy.data.objects.new("S", ld); lo.rotation_euler = (math.radians(50), 0, math.radians(-30)); sc.collection.objects.link(lo)
cd = bpy.data.cameras.new("C"); cd.lens = 45
co = bpy.data.objects.new("C", cd); sc.collection.objects.link(co); sc.camera = co
mode = sys.argv[sys.argv.index('--') + 3] if len(sys.argv) > sys.argv.index('--') + 3 else 'front'
cd.lens = 32
if mode == 'front':
    co.location = (-0.4, -5.0, 0.15); co.rotation_euler = (math.radians(90), 0, 0)
else:
    tgt = Vector((-0.4, 0, 0.15)); co.location = (2.5, -4.2, 1.6)
    co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True)



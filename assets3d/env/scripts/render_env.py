import bpy, sys, math
from mathutils import Vector
blend = sys.argv[sys.argv.index("--") + 1]
out = sys.argv[sys.argv.index("--") + 2]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
eng = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next(e for e in eng if 'EEVEE' in e)
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.view_settings.view_transform = 'Standard' if 'Standard' in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else sc.view_settings.view_transform
if sc.world is None: sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
bg = next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0.05, 0.06, 0.09, 1); bg.inputs[1].default_value = 0.6
for i, (x, y) in enumerate([(-4, -3), (4, -3), (-4, 3), (4, 3), (0, 0)]):
    ld = bpy.data.lights.new(f"PL{i}", 'POINT'); ld.energy = 900; ld.shadow_soft_size = 0.3
    ld.color = (1, 0.85, 0.65)
    o = bpy.data.objects.new(f"PL{i}", ld); o.location = (x, y, 4.0); sc.collection.objects.link(o)
cd = bpy.data.cameras.new("C"); cd.lens = 24
co = bpy.data.objects.new("C", cd); sc.collection.objects.link(co); sc.camera = co
shots = {"player": ((0, -5.6, 1.7), (0, 4, 1.4)), "overview": ((7.5, -5.5, 3.6), (-1, 2, 1.0)),
         "counter": ((-3, -2.6, 1.6), (1, 1, 1.2)), "alcove": ((0, 1.5, 1.7), (0, 7.5, 1.6)),
         "top": ((0, -0.1, 12), (0, 0, 0))}
for n, (p, t) in shots.items():
    co.location = p
    co.rotation_euler = (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
    if n == "top": cd.lens = 18
    sc.render.filepath = f"{out}\\{n}.png"
    bpy.ops.render.render(write_still=True)

import bpy, os, sys, numpy as np
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
from rast import raster
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s5hi.blend"))
O = bpy.data.objects; sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
body = O["CHAR_Heister_Body"]
mode = os.environ.get("MODE", "copy")
if mode == "copy":
    hi = body.copy(); hi.data = body.data.copy(); sc.collection.objects.link(hi)
    hi.modifiers.clear(); hi.shape_key_clear() if hi.data.shape_keys else None
    hi.parent = None
    hi.name = "HI_test"
else:
    hi = O["HI_all"]
for n in ("Body_hi", "HI_duffel", "CHAR_Heister_Mask", "CHAR_Heister_Duffel", "CHAR_Heister_EyeL", "CHAR_Heister_EyeR"):
    O[n].hide_render = True; O[n].hide_viewport = True
if mode == "copy":
    O["HI_all"].hide_render = True; O["HI_all"].hide_viewport = True
im = bpy.data.images.new("n", 1024, 1024)
im.colorspace_settings.name = 'Non-Color'
im.pixels.foreach_set(np.tile(np.array([0.5, 0.5, 1, 1], np.float32), 1024 * 1024))
body.data.materials.clear()
mat = bpy.data.materials.new("m"); mat.use_nodes = True
t = mat.node_tree.nodes.new("ShaderNodeTexImage"); t.image = im; mat.node_tree.nodes.active = t
body.data.materials.append(mat)
bk = sc.render.bake; bk.use_selected_to_active = True; bk.cage_extrusion = float(os.environ.get("EXT", "0.02")); bk.max_ray_distance = float(os.environ.get("MAXD", "0.05"))
bk.margin = 4; bk.use_clear = False
bpy.ops.object.select_all(action='DESELECT')
hi.select_set(True); body.select_set(True); bpy.context.view_layer.objects.active = body
bpy.ops.object.bake(type='NORMAL')
nrm = np.array(im.pixels[:], np.float32).reshape(1024, 1024, 4)
R = raster([body], 1024)
bad = (nrm[..., 2] < 0.3) & R["filled"]
print("MODE", mode, "bad", bad.sum(), "of", R["filled"].sum())

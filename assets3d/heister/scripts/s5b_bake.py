"""Stage 5b: bake tangent normal (hi->lo) and AO onto the atlas. Saves textures/bake_normal.npy, bake_ao.npy"""
import bpy, os, sys, time
import numpy as np
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s5hi.blend"))
O = bpy.data.objects
sc = bpy.context.scene
RES = 1024
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 24
sc.cycles.use_denoising = False
bk = sc.render.bake
bk.margin = 10; bk.margin_type = 'EXTEND'
bk.use_clear = False
los = [O["CHAR_Heister_Body"], O["CHAR_Heister_Mask"], O["CHAR_Heister_Duffel"]]
his = {"CHAR_Heister_Body": O["HI_all"], "CHAR_Heister_Mask": O["HI_all"], "CHAR_Heister_Duffel": O["HI_duffel"]}
if sc.world is None:
    sc.world = bpy.data.worlds.new("w")
sc.world.light_settings.distance = 0.3

def make_img(name, color):
    im = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color'
    px = np.tile(np.array(color, dtype=np.float32), RES * RES)
    im.pixels.foreach_set(px)
    return im

def attach(o, im):
    o.data.materials.clear()
    mat = bpy.data.materials.new("bake_tmp_" + o.name)
    mat.use_nodes = True
    nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = im
    nt.nodes.active = tex
    for n in nt.nodes:
        n.select = (n == tex)
    o.data.materials.append(mat)

def sel(active, others=()):
    bpy.ops.object.select_all(action='DESELECT')
    for x in others:
        x.select_set(True)
    active.select_set(True)
    bpy.context.view_layer.objects.active = active

# hide non-bake stuff
for n in ("Body_hi", "CHAR_Heister_EyeL", "CHAR_Heister_EyeR"):
    O[n].hide_render = True
    O[n].hide_viewport = True
rig = O["CHAR_Heister"]

# ---------------- normal
im_n = make_img("bake_normal", (0.5, 0.5, 1.0, 1.0))
for lo in los:
    attach(lo, im_n)
O["HI_all"].hide_render = False; O["HI_duffel"].hide_render = False
bk.use_selected_to_active = True
bk.cage_extrusion = 0.02
bk.max_ray_distance = 0.05
bk.normal_space = 'TANGENT'
for lo in los:
    t0 = time.time()
    sel(lo, [his[lo.name]])
    for h in (O["HI_all"], O["HI_duffel"]):
        h.hide_viewport = False
    bpy.ops.object.bake(type='NORMAL')
    print("normal baked", lo.name, round(time.time() - t0, 1))
np.save(os.path.join(H, "textures", "bake_normal.npy"), np.array(im_n.pixels[:], dtype=np.float32).reshape(RES, RES, 4))

# ---------------- AO (lo scene only)
O["HI_all"].hide_render = True; O["HI_duffel"].hide_render = True
O["HI_all"].hide_viewport = True; O["HI_duffel"].hide_viewport = True
im_a = make_img("bake_ao", (1, 1, 1, 1))
for lo in los:
    attach(lo, im_a)
bk.use_selected_to_active = False
sc.cycles.samples = 48
for lo in los:
    t0 = time.time()
    sel(lo)
    bpy.ops.object.bake(type='AO')
    print("ao baked", lo.name, round(time.time() - t0, 1))
np.save(os.path.join(H, "textures", "bake_ao.npy"), np.array(im_a.pixels[:], dtype=np.float32).reshape(RES, RES, 4))
print("done")


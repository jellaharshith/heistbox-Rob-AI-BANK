"""Stage 4: bake BaseColor / Roughness / Normal / AO for the main pieces, paint hair/eyes/lashes/hardware, write 2048 PNGs."""
import sys, time
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina/scripts")
import bpy, numpy as np
import bake_utils as bk, mesh_utils as mu, tlib, tmat

ROOT = r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina"
S = 2048
bpy.ops.wm.open_mainfile(filepath=ROOT + "/scripts/_stage3.blend")
t0 = time.time()
PIECES = ["Skin", "Blazer", "Blouse", "Trousers", "Shoes"]
HI = {n: bpy.data.objects["Tina_%sHi" % n] for n in PIECES}
LO = {n: bpy.data.objects["Tina_%s_L0" % n] for n in PIECES}
EX = [bpy.data.objects[n] for n in ("Tina_HairAll_L0", "Tina_EyesAll_L0", "Tina_LashesAll_L0", "Tina_Headset_L0")]
body = bpy.data.objects["Tina_BodyHi"]
body.hide_render = True; body.hide_viewport = True

mats = tmat.build_hi_materials()
for n in PIECES:
    HI[n].data.materials.clear()
    HI[n].data.materials.append(mats[n])

bk.setup_cycles(samples=24)
world = bpy.data.worlds.new("W"); bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (1, 1, 1, 1)
try:
    world.light_settings.distance = 0.12
except Exception as e:
    print("ao dist", e)

img_a = bk.new_image("Tina_BaseColor_raw", S, fill=(0.4, 0.25, 0.2, 1))
img_r = bk.new_image("Tina_Rough_raw", S, fill=(0.6, 0.6, 0.6, 1))
img_n = bk.new_image("Tina_Normal_raw", S, fill=(0.5, 0.5, 1.0, 1))
img_ao = bk.new_image("Tina_AO_raw", S, fill=(1, 1, 1, 1))
tgt = bk.make_target_material("BAKE_TARGET")

EXTR = {"Skin": (0.012, 0.03), "Blazer": (0.012, 0.03), "Blouse": (0.01, 0.025), "Trousers": (0.012, 0.03), "Shoes": (0.01, 0.025)}
for n in PIECES:
    ex, ray = EXTR[n]
    for typ, img, pf in (("DIFFUSE", img_a, {'COLOR'}), ("ROUGHNESS", img_r, None), ("NORMAL", img_n, None)):
        t1 = time.time()
        r = bk.bake_pass(LO[n], [HI[n]], img, tgt, typ, selected_to_active=True, extrusion=ex, max_ray=ray, margin=10, pass_filter=pf)
        print("baked", n, typ, r, "%.1fs" % (time.time() - t1))

# AO: self-bake of the assembled low-poly character (hair/headset are occluders)
for o in list(HI.values()):
    o.hide_render = True
    o.hide_viewport = True
for n in PIECES:
    LO[n].data.materials.clear(); LO[n].data.materials.append(tgt)
tgt.node_tree.nodes["BAKE_IMG"].image = img_ao
tgt.node_tree.nodes.active = tgt.node_tree.nodes["BAKE_IMG"]
for o in bpy.context.view_layer.objects:
    o.select_set(False)
for n in PIECES:
    LO[n].select_set(True)
bpy.context.view_layer.objects.active = LO["Skin"]
bpy.context.scene.cycles.samples = 64
r = bpy.ops.object.bake(type='AO', margin=10, margin_type='EXTEND', use_selected_to_active=False, target='IMAGE_TEXTURES', use_clear=False)
print("AO", r, "%.1fs" % (time.time() - t0))

alb = bk.image_to_array(img_a)
rough = bk.image_to_array(img_r)
nrm = bk.image_to_array(img_n)
ao = bk.image_to_array(img_ao)
print("stats albedo", alb[..., :3].mean(), "rough", rough[..., 0].mean(), "nrm", nrm[..., :3].mean(axis=(0, 1)), "ao", ao[..., 0].mean())

# compose
base = np.ones((S, S, 4), dtype=np.float32)
base[..., :3] = alb[..., :3]
orm = np.ones((S, S, 4), dtype=np.float32)
orm[..., 0] = np.clip(ao[..., 0], 0, 1)
orm[..., 1] = np.clip(rough[..., 0], 0, 1)
orm[..., 2] = 0.0
tmat.paint_hair(base, orm, S, tlib.HAIR)
tmat.paint_lashes(base, orm, S, tlib.LASH)
tmat.paint_eye(base, orm, S, tlib.EYE)
tmat.paint_cells(base, orm, S, tlib.HARD)

import os
os.makedirs(ROOT + "/textures", exist_ok=True)
base_srgb = base.copy()
base_srgb[..., :3] = bk.linear_to_srgb(base[..., :3])
bk.save_png_raw(base_srgb, ROOT + "/textures/Tina_BaseColor.png")
bk.save_png_raw(orm, ROOT + "/textures/Tina_ORM.png")
nrm[..., 3] = 1.0
bk.save_png_raw(nrm, ROOT + "/textures/Tina_Normal.png")
print("textures saved %.1fs" % (time.time() - t0))


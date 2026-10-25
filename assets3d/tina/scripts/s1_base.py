"""Stage 1: MPFB female base + Mixamo rig + the 21 required face shape keys. -> tina/tina_base.blend"""
import sys, os
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import mpfb_base as mb, preview_utils as pv

ROOT = r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina"
body, arm = mb.build_human(gender=0.0, age=0.54, muscle=0.4, weight=0.42, proportions=0.55, height=0.52,
                           cupsize=0.5, firmness=0.6, race=(0.15, 0.85, 0.0))
body.name = "Tina_BodyHi"
arm.name = "Tina_Armature"

U = "eye-left-closure eye-right-closure eyebrows-left-down eyebrows-right-down eyebrows-left-up eyebrows-right-up " \
    "eyebrows-left-inner-up eyebrows-right-inner-up mouth-compression mouth-corner-puller mouth-open mouth-parling " \
    "mouth-part-later mouth-protusion mouth-pursing mouth-retraction mouth-upward-retraction mouth-depression " \
    "mouth-elevation".split()
units = mb.load_unit_targets(body, U)

# name -> {unit: weight}
RECIPES = {
    "viseme_sil": {"mouth-compression": 0.12},
    "viseme_PP": {"mouth-compression": 1.0},
    "viseme_FF": {"mouth-upward-retraction": 0.8, "mouth-open": 0.12},
    "viseme_TH": {"mouth-open": 0.3, "mouth-protusion": 0.25},
    "viseme_DD": {"mouth-open": 0.3, "mouth-retraction": 0.3},
    "viseme_kk": {"mouth-open": 0.38, "mouth-retraction": 0.15},
    "viseme_CH": {"mouth-pursing": 0.5, "mouth-open": 0.2, "mouth-protusion": 0.4},
    "viseme_SS": {"mouth-retraction": 0.6, "mouth-open": 0.1, "mouth-corner-puller": 0.2},
    "viseme_nn": {"mouth-open": 0.15, "mouth-retraction": 0.3},
    "viseme_RR": {"mouth-pursing": 0.45, "mouth-open": 0.25},
    "viseme_aa": {"mouth-open": 1.0},
    "viseme_E": {"mouth-open": 0.35, "mouth-retraction": 0.5, "mouth-corner-puller": 0.2},
    "viseme_I": {"mouth-open": 0.2, "mouth-retraction": 0.6, "mouth-corner-puller": 0.3},
    "viseme_O": {"mouth-open": 0.5, "mouth-pursing": 0.8, "mouth-protusion": 0.4},
    "viseme_U": {"mouth-pursing": 1.0, "mouth-open": 0.12, "mouth-protusion": 0.5},
    "eyeBlinkLeft": {"eye-left-closure": 1.0},
    "eyeBlinkRight": {"eye-right-closure": 1.0},
    "mouthSmile": {"mouth-corner-puller": 1.0, "mouth-retraction": 0.15},
    "browUp": {"eyebrows-left-up": 1.0, "eyebrows-right-up": 1.0, "eyebrows-left-inner-up": 0.4, "eyebrows-right-inner-up": 0.4},
    "browDown": {"eyebrows-left-down": 1.0, "eyebrows-right-down": 1.0},
    "jawOpen": {"mouth-open": 1.0, "mouth-parling": 0.3},
}
final = {}
for name, rec in RECIPES.items():
    for k in units.values():
        k.value = 0.0
    for u, w in rec.items():
        units[u].value = w
    sk = body.shape_key_add(name=name, from_mix=True)
    sk.value = 0.0
    final[name] = sk
for k in units.values():
    body.shape_key_remove(k)
body.active_shape_key_index = 0
print("SHAPEKEYS", [k.name for k in body.data.shape_keys.key_blocks])

os.makedirs(ROOT + "/shots/sk", exist_ok=True)
hz = max(v.co.z for v in body.data.vertices)
for o in bpy.data.objects:
    if o is not body: o.hide_render = True
paths = []
for n, k in final.items():
    for kk in final.values(): kk.value = 0
    k.value = 1.0
    p = f"{ROOT}/shots/sk/{n}.png"
    pv.shot(p, target=(0, 0, hz - 0.1), eye=(0.0, -0.8, hz - 0.1), res=(300, 300), lens=85, textured=False)
    paths.append(p)
for kk in final.values(): kk.value = 0
pv.montage(paths, 7, ROOT + "/shots/shapekeys.png")
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/scripts/_stage1.blend")

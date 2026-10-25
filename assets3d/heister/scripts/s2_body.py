"""Stage 2: MPFB base (macro-baked), helper geometry removed, face shape keys composed, rig lifted to ground.
Output: heister_s2.blend with objects Body_hi (full res, shape keys) and Rig."""
import bpy, os, sys, gzip, bmesh
from mathutils import Vector
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.locationservice import LocationService

m = TargetService.get_default_macro_info_dict()
m.update(gender=1.0, muscle=0.7, weight=0.5, proportions=0.6, height=0.54, age=0.5)
m["race"] = {"asian": 0.1, "caucasian": 0.6, "african": 0.3}
base = HumanService.create_human(mask_helpers=False, detailed_helpers=False, extra_vertex_groups=True,
                                 feet_on_ground=False, scale=0.1, macro_detail_dict=m)
rig = HumanService.add_builtin_rig(base, "game_engine", import_weights=True)

# bake macro targets into the mesh
mix = base.shape_key_add(name="mix", from_mix=True)
coords = [v.co.copy() for v in mix.data]
base.shape_key_clear()
for i, v in enumerate(base.data.vertices):
    v.co = coords[i]
base.data.update()

# remove helper geometry (keep only 'body' group verts)
bg = base.vertex_groups['body'].index
bm = bmesh.new(); bm.from_mesh(base.data)
dl = bm.verts.layers.deform.active
kill = [v for v in bm.verts if not (bg in v[dl] and v[dl][bg] > 0.5)]
bmesh.ops.delete(bm, geom=kill, context='VERTS')
bm.to_mesh(base.data); bm.free()
for g in ['HelperGeometry', 'JointCubes', 'Left', 'Mid', 'Right', 'nippleTip', 'nipple', 'genitals', 'body']:
    if g in base.vertex_groups:
        base.vertex_groups.remove(base.vertex_groups[g])
print("body verts", len(base.data.vertices), "tris", sum(len(p.vertices) - 2 for p in base.data.polygons))

# lift to ground (rig + mesh), rig was fit at centred position
zmin = min(v.co.z for v in base.data.vertices)
d = -zmin
for v in base.data.vertices:
    v.co.z += d
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for eb in rig.data.edit_bones:
    eb.head.z += d; eb.tail.z += d
bpy.ops.object.mode_set(mode='OBJECT')
base.parent = None
base.modifiers.clear()
print("height", max(v.co.z for v in base.data.vertices))

# ---- face shape keys composed from MakeHuman expression units (caucasian set)
UD = os.path.join(LocationService.get_mpfb_data("targets"), "expression", "units", "caucasian")
base.shape_key_add(name="Basis")
unit_keys = {}
for fn in sorted(os.listdir(UD)):
    n = fn.replace(".target.gz", "")
    sk = TargetService.load_target(base, os.path.join(UD, fn), weight=0.0, name="u_" + n)
    unit_keys[n] = sk
print("units", list(unit_keys))
basis = base.data.shape_keys.key_blocks["Basis"]
bco = [v.co.copy() for v in basis.data]
delta = {n: [(sk.data[i].co - bco[i]) for i in range(len(bco))] for n, sk in unit_keys.items()}
for n in list(unit_keys):
    base.shape_key_remove(unit_keys[n])
mx = max(delta['mouth-open'][i].length for i in range(len(bco)))
print("mouth-open max delta (m)", mx)

RECIPES = {
    "viseme_sil": {},
    "viseme_PP": {"mouth-compression": 1.0},
    "viseme_FF": {"mouth-upward-retraction": 0.6, "mouth-compression": 0.3},
    "viseme_TH": {"mouth-open": 0.25, "mouth-part-later": 0.4},
    "viseme_DD": {"mouth-open": 0.3, "mouth-retraction": 0.3},
    "viseme_kk": {"mouth-open": 0.35, "mouth-part-later": 0.3},
    "viseme_CH": {"mouth-pursing": 0.6, "mouth-open": 0.25},
    "viseme_SS": {"mouth-retraction": 0.6, "mouth-open": 0.1},
    "viseme_nn": {"mouth-open": 0.2, "mouth-retraction": 0.3},
    "viseme_RR": {"mouth-pursing": 0.5, "mouth-open": 0.2},
    "viseme_aa": {"mouth-open": 1.0},
    "viseme_E": {"mouth-retraction": 0.5, "mouth-open": 0.35},
    "viseme_I": {"mouth-retraction": 0.7, "mouth-open": 0.15},
    "viseme_O": {"mouth-pursing": 0.7, "mouth-open": 0.55},
    "viseme_U": {"mouth-pursing": 1.0, "mouth-open": 0.1},
    "eyeBlinkLeft": {"eye-left-closure": 1.0},
    "eyeBlinkRight": {"eye-right-closure": 1.0},
    "mouthSmile": {"mouth-corner-puller": 1.0, "mouth-elevation": 0.3},
    "browUp": {"eyebrows-left-up": 1.0, "eyebrows-right-up": 1.0},
    "browDown": {"eyebrows-left-down": 1.0, "eyebrows-right-down": 1.0},
    "jawOpen": {"mouth-open": 1.0},
}
import json
json.dump({k: v for k, v in RECIPES.items()}, open(os.path.join(H, "scripts", "recipes.json"), "w"))
# store deltas as a compact npz for later transfer to low-poly parts
import numpy as np
GAIN = {"mouthSmile": 3.0, "viseme_PP": 2.0, "viseme_FF": 2.0, "viseme_U": 2.0, "viseme_SS": 2.0, "viseme_I": 1.6, "viseme_nn": 1.4, "browUp": 1.6, "browDown": 1.4}
keys = {}
for name, rec in RECIPES.items():
    arr = np.zeros((len(bco), 3), dtype=np.float32)
    for un, w in rec.items():
        a = np.array([[x for x in dv] for dv in delta[un]], dtype=np.float32)
        arr += w * a
    keys[name] = arr * GAIN.get(name, 1.0)
np.savez_compressed(os.path.join(H, "scripts", "facekeys_hi.npz"), **keys)
base.shape_key_clear()
pass
base.name = "Body_hi"; base.data.name = "Body_hi"
rig.name = "Rig"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s2.blend"))




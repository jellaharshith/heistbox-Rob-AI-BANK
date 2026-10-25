# Stage 1: MPFB human -> baked macros, mixamo rig, face shape keys (full res). Output: customer/stage1.blend
import bpy, os, math, mathutils
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.locationservice import LocationService
import bl_ext.user_default.mpfb as mp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
macro = TargetService.get_default_macro_info_dict()
macro.update(gender=0.85, age=0.5, muscle=0.5, weight=0.5, height=0.55, proportions=0.5)
macro["race"] = {"asian": 0.2, "caucasian": 0.6, "african": 0.2}
bm = HumanService.create_human(mask_helpers=False, detailed_helpers=True, extra_vertex_groups=True,
                               feet_on_ground=False, scale=0.1, macro_detail_dict=macro)
bm.name = "Body_full"
# bake macro shape keys into mesh
sk = bm.shape_key_add(name="__mix", from_mix=True)
for v, kv in zip(bm.data.vertices, sk.data):
    v.co = kv.co
bm.shape_key_clear()
bm.data.update()
# feet on ground
low = min((bm.matrix_world @ v.co).z for v in bm.data.vertices)
bm.location.z -= low
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT'); bm.select_set(True); bpy.context.view_layer.objects.active = bm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
print("DIMS", bm.dimensions)

rig = HumanService.add_builtin_rig(bm, "mixamo", import_weights=True)
rig.name = "Armature_Customer"
print("RIG", len(rig.data.bones), rig.location, rig.rotation_euler, rig.scale)

# ---- relaxed rest pose: drop arms ~22deg toward body, bake into mesh + rest pose
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
for side, ang in (("Left", 22), ("Right", -22)):
    pb = rig.pose.bones["mixamorig:%sArm" % side]
    head = pb.bone.head_local.copy()
    R = mathutils.Matrix.Rotation(math.radians(ang), 4, 'Y')
    T = mathutils.Matrix.Translation(head)
    pb.matrix = T @ R @ T.inverted() @ pb.bone.matrix_local
    # bring forearm slightly closer too
    bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT'); bm.select_set(True); bpy.context.view_layer.objects.active = bm
for m in list(bm.modifiers):
    if m.type == 'ARMATURE':
        bpy.ops.object.modifier_apply(modifier=m.name)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.armature_apply(selected=False)
bpy.ops.object.mode_set(mode='OBJECT')
mod = bm.modifiers.new("Armature", 'ARMATURE'); mod.object = rig
# shift so soles sit at z=0.015 (room for shoe sole thickness)
dz = -(min(v.co.z for v in bm.data.vertices if True) - 0.0)
vgb = bm.vertex_groups["body"].index
zmin = min(v.co.z for v in bm.data.vertices if any(g.group == vgb and g.weight > .5 for g in v.groups))
for ob in (bm, rig):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    ob.location.z = -(zmin - 0.015)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
print("ZMIN", zmin)

# expression unit shape keys
base = os.path.join(os.path.dirname(mp.__file__), "data", "targets", "expression", "units", "caucasian")
units = ["mouth-open","mouth-pursing","mouth-compression","mouth-corner-puller","mouth-elevation","mouth-eversion",
         "mouth-protusion","mouth-retraction","mouth-parling","mouth-depression","mouth-upward-retraction",
         "eye-left-closure","eye-right-closure","eyebrows-left-up","eyebrows-right-up","eyebrows-left-down","eyebrows-right-down"]
bm.shape_key_add(name="Basis")
for u in units:
    TargetService.load_target(bm, os.path.join(base, u + ".target.gz"), weight=0.0, name="u_" + u)
print("KEYS", [k.name for k in bm.data.shape_keys.key_blocks])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "stage1.blend"))


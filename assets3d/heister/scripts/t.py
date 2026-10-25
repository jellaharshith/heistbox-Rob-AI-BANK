"""Stage 1: MPFB2 male athletic base + game_engine rig + face shape keys. Saves heister_s1.blend"""
import bpy, os, sys, traceback
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.faceservice import FaceService

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")

m = TargetService.get_default_macro_info_dict()
m.update(gender=1.0, muscle=0.68, weight=0.45, proportions=0.55, height=0.6, age=0.5)
m["race"] = {"asian": 0.1, "caucasian": 0.45, "african": 0.45}
base = HumanService.create_human(mask_helpers=False, detailed_helpers=False, extra_vertex_groups=True,
                                 feet_on_ground=False, scale=0.1, macro_detail_dict=m)
print("BASE verts", len(base.data.vertices), "polys", len(base.data.polygons), "dims", tuple(base.dimensions))
try:
    pass
except Exception:
    traceback.print_exc()
sk = base.data.shape_keys
print("SHAPEKEYS", len(sk.key_blocks) if sk else 0, [k.name for k in sk.key_blocks][:80] if sk else None)
rig = HumanService.add_builtin_rig(base, "game_engine", import_weights=True)
print("RIG", rig.name, len(rig.data.bones))
print("VGROUPS", len(base.vertex_groups), [g.name for g in base.vertex_groups][:200])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s1.blend"))

print('PELVIS', bpy.data.objects['Human.rig'].data.bones['pelvis'].head_local, 'zmin', min(v.co.z for v in base.data.vertices), 'zmax', max(v.co.z for v in base.data.vertices))

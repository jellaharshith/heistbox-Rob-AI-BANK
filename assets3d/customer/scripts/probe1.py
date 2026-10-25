import bpy, sys
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.humanservice import HumanService
bm = HumanService.create_human(mask_helpers=False, detailed_helpers=True, extra_vertex_groups=True)
bg = bm.vertex_groups["body"].index
n=sum(1 for p in bm.data.polygons if all(any(g.group==bg and g.weight>0.5 for g in bm.data.vertices[v].groups) for v in p.vertices))
print("BODYPOLYS", n)
for rn in ["game_engine","mixamo","mixamo_unity"]:
    try:
        rig = HumanService.add_builtin_rig(bm, rn, import_weights=True)
        print("RIG", rn, len(rig.data.bones), [b.name for b in rig.data.bones])
        bpy.data.objects.remove(rig)
    except Exception as e:
        import traceback; traceback.print_exc()

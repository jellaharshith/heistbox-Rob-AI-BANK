import bpy
bm=bpy.data.objects["Body_full"]; rig=bpy.data.objects["Armature_Customer"]
print("P1", bm.location[:], bm.parent, bm.matrix_parent_inverse.translation[:], min(v.co.z for v in bm.data.vertices), bm.matrix_world.translation[:])
print("P2", rig.data.bones["mixamorig:LeftFoot"].head_local[:], rig.matrix_world.translation[:])

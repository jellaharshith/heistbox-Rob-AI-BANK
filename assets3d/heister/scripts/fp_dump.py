import bpy, os
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s5d.blend"))
rig = bpy.data.objects["CHAR_Heister"]
print("RIGMAT", [list(r) for r in rig.matrix_world])
for n in ["Hips", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase", "RightUpLeg", "RightFoot", "LeftToe_End", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "Head", "RightHand"]:
    b = rig.data.bones.get("mixamorig:" + n)
    if b:
        print("BONE", n, [round(x, 4) for x in b.head_local], [round(x, 4) for x in b.tail_local], "parent", b.parent.name if b.parent else None)
    else:
        print("nobone", n)
print([o.name for o in bpy.data.objects])

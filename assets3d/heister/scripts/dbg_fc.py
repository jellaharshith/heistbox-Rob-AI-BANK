import bpy, os
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s6.blend"))
a = bpy.data.actions["Heister_Walk"]
print("range", tuple(a.frame_range))
for l in a.layers:
    for s in l.strips:
        for cb in s.channelbags:
            for fc in cb.fcurves:
                if "Hips" in fc.data_path and "location" in fc.data_path or ("RightLeg" in fc.data_path and "quaternion" in fc.data_path):
                    print(fc.data_path, fc.array_index, [(round(k.co[0]), round(k.co[1], 4)) for k in fc.keyframe_points][:3], "...", [(round(k.co[0]), round(k.co[1], 4)) for k in fc.keyframe_points][-2:])

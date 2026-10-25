import bpy, os

ROOT = r"C:\Users\Shaik\Downloads\heistbox\assets3d\customer"
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "CHAR_Customer.blend"))
phone = bpy.data.objects["PROP_Phone"]
me = phone.data
uv = me.uv_layers.active.data
slot = next(i for i, m in enumerate(me.materials) if m and m.name == "MAT_PhoneRuntime")
loops = [li for poly in me.polygons if poly.material_index == slot for li in poly.loop_indices]
us = [uv[li].uv.x for li in loops]
vs = [uv[li].uv.y for li in loops]
umin, umax, vmin, vmax = min(us), max(us), min(vs), max(vs)
for li in loops:
    p = uv[li].uv
    p.x = (p.x - umin) / (umax - umin)
    p.y = (p.y - vmin) / (vmax - vmin)
print("screen UV before", (umin, umax, vmin, vmax))
print("screen UV after", (min(uv[li].uv.x for li in loops), max(uv[li].uv.x for li in loops),
                           min(uv[li].uv.y for li in loops), max(uv[li].uv.y for li in loops)))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "CHAR_Customer.blend"))

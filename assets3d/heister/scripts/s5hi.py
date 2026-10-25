"""Stage 5hi: subdivide hi-res and displace with procedural cloth detail (normal-map source). s5a -> s5hi blend"""
import bpy, os, sys, json
import numpy as np
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
from hlib import coords, vertex_normals
from detail import hi_height
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s5a.blend"))
O = bpy.data.objects
LM = json.load(open(os.path.join(H, "scripts", "landmarks_s4.json")))
rig = O["CHAR_Heister"]
B = {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in rig.data.bones}
body = O["CHAR_Heister_Body"]; duffel = O["CHAR_Heister_Duffel"]
C = dict(LM)
C["elbow"] = B["mixamorig:LeftForeArm"][0]
C["knee"] = B["mixamorig:LeftLeg"][0]
for side, nm in (("L", "Left"), ("R", "Right")):
    hnd = B[f"mixamorig:{nm}Hand"][0]
    fa = B[f"mixamorig:{nm}ForeArm"][0]
    ax = hnd - fa; ax /= np.linalg.norm(ax)
    C["hand_" + side] = hnd; C["axis_" + side] = ax
C["torso_cy"] = float(np.mean([v.co.y for v in body.data.vertices if 1.0 < v.co.z < 1.3 and abs(v.co.x) < 0.15]))
sh = [v.co for v in body.data.vertices]
pa = np.zeros(len(body.data.vertices), np.float32); body.data.attributes["part"].data.foreach_get("value", pa)
cs = coords(body.data)
shoe = cs[np.rint(pa) == 4]
C["shoe_ymin"] = float(shoe[:, 1].min())
C["foot_x"] = float(np.abs(shoe[:, 0]).mean())
pants = cs[np.rint(pa) == 3]
C["thigh_outer"] = float(np.abs(pants[(pants[:, 2] > 0.7) & (pants[:, 2] < 0.85)][:, 0]).max() * 0.98)
dc = coords(duffel.data)
zmin = dc[:, 2].min()
bag = dc[np.abs(dc[:, 0]) > 0.17]
C["duffel_c"] = (0.0, float(bag[:, 1].mean()), float(bag[:, 2].mean()))
C["duffel_r"] = 0.125; C["duffel_L"] = 0.26
json.dump({k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in C.items()}, open(os.path.join(H, "scripts", "ctx.json"), "w"))

for name, lv in (("HI_all", 2), ("HI_duffel", 2)):
    o = O[name]
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    md = o.modifiers.new("s", 'SUBSURF'); md.levels = lv; md.render_levels = lv
    bpy.ops.object.modifier_apply(modifier=md.name)
    me = o.data
    P = coords(me); N = vertex_normals(me)
    part = np.zeros(len(me.vertices), np.float32); me.attributes["part"].data.foreach_get("value", part)
    d = hi_height(P, N, part, C)
    print(name, "verts", len(P), "disp range", d.min(), d.max())
    me.vertices.foreach_set("co", (P + N * d[:, None]).astype(np.float32).ravel())
    me.update()
    print(name, "tris", sum(len(p.vertices) - 2 for p in me.polygons))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s5hi.blend"))



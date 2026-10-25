import bpy, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
O = bpy.data.objects
ob = O["CHAR_Customer_LOD0"]; me = ob.data
co = get_co(me)
kb = me.shape_keys.key_blocks
def key(n):
    a = np.empty(len(co) * 3); kb[n].data.foreach_get("co", a); return a.reshape(-1, 3)
d = key("jawOpen") - co
mag = np.linalg.norm(d, axis=1)
idx = np.where(mag > 0.0005)[0]
print("n moving", len(idx), "bbox", co[idx].min(0), co[idx].max(0))
print("maxdisp", mag.max(), "at", co[mag.argmax()], "dir", d[mag.argmax()])
# lips region: verts with large disp and near front
big = np.where(mag > 0.6 * mag.max())[0]
print("big n", len(big), co[big].min(0), co[big].max(0), co[big].mean(0))
# vertices in the mouth area: y < -0.05? print z-hist of moving verts front
front = idx[co[idx, 1] < co[idx, 1].min() + 0.06]
print("front", len(front), co[front].min(0), co[front].max(0))
# any internal verts: those behind lip plane within mouth box
c = co[big].mean(0)
box = np.where((abs(co[:, 0] - c[0]) < 0.03) & (abs(co[:, 2] - c[2]) < 0.03) & (co[:, 1] < c[1] + 0.06) & (co[:, 1] > c[1] - 0.02))[0]
print("box verts", len(box), "y range", co[box, 1].min(), co[box, 1].max())
for i in box[np.argsort(co[box, 1])][:5]: print(i, co[i])
print("faces", len(me.polygons), "uv", [u.name for u in me.uv_layers])
print("LOD0 tris", tri_count(me), "vgroups", len(ob.vertex_groups))
# interior: verts with y > lip y + 0.01 in the box -> mouth interior geometry
inner = box[co[box, 1] > c[1] + 0.012]
print("inner", len(inner), co[inner].min(0) if len(inner) else None, co[inner].max(0) if len(inner) else None)
# head bbox
hb = O["CHAR_Customer"]
print("head bone", [ (b.name, tuple(round(x,3) for x in b.head_local), tuple(round(x,3) for x in b.tail_local)) for b in hb.data.bones if b.name.endswith(("Head","Neck","RightHand","RightForeArm","RightArm","Spine2"))])
# nose tip: most -y vertex near x=0 in head
hv = np.where((co[:, 2] > 1.6) & (co[:, 2] < 1.75) & (abs(co[:, 0]) < 0.03))[0]
print("nose-ish", co[hv[co[hv, 1].argmin()]])

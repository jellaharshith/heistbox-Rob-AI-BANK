import bpy, numpy as np, sys, os, bmesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
O = bpy.data.objects
ob = O["CHAR_Customer_LOD0"]; me = ob.data
co = get_co(me)
kb = me.shape_keys.key_blocks
a = np.empty(len(co) * 3); kb["jawOpen"].data.foreach_get("co", a); d = a.reshape(-1, 3) - co
box = np.where((abs(co[:, 0] - 0) < 0.05) & (abs(co[:, 2] - 1.57) < 0.04) & (co[:, 1] < -0.07) & (co[:, 1] > -0.17))[0]
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
# boundary / non-manifold edges in box
bnd = [v.index for v in bm.verts if v.index in set(box) and any(e.is_boundary for e in v.link_edges)]
print("boundary verts in box", len(bnd))
for i in box[np.argsort(co[box][:, 1])]:
    print(i, np.round(co[i], 4), "jaw", np.round(d[i], 4), "nf", len(bm.verts[i].link_faces))

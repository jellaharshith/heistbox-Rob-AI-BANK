import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina/CHAR_Tina.blend")
ob = bpy.data.objects["CHAR_Tina_LOD0"]; me = ob.data; n = len(me.vertices)
kb = me.shape_keys.key_blocks
def g(k):
    a = np.empty(n*3, np.float32); kb[k].data.foreach_get("co", a); return a.reshape(-1,3)
B, A = g("Basis"), g("viseme_aa")
uv = me.uv_layers.active
for p in me.polygons:
    vs = list(p.vertices)
    if vs[0] >= 7031: continue
    cb = B[vs].mean(0); ca = A[vs].mean(0)
    if abs(cb[0]) < 0.014 and 1.395 < ca[2] < 1.445 and cb[1] < -0.10 and cb[2] > 1.395:
        u = uv.data[p.loop_start].uv
        print(p.index, len(vs), "rest", np.round(cb,4), "aa", np.round(ca,4), "uv", round(u[0],3), round(u[1],3), "mat", p.material_index)

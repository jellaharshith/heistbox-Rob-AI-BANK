import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina/CHAR_Tina.blend")
ob = bpy.data.objects["CHAR_Tina_LOD0"]; me = ob.data; n = len(me.vertices)
kb = me.shape_keys.key_blocks
def g(k):
    a = np.empty(n*3, np.float32); kb[k].data.foreach_get("co", a); return a.reshape(-1,3)
B, A = g("Basis"), g("viseme_aa")
for name, (a, b) in (("upper teeth", (7031, 7031+36)), ("lower teeth", (7067, 7067+36)), ("tongue", (7103, 7103+25)), ("dome", (7128, 7169))):
    print(name)
    for v in range(a, min(b, a+14)):
        print("  ", v, np.round(B[v], 4), "->", np.round(A[v], 4))

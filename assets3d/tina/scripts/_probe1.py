import bpy, numpy as np, sys
bpy.ops.wm.open_mainfile(filepath=r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina/CHAR_Tina_prefix.blend")
for lod in (0,):
    ob = bpy.data.objects["CHAR_Tina_LOD%d" % lod]
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n*3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1,3)
    print("LOD", lod, "verts", n, "mats", [m.name for m in me.materials], "uvl", [u.name for u in me.uv_layers])
    print("keys", [k.name for k in me.shape_keys.key_blocks])
    kb = me.shape_keys.key_blocks
    def kco(name):
        a = np.empty(n*3, np.float32); kb[name].data.foreach_get("co", a); return a.reshape(-1,3)
    for kn in ("jawOpen","viseme_aa","viseme_PP","viseme_O","viseme_U","viseme_FF"):
        d = kco(kn) - co
        m = np.linalg.norm(d, axis=1)
        idx = np.nonzero(m > 0.002)[0]
        print(kn, "moved>2mm", len(idx), "max", m.max(), "at", co[m.argmax()], "dz min", d[:,2].min(), "dy", d[:,1].min(), d[:,1].max())
    # mouth region
    sel = (np.abs(co[:,0]) < 0.04) & (co[:,2] > 1.405) & (co[:,2] < 1.46) & (co[:,1] < -0.06)
    print("mouth verts", sel.sum())
    for i in np.nonzero(sel)[0]:
        print(i, np.round(co[i],4), "jaw dz", round(float(kco("jawOpen")[i][2]-co[i][2]),4), "dy", round(float(kco("jawOpen")[i][1]-co[i][1]),4))
    # skin vert extent for head
    h = co[co[:,2]>1.35]
    print("head ymin/ymax", h[:,1].min(), h[:,1].max())

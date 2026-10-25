import bpy, os, sys, numpy as np, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s5hi.blend"))
sys.path.insert(0, os.path.join(H, "scripts"))
from rast import raster
O = bpy.data.objects
body = O["CHAR_Heister_Body"]; hi = O["HI_all"]
R = raster([body], 1024)
nrm = np.load(os.path.join(H, "textures", "bake_normal.npy"))
bad = (nrm[..., 2] < 0.3) & R["filled"] & np.isclose(R["part"], 2)
good = (nrm[..., 2] > 0.8) & R["filled"] & np.isclose(R["part"], 2)
bm = bmesh.new(); bm.from_mesh(hi.data)
bvh = BVHTree.FromBMesh(bm)
def stats(m, label):
    ys, xs = np.nonzero(m)
    idx = np.random.RandomState(0).choice(len(ys), 40, replace=False)
    ds = []; sd = []
    for i in idx:
        p = Vector(R["pos"][ys[i], xs[i]].tolist())
        loc, nor, fi, d = bvh.find_nearest(p)
        ds.append(d)
        # signed along lo normal
        sd.append((loc - p).dot(Vector(R["nrm"][ys[i], xs[i]].tolist())))
    print(label, "n", m.sum(), "dist mean", np.mean(ds), "signed mean", np.mean(sd), "min/max signed", min(sd), max(sd))
stats(bad, "bad"); stats(good, "good")
# mean lo normal vs pos for bad texels
print("bad nrm mean", R["nrm"][bad].mean(0), "pos mean", R["pos"][bad].mean(0))
print("tangent map mean bad", nrm[bad].mean(0))

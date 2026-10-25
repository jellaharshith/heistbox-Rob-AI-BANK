import bpy, os, sys, numpy as np
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
from rast import raster
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, os.environ.get("BLEND", "heister_s5a.blend")))
O = bpy.data.objects
objs = [O["CHAR_Heister_Body"], O["CHAR_Heister_Mask"], O["CHAR_Heister_Duffel"]]
R = raster(objs, 1024)
cmap = {0: (0, 0, 0), 1: (0.9, 0.6, 0.5), 2: (0.2, 0.3, 0.8), 3: (0.3, 0.6, 0.2), 4: (0.9, 0.9, 0.9), 5: (0.1, 0.1, 0.1), 6: (0.8, 0.1, 0.1), 7: (0.3, 0.3, 0.3), 8: (0.8, 0.6, 0.1), 10: (1, 1, 0), 11: (0.2, 0.8, 0.8), 12: (0.6, 0.9, 0.2)}
img = np.zeros((1024, 1024, 4), np.float32); img[..., 3] = 1
for k, c in cmap.items():
    m = np.isclose(R["part"], k) & R["filled"]
    img[m, :3] = c
print("filled fraction", R["filled"].mean())
im = bpy.data.images.new("uv", 1024, 1024, alpha=True)
im.pixels.foreach_set(img.ravel())
im.filepath_raw = os.path.join(H, "shots", "uvlayout.png"); im.file_format = 'PNG'; im.save()

import bpy, os, numpy as np, json
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "CHAR_Heister.blend"))
b = bpy.data.objects["CHAR_Heister_Body_LOD0"]
LM = json.load(open(os.path.join(H, "scripts", "landmarks_s4.json")))
kb = b.data.shape_keys.key_blocks
base = np.array([v.co[:] for v in kb[0].data])
ez = LM["eye_z"]
print("eye_z", ez)
for k in list(kb)[1:]:
    a = np.array([v.co[:] for v in k.data]) - base
    m = np.linalg.norm(a, axis=1)
    eyes = m[(base[:, 2] > ez - 0.02) & (base[:, 2] < ez + 0.03)]
    mouth = m[(base[:, 2] < ez - 0.04) & (base[:, 2] > ez - 0.13)]
    brow = m[(base[:, 2] > ez + 0.015) & (base[:, 2] < ez + 0.05)]
    print(f"{k.name:14s} val {k.value:.1f} eye-band max {eyes.max() if len(eyes) else 0:.4f} mouth-band max {mouth.max() if len(mouth) else 0:.4f} brow-band max {brow.max() if len(brow) else 0:.4f}  total max {m.max():.4f}")

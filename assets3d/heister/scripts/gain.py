import numpy as np, os
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister\scripts"
f = os.path.join(H, "facekeys_hi.npz")
d = dict(np.load(f))
GAIN = {"mouthSmile": 3.0, "viseme_PP": 2.0, "viseme_FF": 2.0, "viseme_U": 2.0, "viseme_SS": 2.0, "viseme_I": 1.6, "viseme_nn": 1.4, "browUp": 1.6, "browDown": 1.4}
for k, g in GAIN.items():
    d[k] = d[k] * g
np.savez_compressed(f, **d)
print("scaled")

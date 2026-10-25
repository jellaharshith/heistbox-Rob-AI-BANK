import bpy, sys, os, numpy as np
src = os.environ["N_IN"]; dst = os.environ["N_OUT"]
a = np.load(src).astype(np.float32)
if a.ndim == 2:
    a = np.stack([a, a, a, np.ones_like(a)], -1)
if a.shape[2] == 3:
    a = np.concatenate([a, np.ones(a.shape[:2] + (1,), np.float32)], -1)
h, w = a.shape[:2]
im = bpy.data.images.new("t", w, h, alpha=True)
im.colorspace_settings.name = 'Non-Color'
im.pixels.foreach_set(a.ravel())
im.filepath_raw = dst; im.file_format = 'PNG'; im.save()

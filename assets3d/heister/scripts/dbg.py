import bpy, numpy as np
for o in bpy.data.objects:
    if o.type != 'MESH':
        print(o.name, o.type, o.parent.name if o.parent else None); continue
    a = np.array([v.co[:] for v in o.data.vertices])
    print(o.name, len(a), "hide", o.hide_render, o.hide_viewport, "min", a.min(0).round(3), "max", a.max(0).round(3), "par", o.parent.name if o.parent else None, [m.type for m in o.modifiers],
          "keys", len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0)

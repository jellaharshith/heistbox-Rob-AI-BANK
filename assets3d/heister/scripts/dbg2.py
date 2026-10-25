import bpy
o=bpy.data.objects["Body_hi"]; print("UVL", [u.name for u in o.data.uv_layers], len(o.data.polygons), len(o.data.loops))

import bpy, bmesh
from mathutils import Vector
b = bpy.data.objects['Human'] if 'Human' in bpy.data.objects else [o for o in bpy.data.objects if o.type=='MESH'][0]
rig = [o for o in bpy.data.objects if o.type=='ARMATURE'][0]
print([ (o.name,o.type) for o in bpy.data.objects])
print("dims", b.dimensions, "loc", b.location, "rot", b.rotation_euler, "scale", b.scale, "parent", b.parent)
me = b.data
body_g = b.vertex_groups['body'].index
n_body = sum(1 for v in me.vertices if any(g.group==body_g and g.weight>0.5 for g in v.groups))
print("verts", len(me.vertices), "in body", n_body, "polys", len(me.polygons), "tris", sum(len(p.vertices)-2 for p in me.polygons))
for g in ['HelperGeometry','JointCubes','Left','Mid','Right','nipple','lips','fingernails','toenails','ears','scalp','genitals']:
    gi = b.vertex_groups[g].index
    print(g, sum(1 for v in me.vertices if any(x.group==gi and x.weight>0.5 for x in v.groups)))
mw = rig.matrix_world
for bn in rig.data.bones:
    print(bn.name, bn.parent.name if bn.parent else None, tuple(round(x,3) for x in (mw@bn.head_local)), tuple(round(x,3) for x in (mw@bn.tail_local)), bn.use_deform)
print("bb", [tuple(round(c,3) for c in v) for v in (Vector(c) for c in b.bound_box)][:2])
sk = me.shape_keys
print("sk", sk)

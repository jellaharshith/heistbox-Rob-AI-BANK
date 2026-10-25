import bpy, sys
fn=sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=fn)
O=bpy.data.objects
for o in O:
    if o.type=='MESH':
        me=o.data; t=sum(len(p.vertices)-2 for p in me.polygons)
        print("V", o.name, "tris",t,"mats",len(me.materials),"keys", len(me.shape_keys.key_blocks)-1 if me.shape_keys else 0, "parent", o.parent.name if o.parent else None, o.parent_bone)
    if o.type=='ARMATURE': print("V ARM", o.name, len(o.data.bones))
print("V ACTIONS", [(a.name, tuple(round(x) for x in a.frame_range)) for a in bpy.data.actions if not a.name.endswith('_face') ])
print("V IMAGES", [(i.name, tuple(i.size)) for i in bpy.data.images])

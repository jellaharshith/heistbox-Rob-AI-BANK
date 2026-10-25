import bpy, sys, os, math
argv = sys.argv[sys.argv.index("--") + 1:]
for path in argv:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    print("=====", os.path.basename(path), round(os.path.getsize(path) / 1024), "KB")
    total = 0
    for o in bpy.data.objects:
        info = ""
        if o.type == 'MESH':
            o.data.calc_loop_triangles(); t = len(o.data.loop_triangles); total += t
            info = f"tris={t} mats={[m.name for m in o.data.materials]} shapekeys={bool(o.data.shape_keys)}"
        print("OBJ", o.name, o.type, "loc", tuple(round(x, 3) for x in o.location),
              "rot", tuple(round(math.degrees(x), 1) for x in o.rotation_euler), info,
              "parent", o.parent.name if o.parent else None)
    print("TOTAL TRIS", total, "ARMATURES", sum(1 for o in bpy.data.objects if o.type == 'ARMATURE'))
    for a in bpy.data.actions:
        chans = set()
        for fc in a.fcurves if hasattr(a, "fcurves") else []:
            chans.add(fc.data_path)
        rng = tuple(round(x, 1) for x in a.frame_range)
        print("ACTION", a.name, rng, "paths", sorted(chans) if chans else "(slotted)")
        try:
            for l in a.layers:
                for s in l.strips:
                    for cb in s.channelbags:
                        print("   slot", cb.slot.name_display if hasattr(cb.slot, 'name_display') else cb.slot,
                              [(fc.data_path, fc.array_index) for fc in cb.fcurves][:3], len(cb.fcurves), "fcurves")
        except Exception as e:
            print("  err", e)
    for im in bpy.data.images:
        print("IMG", im.name, tuple(im.size))
    print("MATS", len(bpy.data.materials), [m.name for m in bpy.data.materials])

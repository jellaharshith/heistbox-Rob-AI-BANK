"""
export_utils.py - glTF export / optimise / verify helpers (Blender 5.2). Shared; keep API stable.

    import export_utils as eu
    eu.export_glb(objs, r"C:/.../export/CHAR_Tina.glb")                 # NLA_TRACKS, deform bones only, morph targets, no lights/cameras
    eu.optimize(in_glb, out_glb)                                        # npx @gltf-transform/cli optimize --compress meshopt --texture-compress webp
    info = eu.reimport_report(glb_path)                                 # run INSIDE a fresh Blender session (clears the scene)
    print(eu.format_report(info))

export_glb(objs, path, animation_mode='NLA_TRACKS', extra_kwargs=None)
optimize(src, dst, texture_size=None)         -> (returncode, stdout)
reimport_report(path)                         -> dict(meshes={name:{tris,verts,keys,mats}}, bones, clips={name:(frames,seconds)}, textures, ...)
tri_report(objs)                              -> {name: tris}
"""
import bpy, os, subprocess, shutil


def export_glb(objs, path, animation_mode='NLA_TRACKS', extra_kwargs=None):
    try:
        bpy.ops.preferences.addon_enable(module="io_scene_gltf2")
    except Exception:
        pass
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
              export_animations=True, export_animation_mode=animation_mode, export_frame_range=False,
              export_force_sampling=True, export_def_bones=True, export_skins=True, export_morph=True,
              export_morph_normal=True, export_lights=False, export_cameras=False, export_extras=False,
              export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
              export_image_format='AUTO', export_optimize_animation_size=False, export_anim_slide_to_zero=False,
              export_influence_nb=4, export_vertex_color='NONE', export_current_frame=False,
              export_reset_pose_bones=True)
    if extra_kwargs:
        kw.update(extra_kwargs)
    return bpy.ops.export_scene.gltf(**kw)


def optimize(src, dst, texture_size=None):
    cmd = ["npx", "--yes", "@gltf-transform/cli", "optimize", src, dst, "--compress", "meshopt",
           "--texture-compress", "webp"]
    if texture_size:
        cmd += ["--texture-size", str(texture_size)]
    r = subprocess.run(" ".join('"%s"' % c if " " in c else c for c in cmd), shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def tri_report(objs):
    return {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == 'MESH'}


def reimport_report(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="io_scene_gltf2")
    bpy.ops.import_scene.gltf(filepath=path)
    info = {"meshes": {}, "bones": 0, "clips": {}, "textures": {}, "armatures": [], "empties": []}
    for o in bpy.data.objects:
        if o.type == 'MESH':
            keys = [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
            info["meshes"][o.name] = dict(tris=sum(len(p.vertices) - 2 for p in o.data.polygons), verts=len(o.data.vertices),
                                          keys=[k for k in keys if k != "Basis"], mats=[m.name for m in o.data.materials if m],
                                          groups=len(o.vertex_groups))
        elif o.type == 'ARMATURE':
            info["armatures"].append(o.name)
            info["bones"] = max(info["bones"], len(o.data.bones))
        elif o.type == 'EMPTY':
            info["empties"].append(o.name)
    for a in bpy.data.actions:
        fr = a.frame_range
        info["clips"][a.name] = (round(fr[1] - fr[0]), round((fr[1] - fr[0]) / bpy.context.scene.render.fps, 3))
    for im in bpy.data.images:
        info["textures"][im.name] = tuple(im.size)
    return info


def format_report(info):
    lines = []
    for n, m in info["meshes"].items():
        lines.append("mesh %s: tris=%d verts=%d keys=%d mats=%s groups=%d" % (n, m["tris"], m["verts"], len(m["keys"]), m["mats"], m["groups"]))
    lines.append("bones=%d armatures=%s" % (info["bones"], info["armatures"]))
    lines.append("clips=%s" % info["clips"])
    lines.append("textures=%s" % info["textures"])
    return "\n".join(lines)

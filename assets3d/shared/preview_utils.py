"""
preview_utils.py - quick headless Workbench/EEVEE preview renders (PNG) so you can LOOK at your asset.

    import preview_utils as pv
    pv.shot(r"C:/.../shots/front.png", target=(0,0,1.0), eye=(0,-3,1.2), res=(640,900), lens=50,
            objects=None, textured=True)

`objects`: optional list of objects to show (others hidden for the render only).
`textured`: Workbench 'TEXTURE' colour mode when True else 'MATERIAL'.
"""
import bpy
from mathutils import Vector


def montage(paths, cols, out_path):
    """Tile PNG files into one PNG (numpy only). Images must share a size."""
    import numpy as np
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p, check_existing=False)
        w, h = im.size
        a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        imgs.append(a)
        bpy.data.images.remove(im)
    h, w = imgs[0].shape[:2]
    rows = (len(imgs) + cols - 1) // cols
    canvas = np.zeros((rows * h, cols * w, 4), dtype=np.float32)
    canvas[..., 3] = 1
    for i, a in enumerate(imgs):
        r, c = divmod(i, cols)
        # image rows start at the bottom in Blender; row 0 of the montage should be at the top
        y0 = (rows - 1 - r) * h
        canvas[y0:y0 + h, c * w:(c + 1) * w] = a
    o = bpy.data.images.new("_montage", cols * w, rows * h, alpha=True)
    o.pixels.foreach_set(canvas.ravel())
    o.filepath_raw = out_path
    o.file_format = 'PNG'
    o.save()
    bpy.data.images.remove(o)
    return out_path


def _look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def shot(path, target=(0, 0, 1), eye=(0, -3, 1.2), res=(640, 900), lens=50, objects=None,
         textured=True, engine='BLENDER_WORKBENCH', ortho_scale=None, transparent=False, flat=False):
    scn = bpy.context.scene
    cam = bpy.data.objects.get("_PV_CAM")
    if cam is None:
        cam = bpy.data.objects.new("_PV_CAM", bpy.data.cameras.new("_PV_CAM"))
        scn.collection.objects.link(cam)
    cam.data.lens = lens
    if ortho_scale:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho_scale
    else:
        cam.data.type = 'PERSP'
    cam.location = eye
    _look_at(cam, target)
    scn.camera = cam
    scn.render.engine = engine
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    scn.render.film_transparent = transparent
    scn.render.filepath = path
    scn.render.image_settings.file_format = 'PNG'
    try:
        sh = scn.display.shading
        sh.light = 'FLAT' if flat else 'STUDIO'
        sh.color_type = 'TEXTURE' if textured else 'MATERIAL'
        sh.show_cavity = False
        scn.display.render_aa = '8'
    except Exception as e:
        print("shading:", e)
    hidden = []
    if objects is not None:
        keep = set(objects)
        for o in scn.objects:
            if o.type in ('MESH', 'CURVE') and o not in keep and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    return path

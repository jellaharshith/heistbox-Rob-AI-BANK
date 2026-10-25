"""
bake_utils.py - headless Cycles texture baking helpers for Blender 5.x (shared; keep API stable).

Typical flow (see tina/scripts/s4_bake.py):
    import bake_utils as bk
    bk.setup_cycles(samples=16)
    img  = bk.new_image("Albedo", 2048, fill=(0.5,0.5,0.5,1))            # float, Non-Color (raw linear)
    tgt  = bk.make_target_material("BAKE_TARGET")                         # has an active Image Texture node
    for lo, hi in pairs:
        bk.bake_pass(lo, [hi], img, tgt, 'DIFFUSE', selected_to_active=True, extrusion=0.01, max_ray=0.03)
    arr = bk.image_to_array(img)                                         # (H,W,4) float32, row 0 = bottom
    bk.save_png_raw(arr_srgb_encoded, "C:/.../Tina_BaseColor.png")       # writes values as-is (8-bit)

Public API
    setup_cycles(samples=16, device='CPU')
    new_image(name, size, fill=(0,0,0,1), float_buffer=True) -> Image  (colorspace Non-Color)
    make_target_material(name)                                -> Material (image node is active)
    bake_pass(lo_obj, hi_objs, image, target_mat, bake_type, selected_to_active=True, extrusion=0.01, max_ray=0.03,
              margin=8, pass_filter=None, normal_space='TANGENT', clear=False, uv_name=None)
    image_to_array(img) / array_to_image(arr, img)
    linear_to_srgb(a) / srgb_to_linear(a)
    save_png_raw(arr, path, size=None)     arr is written without any colour management.
    pack_orm(ao, rough, metal)             -> (H,W,4) array R=AO G=Rough B=Metal
"""
import bpy
import numpy as np


def setup_cycles(samples=16, device='CPU'):
    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'
    scn.cycles.samples = samples
    try:
        scn.cycles.device = device
    except Exception as e:
        print("cycles device:", e)
    try:
        scn.cycles.use_denoising = False
    except Exception:
        pass
    scn.cycles.use_adaptive_sampling = False
    scn.render.bake.use_clear = False


def new_image(name, size, fill=(0, 0, 0, 1), float_buffer=True):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    w, h = (size, size) if isinstance(size, int) else size
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=float_buffer)
    img.colorspace_settings.name = 'Non-Color'
    a = np.empty((h, w, 4), dtype=np.float32)
    a[:] = fill
    img.pixels.foreach_set(a.ravel())
    img.update()
    return img


def make_target_material(name="BAKE_TARGET"):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.name = "BAKE_IMG"
    nt.nodes.active = tex
    tex.select = True
    return mat


def _assign_only_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def bake_pass(lo_obj, hi_objs, image, target_mat, bake_type, selected_to_active=True, extrusion=0.01,
              max_ray=0.03, margin=8, pass_filter=None, normal_space='TANGENT', clear=False, uv_name=None,
              restore_materials=True):
    """Bake `bake_type` from hi_objs onto lo_obj's active UV into `image`."""
    scn = bpy.context.scene
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    saved = [m for m in lo_obj.data.materials]
    _assign_only_material(lo_obj, target_mat)
    tex = target_mat.node_tree.nodes["BAKE_IMG"]
    tex.image = image
    target_mat.node_tree.nodes.active = tex
    if uv_name:
        lo_obj.data.uv_layers.active = lo_obj.data.uv_layers[uv_name]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for h in hi_objs:
        h.select_set(True)
    lo_obj.select_set(True)
    bpy.context.view_layer.objects.active = lo_obj
    b = scn.render.bake
    b.use_clear = clear
    kw = dict(type=bake_type, margin=margin, margin_type='EXTEND', use_selected_to_active=selected_to_active,
              normal_space=normal_space, target='IMAGE_TEXTURES', use_clear=clear)
    if selected_to_active:
        kw.update(cage_extrusion=extrusion, max_ray_distance=max_ray)
    if pass_filter is not None:
        kw['pass_filter'] = set(pass_filter)
    r = bpy.ops.object.bake(**kw)
    if restore_materials:
        lo_obj.data.materials.clear()
        for m in saved:
            lo_obj.data.materials.append(m)
    return r


def image_to_array(img):
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def array_to_image(arr, img):
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    img.update()


def linear_to_srgb(a):
    a = np.clip(a, 0.0, 1.0)
    return np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055)


def srgb_to_linear(a):
    a = np.clip(a, 0.0, 1.0)
    return np.where(a <= 0.04045, a / 12.92, np.power((a + 0.055) / 1.055, 2.4))


def save_png_raw(arr, path, size=None):
    """Write float array (H,W,4; values 0..1, row 0 = bottom) to an 8-bit PNG with no colour transform."""
    h, w = arr.shape[:2]
    img = bpy.data.images.new("_save_tmp", w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.clip(arr, 0, 1).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


def pack_orm(ao, rough, metal):
    h, w = ao.shape[:2]
    out = np.ones((h, w, 4), dtype=np.float32)
    out[..., 0] = ao[..., 0]
    out[..., 1] = rough[..., 0]
    out[..., 2] = metal if np.isscalar(metal) else metal[..., 0]
    return out

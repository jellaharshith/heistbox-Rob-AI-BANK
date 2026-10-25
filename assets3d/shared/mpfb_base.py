"""
mpfb_base.py - headless MPFB2 helpers for Blender 5.x (shared, do not break the public API).

Usage inside a headless script (blender.exe -b -P your_script.py):

    import sys; sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
    import mpfb_base as mb
    body, arm = mb.build_human(gender=0.0, age=0.54, rig="mixamo")
    # body: basemesh object ("body" only, helper geometry removed, macro targets baked into the basis)
    # arm : armature, Mixamo-named ("mixamorig:Hips", ...), 52 bones, weights already on `body`
    mb.load_unit_targets(body, ["mouth-open", "eye-left-closure"])   # MakeHuman expression units as shape keys

Public API
    enable_mpfb()
    build_human(gender, age, muscle, weight, proportions, height, cupsize, firmness, race, rig, keep_helpers)
    load_unit_targets(body, names, race="caucasian")
    unit_target_path(name, race="caucasian")
    remove_helper_geometry(body)
    dominant_bone_map(body)        -> list[str] bone name with highest weight per vertex
    rename_to_mixamo_if_needed(arm)  (no-op for rig="mixamo")

Notes (hard-won)
  * module name is "bl_ext.user_default.mpfb"; enable with bpy.ops.preferences.addon_enable.
  * gender: 0.0 = female, 1.0 = male. age: 0.5 = 25y, 1.0 = 90y.
  * create_human(detailed_helpers=True) is required for rig fitting (joint cubes). Helpers are stripped afterwards.
  * macro targets live as shape keys until TargetService.bake_targets(); we bake BEFORE adding the rig.
  * the MPFB "mixamo" rig json already uses mixamorig: naming (52 bones: Hips root, Spine/1/2, Neck, Head,
    Shoulder/Arm/ForeArm/Hand + 15 finger bones per side, UpLeg/Leg/Foot/ToeBase).
"""
import bpy
import os

MPFB_MODULE = "bl_ext.user_default.mpfb"
_DATA = os.path.join(os.environ.get("APPDATA", ""), "Blender Foundation", "Blender", "5.2",
                     "extensions", "user_default", "mpfb", "data")


def enable_mpfb():
    try:
        bpy.ops.preferences.addon_enable(module=MPFB_MODULE)
    except Exception as e:  # already enabled etc.
        print("enable_mpfb:", e)
    import importlib
    return importlib.import_module(MPFB_MODULE)


def unit_target_path(name, race="caucasian"):
    p = os.path.join(_DATA, "targets", "expression", "units", race, name + ".target.gz")
    if not os.path.isfile(p):
        raise IOError(p)
    return p


def load_unit_targets(body, names, race="caucasian"):
    """Load MakeHuman expression-unit targets as shape keys (value 0). Returns dict name->ShapeKey."""
    enable_mpfb()
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    out = {}
    if body.data.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)
    for n in names:
        sk = TargetService.load_target(body, unit_target_path(n, race), weight=0.0, name=n)
        sk.value = 0.0
        out[n] = sk
    return out


def remove_helper_geometry(body):
    """Delete every vertex that is not in the 'body' vertex group (helper geometry, joint cubes)."""
    import bmesh
    vg = body.vertex_groups.get("body")
    if vg is None:
        return
    # object-level mask modifiers would hide helpers; make sure none are applied twice
    for m in list(body.modifiers):
        if m.type == 'MASK':
            body.modifiers.remove(m)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    deform = bm.verts.layers.deform.verify()
    kill = []
    for v in bm.verts:
        w = v[deform].get(vg.index, 0.0)
        if w < 0.5:
            kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    for name in ("HelperGeometry", "JointCubes", "body"):
        g = body.vertex_groups.get(name)
        if g:
            body.vertex_groups.remove(g)


def build_human(gender=0.0, age=0.54, muscle=0.45, weight=0.45, proportions=0.5, height=0.5,
                cupsize=0.5, firmness=0.5, race=(0.0, 1.0, 0.0), rig="mixamo", keep_helpers=False,
                scale=0.1):
    """Create an MPFB human with a standard rig + weights. race = (asian, caucasian, african).
    Returns (body_object, armature_object)."""
    enable_mpfb()
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    md = TargetService.get_default_macro_info_dict()
    md.update(dict(gender=gender, age=age, muscle=muscle, weight=weight, proportions=proportions,
                   height=height, cupsize=cupsize, firmness=firmness))
    md["race"] = dict(asian=race[0], caucasian=race[1], african=race[2])
    body = HumanService.create_human(mask_helpers=False, detailed_helpers=True, extra_vertex_groups=False,
                                     feet_on_ground=True, scale=scale, macro_detail_dict=md)
    try:
        TargetService.bake_targets(body)
    except Exception as e:
        print("bake_targets:", e)
    # keep feet on the ground after baking
    arm = HumanService.add_builtin_rig(body, rig, import_weights=True)
    if not keep_helpers:
        remove_helper_geometry(body)
    bpy.context.view_layer.update()
    return body, arm


def dominant_bone_map(body):
    """For every vertex return the name of the vertex group with the highest weight."""
    names = {vg.index: vg.name for vg in body.vertex_groups}
    out = []
    for v in body.data.vertices:
        best, bw = None, -1.0
        for g in v.groups:
            if g.weight > bw:
                best, bw = names.get(g.group), g.weight
        out.append(best)
    return out

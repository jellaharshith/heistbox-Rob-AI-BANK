"""Stage 5: LOD0/1/2 objects, materials, weights, shape keys, armature parenting -> tina/CHAR_Tina_pre.blend"""
import sys
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina/scripts")
import bpy, bmesh, numpy as np
import mesh_utils as mu, tlib, tface

ROOT = r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina"
bpy.ops.wm.open_mainfile(filepath=ROOT + "/scripts/_stage3.blend")
PIECES = ["Skin", "Blazer", "Blouse", "Trousers", "Shoes"]
HI = {n: bpy.data.objects["Tina_%sHi" % n] for n in PIECES}
LO0 = {n: bpy.data.objects["Tina_%s_L0" % n] for n in PIECES}
body = bpy.data.objects["Tina_BodyHi"]
arm = bpy.data.objects["Tina_Armature"]
for o in bpy.data.objects:
    if o.name.startswith("Tina_") and o.type == 'MESH' and "_L" not in o.name and o is not body:
        pass

# ---------------- materials
def load_img(path, srgb):
    im = bpy.data.images.load(path)
    im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    return im

def make_main_material():
    m = bpy.data.materials.new("MAT_Tina")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = load_img(ROOT + "/textures/Tina_BaseColor.png", True); tb.label = "BaseColor"
    to = nt.nodes.new("ShaderNodeTexImage"); to.image = load_img(ROOT + "/textures/Tina_ORM.png", False); to.label = "ORM"
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = load_img(ROOT + "/textures/Tina_Normal.png", False); tn.label = "Normal"
    nt.links.new(tb.outputs["Color"], bs.inputs["Base Color"])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5
    nt.links.new(tb.outputs["Alpha"], gt.inputs[0]); nt.links.new(gt.outputs[0], bs.inputs["Alpha"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(to.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bs.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    grp = bpy.data.node_groups.get("glTF Material Output")
    if grp is None:
        grp = bpy.data.node_groups.new("glTF Material Output", 'ShaderNodeTree')
        grp.interface.new_socket("Occlusion", socket_type="NodeSocketFloat", in_out='INPUT')
    gn = nt.nodes.new("ShaderNodeGroup"); gn.node_tree = grp
    nt.links.new(sep.outputs["Red"], gn.inputs["Occlusion"])
    m.use_backface_culling = False       # hair/lash cards are single planes -> doubleSided
    return m

def make_seam_material():
    m = bpy.data.materials.new("MAT_Tina_Seam")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs[0])
    bs.inputs["Base Color"].default_value = (0.0, 0.08, 0.1, 1)
    bs.inputs["Roughness"].default_value = 0.4
    bs.inputs["Emission Color"].default_value = (0.0, 0.85, 1.0, 1)
    bs.inputs["Emission Strength"].default_value = 2.0
    m.use_backface_culling = False
    return m

MAT = make_main_material(); MSEAM = make_seam_material()

def set_mats(ob, slot):
    ob.data.materials.clear()
    ob.data.materials.append(MAT); ob.data.materials.append(MSEAM)
    ob.data.polygons.foreach_set("material_index", [slot] * len(ob.data.polygons))

TARGETS = {1: dict(Skin=2400, Blazer=1500, Blouse=160, Trousers=750, Shoes=280),
           2: dict(Skin=1050, Blazer=650, Blouse=60, Trousers=330, Shoes=140)}

col = bpy.data.collections.new("CHAR_Tina"); bpy.context.scene.collection.children.link(col)
results = {}
for lod in (0, 1, 2):
    parts = []   # (obj, kind) kind: gate eligible 'skin'/'face' else None
    for n in PIECES:
        if lod == 0:
            o = mu.copy_object(LO0[n], "p_%s_%d" % (n, lod))
        else:
            if lod == 2 and n == "Blouse":
                o = tlib.lod_from(LO0[n], TARGETS[lod][n], "p_%s_%d" % (n, lod), delimit=None)
            else:
                o = tlib.lod_from(LO0[n], TARGETS[lod][n], "p_%s_%d" % (n, lod), keep_face=False,
                                  delimit=('UV',) if lod == 1 else None)
        mu.limit_and_normalize_weights(o, 4, keep_prefix="mixamorig:")
        parts.append((o, "skin" if n == "Skin" else None, 0))
    skin_obj = parts[0][0]
    hair = tlib.build_hair(HI["Skin"], lod); parts.append((hair, None, 0))
    # eyes are separate objects now (CHAR_Tina_Eyes empty, see below) -> not part of the body LOD meshes
    lashes = tlib.build_lashes(lod); parts.append((lashes, "skin", 0))
    mouth = tlib.build_mouth(lod) if lod < 2 else None
    if mouth is not None:
        parts.append((mouth, "mouth", 0))
    hs = tlib.build_headset(lod); parts.append((hs, None, 0))
    btn = tlib.build_buttons(HI["Blazer"], lod)
    if btn: parts.append((btn, None, 0))
    pin = tlib.build_pin(HI["Blazer"], lod); parts.append((pin, None, 1))
    seam = tlib.build_seam(skin_obj, lod); parts.append((seam, "skin", 1))
    mask = []
    objs = []
    mouth_rng = None
    skin_nv = len(skin_obj.data.vertices)
    for ob, kind, slot in parts:
        ob.name = "q_" + ob.name
        set_mats(ob, slot)
        if kind == "mouth":
            mouth_rng = (len(mask), len(mask) + len(ob.data.vertices))
        mask += [kind == "skin"] * len(ob.data.vertices)
        objs.append(ob)
    # remove helper uv layers other than UVMap
    for ob in objs:
        while len(ob.data.uv_layers) > 1:
            ob.data.uv_layers.remove(ob.data.uv_layers[-1])
        ob.data.uv_layers[0].name = "UVMap"
    J = mu.join(objs, "CHAR_Tina_LOD%d" % lod)
    mu.limit_and_normalize_weights(J, 4, keep_prefix="mixamorig:")
    mu.transfer_shape_keys(body, J, vert_filter=np.array(mask), falloff=(0.004, 0.014))
    J.data.shape_keys.name = "Key"
    skin_only = np.zeros(len(J.data.vertices), dtype=bool); skin_only[:skin_nv] = True
    tface.tune_visemes(J, skin_only)
    ninterior = tface.recolor_interior(J, skin_only)
    if mouth_rng:
        B = np.empty(len(J.data.vertices) * 3, np.float32); J.data.shape_keys.key_blocks["Basis"].data.foreach_get("co", B); B = B.reshape(-1, 3)
        mc = tlib.MOUTH_COUNTS
        m0 = mouth_rng[0]
        dome0 = m0 + 2 * mc["teeth"] + mc["tongue"]
        ups = list(range(m0, m0 + mc["teeth"])) + [v for v in range(dome0, mouth_rng[1]) if B[v, 2] > 1.4325]
        tface.set_upper(ups)
        tface.mouth_deltas(J, mouth_rng, skin_only)
    print("LOD", lod, "interior faces recoloured", ninterior, "mouth verts", mouth_rng)
    results[lod] = J
    print("LOD", lod, "tris", mu.tri_count(J), "verts", len(J.data.vertices), "keys", len(J.data.shape_keys.key_blocks) - 1)

# ---------------- hierarchy
arm.name = "CHAR_Tina"
arm.data.name = "CHAR_Tina_Armature"
for c in list(arm.users_collection):
    c.objects.unlink(arm)
col.objects.link(arm)
for lod, J in results.items():
    for c in list(J.users_collection):
        c.objects.unlink(J)
    col.objects.link(J)
    J.parent = arm
    J.matrix_parent_inverse = arm.matrix_world.inverted()
    J.modifiers.clear()
    m = J.modifiers.new("Armature", 'ARMATURE'); m.object = arm
    for vg in list(J.vertex_groups):
        if not vg.name.startswith("mixamorig:"):
            J.vertex_groups.remove(vg)
    for sm in J.data.polygons:
        sm.use_smooth = True
# ---------------- eyes: CHAR_Tina_Eyes empty (parented to mixamorig:Head) -> CHAR_Tina_EyeL / CHAR_Tina_EyeR
from mathutils import Matrix, Vector
eyes_empty = bpy.data.objects.new("CHAR_Tina_Eyes", None)
eyes_empty.empty_display_type = 'PLAIN_AXES'; eyes_empty.empty_display_size = 0.03
col.objects.link(eyes_empty)
mid = (tlib.EYE_C["L"] + tlib.EYE_C["R"]) * 0.5
bpy.context.view_layer.update()
pb = arm.pose.bones["mixamorig:Head"]
pm = arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
eyes_empty.parent = arm; eyes_empty.parent_type = 'BONE'; eyes_empty.parent_bone = "mixamorig:Head"
eyes_empty.matrix_parent_inverse = pm.inverted()
eyes_empty.location = mid
eye_objs = []
for side in ("L", "R"):
    e = tlib.build_eye_object(side, 0)
    for c in list(e.users_collection):
        c.objects.unlink(e)
    col.objects.link(e)
    e.data.materials.clear(); e.data.materials.append(MAT)
    for p in e.data.polygons:
        p.use_smooth = True
    e.parent = eyes_empty
    e.matrix_parent_inverse = Matrix.Identity(4)
    e.location = tlib.EYE_C[side] - mid
    eye_objs.append(e)
bpy.context.view_layer.update()
for e in eye_objs:
    print("EYE", e.name, "world", tuple(round(v, 4) for v in e.matrix_world.translation), "tris", mu.tri_count(e))

# hide / remove everything else
keep = set(results.values()) | {arm, eyes_empty} | set(eye_objs)
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)
arm.show_in_front = False
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/scripts/_stage5.blend")


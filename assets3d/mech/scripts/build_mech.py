import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Matrix, Vector

ROOT = r"C:\Users\Shaik\Downloads\heistbox\assets3d\mech"
sys.path.insert(0, ROOT + r"\scripts")
import importlib, mech_tex
importlib.reload(mech_tex)

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
sc.render.fps = 30

# ---------------------------------------------------------------- materials
def make_image(name, arr, colorspace, path):
    n = arr.shape[0]
    img = bpy.data.images.new(name, n, n, alpha=False)
    rgba = np.ones((n, n, 4), np.float32); rgba[..., :3] = arr
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    img.pack()
    return img


def occlusion_group():
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", 'ShaderNodeTree')
        g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    return g


def pbr_material(name, tex):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tdir = ROOT + r"\textures"

    def tex_node(key, cs, x, y):
        img = make_image(f"{name}_{key}", tex[key], cs, f"{tdir}\\{name}_{key}.png")
        t = nodes.new("ShaderNodeTexImage"); t.image = img; t.location = (x, y)
        return t
    tb = tex_node("base", "sRGB", -700, 300)
    links.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
    to = tex_node("orm", "Non-Color", -700, 0)
    sep = nodes.new("ShaderNodeSeparateColor"); sep.location = (-420, 0)
    links.new(to.outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    grp = nodes.new("ShaderNodeGroup"); grp.node_tree = occlusion_group(); grp.location = (-200, -200)
    links.new(sep.outputs["Red"], grp.inputs["Occlusion"])
    tn = tex_node("normal", "Non-Color", -700, -300)
    nm = nodes.new("ShaderNodeNormalMap"); nm.location = (-420, -300)
    links.new(tn.outputs["Color"], nm.inputs["Color"])
    links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if tex.get("emissive") is not None:
        te = tex_node("emissive", "sRGB", -700, -600)
        links.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return m


def emissive_material(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*[c * 0.2 for c in color], 1)
    b.inputs["Roughness"].default_value = 0.4
    b.inputs["Emission Color"].default_value = (*color, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m


# ---------------------------------------------------------------- geometry helpers
class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def _new(self, fn, uvfn, smooth=False):
        before = set(self.bm.faces)
        fn()
        new = [f for f in self.bm.faces if f not in before]
        for f in new:
            f.smooth = smooth
            if uvfn:
                for l in f.loops:
                    l[self.uv].uv = uvfn(l.vert.co)
        return new

    def box(self, size, loc, uvfn, rot=None):
        mat = Matrix.Translation(loc) @ (rot if rot is not None else Matrix.Identity(4))
        return self._new(lambda: bmesh.ops.create_cube(self.bm, size=1.0, matrix=mat @ Matrix.Diagonal((*size, 1))), uvfn)

    def cyl(self, r1, r2, depth, seg, loc, uvfn, rot=None, smooth=False, caps=True):
        mat = Matrix.Translation(loc) @ (rot if rot is not None else Matrix.Identity(4))
        return self._new(lambda: bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=seg,
                                                        radius1=r1, radius2=r2, depth=depth, matrix=mat), uvfn, smooth)

    def sphere(self, r, us, vs, loc, uvfn, smooth=True):
        return self._new(lambda: bmesh.ops.create_uvsphere(self.bm, u_segments=us, v_segments=vs, radius=r,
                                                           matrix=Matrix.Translation(loc)), uvfn, smooth)

    def torus(self, R, r, nu, nv, mat, uvfn):
        def fn():
            vs = []
            for i in range(nu):
                a = 2 * math.pi * i / nu
                row = []
                for j in range(nv):
                    b = 2 * math.pi * j / nv
                    p = Vector(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
                    row.append(self.bm.verts.new(mat @ p))
                vs.append(row)
            for i in range(nu):
                for j in range(nv):
                    self.bm.faces.new((vs[i][j], vs[(i + 1) % nu][j], vs[(i + 1) % nu][(j + 1) % nv], vs[i][(j + 1) % nv]))
        return self._new(fn, uvfn, True)

    def lathe(self, prof, seg, uvfn):
        """profile (r, y) around Y axis; each profile segment gets its own verts (hard edges between segments)"""
        def fn():
            for (r0, y0), (r1, y1) in zip(prof[:-1], prof[1:]):
                def ring(r, y):
                    if r == 0:
                        return [self.bm.verts.new((0, y, 0))] * seg
                    return [self.bm.verts.new((r * math.cos(2 * math.pi * i / seg), y, r * math.sin(2 * math.pi * i / seg)))
                            for i in range(seg)]
                a = ring(r0, y0); b = ring(r1, y1)
                for i in range(seg):
                    j = (i + 1) % seg
                    q = [a[i], a[j], b[j], b[i]]
                    uq = []
                    for v in q:
                        if v not in uq:
                            uq.append(v)
                    if len(uq) >= 3:
                        # keep winding facing outward: front (y<0) faces point to -Y
                        self.bm.faces.new(uq)
        return self._new(fn, uvfn, True)

    def finish(self, name, material):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(name, me)
        me.materials.append(material)
        return ob


def tri_count(ob):
    me = ob.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def new_collection(name):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    return c


def rotY(a):
    return Matrix.Rotation(a, 4, 'Y')


RX90 = Matrix.Rotation(math.radians(90), 4, 'X')

# ---------------------------------------------------------------- vault doors
def build_door(name, mat, variant, world_hinge):
    B = Builder()
    R = 1.1

    def uv(co):
        return (min(max((co.x + R) / (2 * R), 0.01), 0.99), min(max((co.z + R) / (2 * R), 0.01), 0.99))
    const = lambda u, v: (lambda co: (u, v))
    seg = 64
    prof = [(0, -0.14), (0.80, -0.14), (0.86, -0.20), (1.02, -0.20), (1.06, -0.16), (1.10, -0.16),
            (1.10, 0.16), (1.06, 0.20), (0, 0.20)]
    B.lathe(prof, seg, uv)
    # bolt heads on raised ring
    for i in range(12):
        a = i * math.pi / 6
        B.cyl(0.05, 0.045, 0.05, 8, (0.93 * math.cos(a), -0.225, 0.93 * math.sin(a)), uv, rot=RX90)
    # central wheel: hub, rim torus, spokes, handles
    B.cyl(0.20, 0.17, 0.14, 20, (0, -0.21, 0), uv, rot=RX90, smooth=True)
    B.torus(0.40, 0.035, 24, 6, Matrix.Translation((0, -0.20, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'), uv)
    nsp = 6
    for i in range(nsp):
        a = i * 2 * math.pi / nsp
        B.box((0.22, 0.05, 0.05), (0.29 * math.cos(a), -0.20, 0.29 * math.sin(a)), uv, rot=rotY(-a))
        B.cyl(0.04, 0.035, 0.10, 8, (0.45 * math.cos(a), -0.20, 0.45 * math.sin(a)), uv, rot=RX90, smooth=False)
    # hinge: barrel at the hinge axis (x=-R after centring => local origin), two arms
    hx = -R
    B.cyl(0.085, 0.085, 1.5, 14, (hx - 0.03, 0.0, 0.0), uv, smooth=True)
    for z in (-0.55, 0.0, 0.55):
        B.cyl(0.11, 0.11, 0.16, 14, (hx - 0.03, 0.0, z), uv, smooth=True)
        B.box((0.16, 0.12, 0.12), (hx + 0.06, 0.0, z), uv)
    if variant == 'R':
        # heavy steel: 8 lugs + cyan airlock ring torus (emissive via texture annulus r 0.67-0.73)
        for i in range(8):
            a = i * math.pi / 4
            B.box((0.22, 0.30, 0.14), (1.10 * math.cos(a), 0.0, 1.10 * math.sin(a)), uv, rot=rotY(-a))
        B.torus(0.70, 0.032, 48, 6, Matrix.Translation((0, -0.15, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'), uv)
    if variant == 'M':
        # red lockdown bars (UV -> red emissive swatch in texture corner)
        red = const(0.94, 0.05)
        for z in (-0.45, 0.45):
            B.box((2.0, 0.06, 0.12), (0, -0.23, z), red)
    if variant == 'L':
        # chipped brass: a broken lug on rim near the crack
        a = math.radians(35)
        B.box((0.10, 0.22, 0.08), (1.12 * math.cos(a), 0.0, 1.12 * math.sin(a)), uv, rot=rotY(-a))
    # shift so hinge axis is the origin: disc centre goes to local x=+R (the barrel lands at ~origin)
    bmesh.ops.translate(B.bm, vec=(R + 0.03, 0, 0), verts=B.bm.verts)
    ob = B.finish(name, mat)
    ob.location = world_hinge
    return ob


# ---------------------------------------------------------------- vault props
def build_shredder(mat):
    B = Builder()
    def box_uv(co):   # tiling steel area, kept inside u,v<0.85
        return (0.1 + 0.4 * (co.x + 0.5), 0.15 + 0.4 * (co.z * 0.5 + 0.5) * 0.9)
    sw = lambda u: (lambda co: (u, 0.05))
    DARK, SLOT, GREEN, AMBER, RED = 0.91, 0.93, 0.95, 0.97, 0.99
    # collection bin / base cabinet
    B.box((0.80, 0.50, 0.62), (0, 0, 0.31), box_uv)
    B.box((0.70, 0.02, 0.50), (0, -0.26, 0.31), sw(DARK))               # bin front panel
    B.box((0.20, 0.03, 0.04), (0, -0.28, 0.40), box_uv)                 # handle
    # shredder head
    B.box((0.90, 0.56, 0.20), (0, 0, 0.72), box_uv)
    B.box((0.70, 0.30, 0.03), (0, 0, 0.835), sw(SLOT))                  # paper slot
    B.box((0.78, 0.02, 0.12), (0, -0.29, 0.72), sw(DARK))               # control strip
    B.cyl(0.015, 0.015, 0.01, 8, (-0.2, -0.30, 0.72), sw(GREEN), rot=RX90)
    B.cyl(0.015, 0.015, 0.01, 8, (0.2, -0.30, 0.72), sw(AMBER), rot=RX90)
    # rear mast to the laser emitter
    B.box((0.08, 0.08, 1.45), (0.36, 0.0, 0.725), box_uv)
    B.box((0.90, 0.08, 0.08), (-0.05, 0.0, 1.46), box_uv)               # arm over to -X side
    B.cyl(0.05, 0.05, 0.12, 12, (-0.50, 0.0, 1.5), sw(RED), rot=rotY(math.radians(90)), smooth=True)  # emitter lens
    B.cyl(0.07, 0.07, 0.10, 12, (-0.44, 0.0, 1.5), sw(DARK), rot=rotY(math.radians(90)), smooth=True)
    for sx in (-0.34, 0.34):                                           # feet
        for sy in (-0.2, 0.2):
            B.cyl(0.04, 0.04, 0.03, 8, (sx, sy, 0.015), sw(DARK))
    ob = B.finish("PROP_Shredder", mat)
    return ob


def build_laser(mat, length):
    B = Builder()
    # cylinder along -X, origin at start (emitter)
    B.cyl(0.015, 0.015, length, 8, (-length / 2, 0, 0), None, rot=rotY(math.radians(90)), smooth=True, caps=True)
    return B.finish("FX_Laser", mat)


def build_strip(name, mat, length=3.0):
    B = Builder()
    B.box((length, 0.04, 0.06), (0, 0, 0), None)
    return B.finish(name, mat)


# ---------------------------------------------------------------- sentinel
def build_sentinel(mat, hover=1.0):
    B = Builder()
    SR = 0.30
    TAU = 2 * math.pi

    # body sphere with lat-long UV (u wrap handled per face afterwards)
    def body_uv(co):
        u = math.atan2(co.y, co.x) / TAU + 0.5
        lat = math.asin(max(-1, min(1, co.z / SR)))
        return (u, 0.3 + 0.7 * (lat + math.pi / 2) / math.pi)
    faces = B.sphere(SR, 24, 14, (0, 0, 0), None)
    uvl = B.uv
    for f in faces:
        us = []
        for l in f.loops:
            uvc = body_uv(l.vert.co); l[uvl].uv = uvc
        # fix wrap and poles
        loops = list(f.loops)
        pole = [abs(l.vert.co.x) < 1e-5 and abs(l.vert.co.y) < 1e-5 for l in loops]
        reg = [l[uvl].uv[0] for l, p in zip(loops, pole) if not p]
        if reg and max(reg) - min(reg) > 0.5:
            for l, p in zip(loops, pole):
                if not p and l[uvl].uv[0] < 0.5:
                    l[uvl].uv[0] += 1.0
            reg = [l[uvl].uv[0] for l, p in zip(loops, pole) if not p]
        if reg:
            mu = sum(reg) / len(reg)
            for l, p in zip(loops, pole):
                if p:
                    l[uvl].uv[0] = mu
    steel_uv = lambda co: (0.7, 0.65)
    dark_uv = lambda co: (0.55, 0.10)
    ring_uv = lambda co: (0.5, 0.02)
    LZ = 0.095
    lens_uv = lambda co: (0.14 + co.x * (0.12 / 0.11), 0.16 + (co.z - LZ) * (0.12 / 0.11))
    # ring light just below the equator so it clears the lens
    B.torus(0.310, 0.030, 24, 6, Matrix.Translation((0, 0, -0.065)), ring_uv)
    # single lens facing -Y: bezel + glass disc (flat disc planar-UV'd to the lens square)
    B.cyl(0.115, 0.105, 0.07, 20, (0, -SR + 0.01, LZ), lens_uv, rot=RX90, smooth=False)
    B.cyl(0.105, 0.105, 0.012, 20, (0, -SR - 0.030, LZ), lens_uv, rot=RX90)
    # side pods and top antenna and bottom emitter
    for s in (-1, 1):
        B.box((0.07, 0.16, 0.10), (s * 0.335, 0.02, 0.12), dark_uv, rot=Matrix.Rotation(s * math.radians(-12), 4, 'Z'))
        B.cyl(0.02, 0.02, 0.16, 8, (s * 0.36, 0.02, 0.19), steel_uv)
    B.cyl(0.012, 0.008, 0.20, 6, (0.0, 0.10, SR + 0.07), steel_uv, smooth=True)
    B.sphere(0.022, 8, 5, (0.0, 0.10, SR + 0.17), ring_uv)
    B.cyl(0.07, 0.035, 0.07, 12, (0, 0, -SR - 0.01), dark_uv, smooth=True)
    bmesh.ops.translate(B.bm, vec=(0, 0, hover), verts=B.bm.verts)
    ob = B.finish("CHAR_Sentinel", mat)
    return ob


# ---------------------------------------------------------------- animation helpers
def push_clip(ob, clip, length, keys, loop=True):
    """keys: list of (frame, {channel_path: value}) for object transform. Creates Action -> NLA track."""
    ad = ob.animation_data or ob.animation_data_create()
    act = bpy.data.actions.new(clip)
    ad.action = act
    first = True
    for frame, vals in keys:
        for path, idx_vals in vals.items():
            setattr(ob, path, idx_vals)
        for path in vals:
            ob.keyframe_insert(path, frame=frame)
    # smooth interpolation
    for fc in act.layers[0].strips[0].channelbags[0].fcurves if hasattr(act, "layers") and act.layers else act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
    start = int(keys[0][0])
    tr = ad.nla_tracks.new(); tr.name = clip
    st = tr.strips.new(clip, start, act)
    st.name = clip
    ad.action = None
    return act


def reset_tx(ob, loc, rot=(0, 0, 0), scale=(1, 1, 1)):
    ob.location = loc; ob.rotation_euler = rot; ob.scale = scale


# ================================================================ BUILD
tex = {
    'L': mech_tex.tex_door_L(), 'M': mech_tex.tex_door_M(), 'R': mech_tex.tex_door_R(),
    'S': mech_tex.tex_sentinel(), 'SH': mech_tex.tex_shredder(),
}
mats = {
    'L': pbr_material("MAT_VaultBrass", tex['L']),
    'M': pbr_material("MAT_VaultIce", tex['M']),
    'R': pbr_material("MAT_VaultGunmetal", tex['R']),
    'S': pbr_material("MAT_Sentinel", tex['S']),
    'SH': pbr_material("MAT_Shredder", tex['SH']),
}
mat_laser = emissive_material("MAT_Laser", (1.0, 0.06, 0.05), 6.0)
mat_stripL = emissive_material("MAT_LockdownStrip_L", (1.0, 0.62, 0.15), 3.0)
mat_stripM = emissive_material("MAT_LockdownStrip_M", (1.0, 0.04, 0.04), 4.0)
mat_stripR = emissive_material("MAT_LockdownStrip_R", (0.0, 0.9, 1.0), 4.0)

yb = 6.0
xs = [-4.6, 0.0, 4.6]
props = new_collection("MECH_VaultProps")
char = new_collection("CHAR_Sentinel")

# --- doors (hinge positions match blockout: centre x, hinge at x-1.1, y=yb+0.5, z=1.6)
doors = {}
for key, x, nm in (('L', xs[0], "VAULT_L_Door"), ('M', xs[1], "VAULT_M_Door"), ('R', xs[2], "VAULT_R_Door")):
    d = build_door(nm, mats[key], key, (x - 1.1, yb + 0.5, 1.6))
    props.objects.link(d)
    doors[key] = d
    # Open: swing outward (toward hall, -Y side) about the vertical hinge axis (Z), 0 -> -100deg
    base = (x - 1.1, yb + 0.5, 1.6)
    # L door starts AJAR (-12 deg about the hinge): that is its node rest pose AND the first key of its Open clip
    AJAR = math.radians(-12)
    z0 = AJAR if key == 'L' else 0.0
    rz = lambda a: {"rotation_euler": (0, 0, a)}
    open_keys = [(1, rz(z0)), (12, rz(math.radians(-8))), (45, rz(math.radians(-100)))]
    slam_keys = [(1, rz(math.radians(-100))), (9, rz(math.radians(-2))), (11, rz(math.radians(-0.0))),
                 (14, rz(math.radians(-6))), (20, rz(0))]
    # shared contract clips (all three doors carry them) + per-door clips (own door only), same keys
    # ORDER matters: the glTF importer (env merge_props.py) puts the FIRST animation of the file on TOP of the NLA stack and the
    # re-export takes the node rest pose from that top track -> VaultDoor_Open (starts at the rest pose) must come first.
    # (export_mech.py also patches the raw node rest rotations, because a direct export evaluates the LAST track = Slam.)
    for cname, keys in (("VaultDoor_Open", open_keys), ("VaultDoor_Slam", slam_keys),
                        (f"VAULT_{key}_Door_Open", open_keys), (f"VAULT_{key}_Door_Slam", slam_keys)):
        reset_tx(d, base)
        push_clip(d, cname, 0, keys)
    if key == 'L':
        reset_tx(d, base)
        push_clip(d, "VAULT_L_Door_Ajar", 0, [(1, rz(AJAR)), (10, rz(AJAR - math.radians(0.05)))])
    # rest pose: L ajar, M/R closed
    reset_tx(d, base, (0, 0, z0))
    d.animation_data.action = None
# --- shredder + laser: shredder at (2.2, 0.5, 0); emitter lens at local (-0.5,0,1.5) -> world (1.7,0.5,1.5);
#     laser runs along -X to ANCHOR_LaserTarget (0,0.5,1.5)
SH_LOC = Vector((2.2, 0.5, 0.0))
sh = build_shredder(mats['SH']); sh.location = SH_LOC; props.objects.link(sh)
emit_world = SH_LOC + Vector((-0.56, 0, 1.5))
laser = build_laser(mat_laser, emit_world.x - 0.0); laser.location = emit_world; props.objects.link(laser)

# --- lockdown strips: horizontal bars above each vault door inside the alcove frame
for key, x, m in (('L', xs[0], mat_stripL), ('M', xs[1], mat_stripM), ('R', xs[2], mat_stripR)):
    s = build_strip(f"FX_LockdownStrip_{key}", m, 3.2)
    s.location = (x, yb + 0.25, 3.15)
    props.objects.link(s)

# --- sentinel
mesh_s = build_sentinel(mats['S'])
char.objects.link(mesh_s)
reset_tx(mesh_s, (0, 0, 0))
H = lambda fr, z=0.0, rz=0.0, rx=0.0, ry=0.0, loc_y=0.0, s=(1, 1, 1): (fr, {
    "location": (0, loc_y, z), "rotation_euler": (rx, ry, rz), "scale": s})
push_clip(mesh_s, "Sentinel_Hover", 60, [
    H(1, 0.0, 0, 0, math.radians(-2)), H(16, 0.06, math.radians(2), math.radians(1.5), 0),
    H(31, 0.0, 0, 0, math.radians(2)), H(46, -0.06, math.radians(-2), math.radians(-1.5), 0),
    H(61, 0.0, 0, 0, math.radians(-2))])
reset_tx(mesh_s, (0, 0, 0))
push_clip(mesh_s, "Sentinel_Scan", 90, [
    H(1, 0.0, math.radians(0)), H(23, 0.03, math.radians(45), math.radians(3)),
    H(45, 0.0, 0), H(68, 0.03, math.radians(-45), math.radians(3)), H(91, 0.0, 0)])
reset_tx(mesh_s, (0, 0, 0))
push_clip(mesh_s, "Sentinel_Fire", 24, [
    H(1, 0.0), H(4, 0.0, 0, math.radians(-8), 0, 0.10, (1.12, 0.9, 1.12)),
    H(9, 0.02, 0, math.radians(3), 0, -0.02, (0.97, 1.03, 0.97)), H(16, 0.0, 0, 0, 0, 0, (1, 1, 1)), H(25, 0.0)])
reset_tx(mesh_s, (0, 0, 0))

# --- tri counts
for o in list(props.objects) + list(char.objects):
    print("TRIS", o.name, tri_count(o))
sc.frame_start = 1; sc.frame_end = 91

bpy.ops.wm.save_as_mainfile(filepath=ROOT + r"\MECH.blend")
print("SAVED")




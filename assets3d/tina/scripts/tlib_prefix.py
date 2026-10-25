"""Tina-specific geometry builders (hair cards, eyes, lashes, headset, buttons, pin, seam ribbon) + atlas layout."""
import sys, math
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
import bpy, bmesh, numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import mesh_utils as mu

# ---- atlas layout (u, v) -----------------------------------------------------------------
MAIN = (0.0, 0.2, 0.8, 1.0)       # packed skin/clothes
HAIR = (0.8, 0.2, 1.0, 1.0)       # hair cards (4 variants side by side)
LASH = (0.0, 0.0, 0.4, 0.1)
EYE = (0.4, 0.0, 0.6, 0.2)
HARD = (0.6, 0.0, 0.8, 0.1)       # flat colour cells for hardware: 4 cells of 0.05 wide
CELL_BLACK = (0.625, 0.05)        # centre uv of cells
CELL_METAL = (0.675, 0.05)
CELL_NAVY = (0.725, 0.05)
CELL_BRASS = (0.775, 0.05)

EYE_R = 0.0125
EYE_C = {"L": Vector((0.0320, -0.1130, 1.4890)), "R": Vector((-0.0320, -0.1130, 1.4890))}


def make_obj(name, verts, faces, uvs=None, collection=None):
    """verts: list of xyz, faces: list of index tuples, uvs: list (per face) of list of (u,v) per corner or None."""
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    bm.verts.ensure_lookup_table()
    uvl = bm.loops.layers.uv.new("UVMap")
    for fi, f in enumerate(faces):
        try:
            face = bm.faces.new([bv[i] for i in f])
        except ValueError:
            continue
        if uvs is not None:
            for l, uv in zip(face.loops, uvs[fi]):
                l[uvl].uv = uv
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def flat_uv(ob, cell):
    uvl = ob.data.uv_layers.active or ob.data.uv_layers.new(name="UVMap")
    a = np.tile(np.array(cell, dtype=np.float32), (len(uvl.data), 1))
    uvl.data.foreach_set("uv", a.ravel())


def tube(name, pts, radius, sides=6, cap=True, cell=CELL_BLACK, radii=None):
    verts, faces = [], []
    pts = [Vector(p) for p in pts]
    n = len(pts)
    prev = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        a = t.cross(ref).normalized(); b = t.cross(a).normalized()
        r = radii[i] if radii else radius
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            verts.append(p + (a * math.cos(ang) + b * math.sin(ang)) * r)
    for i in range(n - 1):
        for s in range(sides):
            a0 = i * sides + s; a1 = i * sides + (s + 1) % sides
            b0 = (i + 1) * sides + s; b1 = (i + 1) * sides + (s + 1) % sides
            faces.append((a0, a1, b1, b0))
    if cap:
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple(range((n - 1) * sides, n * sides)))
    ob = make_obj(name, verts, faces)
    flat_uv(ob, cell)
    return ob


def disc(name, center, normal, radius, thick, sides=10, cell=CELL_METAL):
    n = Vector(normal).normalized()
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    a = n.cross(ref).normalized(); b = n.cross(a).normalized()
    c = Vector(center)
    verts = []
    for k in (0, 1):
        for s in range(sides):
            ang = 2 * math.pi * s / sides
            verts.append(c + n * thick * k + (a * math.cos(ang) + b * math.sin(ang)) * radius)
    faces = [tuple(reversed(range(sides))), tuple(range(sides, 2 * sides))]
    for s in range(sides):
        faces.append((s, (s + 1) % sides, sides + (s + 1) % sides, sides + s))
    ob = make_obj(name, verts, faces)
    flat_uv(ob, cell)
    return ob


def lod_from(lo, target, name, keep_face=False, delimit=('UV',)):
    """Copy a packed LOD0 piece and collapse-decimate it to `target` tris (UV islands preserved)."""
    ob = mu.copy_object(lo, name)
    if mu.tri_count(ob) <= target:
        return ob
    if keep_face:
        vg = ob.vertex_groups.new(name="_keep")
        co = np.array([v.co[:] for v in ob.data.vertices])
        w = np.zeros(len(co))
        w[(co[:, 1] < -0.02) & (co[:, 2] > 1.40) & (np.abs(co[:, 0]) < 0.1)] = 1.0
        w[np.abs(co[:, 0]) > 0.3] = 0.35
        for i in np.nonzero(w > 0)[0]:
            vg.add([int(i)], float(w[i]), 'REPLACE')
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    ratio = target / mu.tri_count(ob)
    for it in range(5):
        m = ob.modifiers.new("dec", 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = float(np.clip(ratio, 0.02, 1.0))
        m.use_collapse_triangulate = True
        if delimit and it < 3:
            m.delimit = set(delimit)
        if keep_face:
            m.vertex_group = "_keep"
            m.vertex_group_factor = 4.0
        bpy.ops.object.modifier_apply(modifier=m.name)
        cur = mu.tri_count(ob)
        if cur <= target:
            break
        ratio = target / cur * 0.97
    if ob.vertex_groups.get("_keep"):
        ob.vertex_groups.remove(ob.vertex_groups["_keep"])
    return ob


def ray_surface(obj, origin, direction=(0, 1, 0)):
    bvh = _bvh(obj)
    hit = bvh.ray_cast(Vector(origin), Vector(direction), 2.0)
    return hit[0], hit[1]


def build_buttons(blazer_hi, lod=0):
    if lod >= 2:
        return None
    parts = []
    for z in (1.075, 1.015):
        p, n = ray_surface(blazer_hi, (0.0, -0.6, z))
        if p is None:
            continue
        parts.append(disc("btn", p + n * 0.0005, n, 0.0105, 0.0042, 10 if lod == 0 else 6, CELL_NAVY))
    ob = mu.join(parts, "Tina_Buttons_L%d" % lod)
    mu.set_group_weight(ob, "mixamorig:Spine1", 1.0)
    return ob


def build_pin(blazer_hi, lod=0):
    p, n = ray_surface(blazer_hi, (0.092, -0.6, 1.262))
    ob = disc("Tina_PairPin_L%d" % lod, p + n * 0.0004, n, 0.0085, 0.0030, 10 if lod == 0 else 6, CELL_METAL)
    mu.set_group_weight(ob, "mixamorig:Spine2", 1.0)
    return ob


SEAM_CTRL = [(0.062, -0.108, 1.526), (0.071, -0.085, 1.506), (0.074, -0.062, 1.470), (0.069, -0.050, 1.432),
             (0.060, -0.062, 1.397), (0.046, -0.105, 1.372), (0.024, -0.135, 1.360), (0.004, -0.146, 1.357)]


def _catmull(pts, per):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def build_seam(skin_obj, lod=0):
    """Glowing jaw+temple ribbon hugging the given skin mesh (her left side, +X)."""
    per = {0: 6, 1: 3, 2: 2}[lod]
    width = {0: 0.0034, 1: 0.0042, 2: 0.0055}[lod]
    lift = {0: 0.0012, 1: 0.0020, 2: 0.0030}[lod]
    ctrl = _catmull([Vector(c) for c in SEAM_CTRL], per)
    bm = bmesh.new(); bm.from_mesh(skin_obj.data, use_shape_key=False)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bvh = BVHTree.FromBMesh(bm)
    pts = []
    for c in ctrl:
        loc, nor, idx, d = bvh.find_nearest(c)
        pts.append((loc, nor))
    bm.free()
    verts, faces = [], []
    n = len(pts)
    for i, (p, nr) in enumerate(pts):
        tg = (pts[min(i + 1, n - 1)][0] - pts[max(i - 1, 0)][0]).normalized()
        w = tg.cross(nr).normalized() * width * 0.5
        verts += [p - w + nr * lift, p + w + nr * lift]
    for i in range(n - 1):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
        faces.append((a, c, b, d) if False else (a, b, c, d))
    ob = make_obj("Tina_Seam_L%d" % lod, verts, faces)
    flat_uv(ob, CELL_NAVY)
    mu.transfer_vertex_groups(skin_obj, ob)
    # ribbon winding: make normals point away from the skin (check against the skin normal)
    me = ob.data
    me.update()
    flip = []
    for p in me.polygons:
        loc, nor, idx, d = _bvh_cache(skin_obj).find_nearest(p.center)
        if loc is not None and p.normal.dot((p.center - loc)) < 0 and p.normal.dot(nor) < 0:
            flip.append(p.index)
    if len(flip) > len(me.polygons) / 2:
        bm2 = bmesh.new(); bm2.from_mesh(me)
        bmesh.ops.reverse_faces(bm2, faces=bm2.faces[:])
        bm2.to_mesh(me); bm2.free()
    return ob


_BVH = {}
def _bvh_cache(obj):
    k = obj.name
    _BVH[k] = _bvh(obj)
    return _BVH[k]


# ---- skull fit ---------------------------------------------------------------------------
def skull_info(skin_hi):
    co = np.array([v.co[:] for v in skin_hi.data.vertices])
    h = co[(co[:, 2] > 1.46)]
    lo, hi = h.min(0), h.max(0)
    return {"top": float(co[:, 2].max()), "ymin": float(h[:, 1].min()), "ymax": float(h[:, 1].max()),
            "xmax": float(h[:, 0].max())}


def _bvh(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data, use_shape_key=False)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bvh = BVHTree.FromBMesh(bm); bm.free()
    return bvh


def build_hair(skin_hi, lod=0, seed=7):
    """Hair cards over the skull gathered into a low bun. Returns one object (UV in HAIR rect)."""
    rng = np.random.default_rng(seed)
    bvh = _bvh(skin_hi)
    info = skull_info(skin_hi)
    C = Vector((0.0, (info["ymin"] + info["ymax"]) * 0.5 + 0.005, 1.505))
    BUN_DIR = Vector((0.0, 0.85, -0.25)).normalized()
    cfg = {0: dict(n1=54, n2=26, segs=6), 1: dict(n1=30, n2=12, segs=4), 2: dict(n1=14, n2=0, segs=3)}[lod]
    verts, faces, uvs = [], [], []

    def surf(d):
        hit = bvh.ray_cast(C, d, 1.0)
        if hit[0] is None:
            return C + d * 0.095, d
        return hit[0], hit[1]

    def add_card(start_dir, width, off0, off1, var, bias_up, segs):
        d0 = start_dir.normalized()
        pts = []
        for i in range(segs + 1):
            t = i / segs
            d = (d0 * (1 - t) + BUN_DIR * t + Vector((0, 0, 1)) * (math.sin(math.pi * t) * bias_up)).normalized()
            p, n = surf(d)
            off = off0 + (off1 - off0) * math.sin(math.pi * min(1.0, t * 1.0)) ** 0.7
            if i == segs:
                off = 0.014
            pts.append((p + n * off, n))
        base = len(verts)
        for i, (p, n) in enumerate(pts):
            tg = (pts[min(i + 1, segs)][0] - pts[max(i - 1, 0)][0]).normalized()
            w = tg.cross(n).normalized() * (width * 0.5 * (1.0 - 0.45 * (i / segs) ** 2))
            verts.append(p - w); verts.append(p + w)
        u0 = HAIR[0] + (HAIR[2] - HAIR[0]) * (var / 4.0)
        u1 = HAIR[0] + (HAIR[2] - HAIR[0]) * ((var + 1) / 4.0)
        for i in range(segs):
            a, b, c, d = base + 2 * i, base + 2 * i + 1, base + 2 * i + 3, base + 2 * i + 2
            faces.append((a, b, c, d))
            va = HAIR[1] + (HAIR[3] - HAIR[1]) * (i / segs)
            vb = HAIR[1] + (HAIR[3] - HAIR[1]) * ((i + 1) / segs)
            uvs.append([(u0, va), (u1, va), (u1, vb), (u0, vb)])

    # hairline ring: azimuth a (0 = front, pi = back), skip the bun side (|a| > 2.5)
    for k in range(cfg["n1"]):
        a = -2.55 + 5.1 * (k + rng.uniform(-0.2, 0.2)) / (cfg["n1"] - 1)
        front = max(0.0, math.cos(a))
        el = 0.50 - 0.18 * (1 - front) + rng.uniform(-0.03, 0.03)       # elevation of the hairline (rad above horizontal)
        d0 = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
        d0 = Vector((d0.x, d0.y, d0.z - 0.0))
        add_card(d0, rng.uniform(0.030, 0.040), 0.004, 0.011, rng.integers(0, 4), 0.55, cfg["segs"])
    for k in range(cfg["n2"]):
        a = -2.2 + 4.4 * (k + rng.uniform(-0.2, 0.2)) / max(1, cfg["n2"] - 1)
        el = 0.75 + rng.uniform(-0.05, 0.05)
        d0 = Vector((math.sin(a) * math.cos(el), -math.cos(a) * math.cos(el), math.sin(el)))
        add_card(d0, rng.uniform(0.032, 0.042), 0.010, 0.017, rng.integers(0, 4), 0.35, cfg["segs"])
    hair = make_obj("Tina_Hair_L%d" % lod, verts, faces, uvs)

    # bun (low torus-ish blob)
    hitp, hitn = surf(BUN_DIR)
    bc = hitp + hitn * 0.016
    R, r = 0.018, 0.022
    ns, nt = (12, 6) if lod == 0 else ((8, 5) if lod == 1 else (6, 4))
    bverts, bfaces, buv = [], [], []
    for i in range(ns):
        for j in range(nt):
            th = 2 * math.pi * i / ns
            ph = 2 * math.pi * j / nt
            # torus around the Y axis (ring faces backwards)
            cx = math.cos(th) * R; cz = math.sin(th) * R
            nx = math.cos(th); nz = math.sin(th)
            px = cx + nx * math.cos(ph) * r
            pz = cz + nz * math.cos(ph) * r
            py = math.sin(ph) * r * 1.1
            bverts.append(Vector((bc.x + px, bc.y + py, bc.z + pz)))
    for i in range(ns):
        for j in range(nt):
            a = i * nt + j; b = i * nt + (j + 1) % nt
            c = ((i + 1) % ns) * nt + (j + 1) % nt; d = ((i + 1) % ns) * nt + j
            bfaces.append((a, b, c, d))
            u0 = HAIR[0] + (HAIR[2] - HAIR[0]) * (j / nt) * 0.25 + 0.0
            u1 = HAIR[0] + (HAIR[2] - HAIR[0]) * ((j + 1) / nt) * 0.25
            v0 = HAIR[1] + (HAIR[3] - HAIR[1]) * (i / ns)
            v1 = HAIR[1] + (HAIR[3] - HAIR[1]) * ((i + 1) / ns)
            buv.append([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    bun = make_obj("Tina_Bun_L%d" % lod, bverts, bfaces, buv)
    # fill the torus hole a little with a flattened sphere? keep it simple: leave as torus
    ob = mu.join([hair, bun], "Tina_HairAll_L%d" % lod)
    mu.set_group_weight(ob, "mixamorig:Head", 1.0)
    return ob


def build_eyes(lod=0):
    objs = []
    seg, rings = {0: (12, 8), 1: (10, 6), 2: (8, 5)}[lod]
    for side in ("L", "R"):
        c = EYE_C[side]
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=EYE_R)
        # rotate so the pole faces -Y (front)
        bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
        uvl = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            for l in f.loops:
                p = l.vert.co
                u = 0.5 + p.x / (2 * EYE_R)
                v = 0.5 + p.z / (2 * EYE_R)
                l[uvl].uv = (EYE[0] + u * (EYE[2] - EYE[0]), EYE[1] + v * (EYE[3] - EYE[1]))
        for v in bm.verts:
            v.co += c
        ob = mu.obj_from_bmesh(bm, "Tina_Eye%s_L%d" % (side, lod))
        objs.append(ob)
    ob = mu.join(objs, "Tina_EyesAll_L%d" % lod)
    mu.set_group_weight(ob, "mixamorig:Head", 1.0)
    return ob


def build_lashes(lod=0):
    objs = []
    segs = {0: 4, 1: 2, 2: 1}[lod]
    for side, sx in (("L", 1.0), ("R", -1.0)):
        c = EYE_C[side]
        verts, faces, uvs = [], [], []
        # upper-lid arc just in front of the eyeball: x from inner to outer corner
        for i in range(segs + 1):
            t = i / segs
            x = sx * (0.0135 + 0.034 * t)          # inner (near nose) -> outer
            arc = math.sin(math.pi * (0.1 + 0.8 * t))
            y = -0.1300 - 0.0040 * (1 - arc)
            z = 1.4885 + 0.0060 * arc
            root = Vector((x, y, z)); out_dir = Vector((0.10 * sx * t, -0.55, 0.85)).normalized()
            tip = root + out_dir * (0.0075 + 0.003 * t)
            verts += [root, tip]
        for i in range(segs):
            a, b, c2, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
            faces.append((a, b, c2, d) if sx > 0 else (d, c2, b, a))
            u0 = LASH[0] + (LASH[2] - LASH[0]) * (i / segs)
            u1 = LASH[0] + (LASH[2] - LASH[0]) * ((i + 1) / segs)
            uvs.append([(u0, LASH[1]), (u0, LASH[3]), (u1, LASH[3]), (u1, LASH[1])] if sx > 0 else
                       [(u1, LASH[1]), (u1, LASH[3]), (u0, LASH[3]), (u0, LASH[1])])
        objs.append(make_obj("Tina_Lash%s_L%d" % (side, lod), verts, faces, uvs))
    ob = mu.join(objs, "Tina_LashesAll_L%d" % lod)
    mu.set_group_weight(ob, "mixamorig:Head", 1.0)
    return ob


def build_headset(lod=0):
    """slim single-ear headset: thin band over the head, ear cup on her left, boom mic to the mouth corner."""
    parts = []
    sides = 6 if lod == 0 else 4
    n = {0: 12, 1: 8, 2: 5}[lod]
    # band: from left ear over the top to right ear, outside hair thickness
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n
        r = 0.098
        pts.append(Vector((math.cos(a) * r, -0.040 + 0.0, 1.488 + math.sin(a) * 0.118)))
    pts = [Vector((p.x, p.y, p.z)) for p in pts]
    pts = [Vector((p.x * 1.0, p.y, p.z)) for p in pts]
    # left end at +x
    band = tube("band", pts, 0.0028, sides, True, CELL_BLACK)
    parts.append(band)
    cup = disc("cup", (0.082, -0.034, 1.480), (1, 0, 0), 0.020, 0.012, 12 if lod == 0 else 8, CELL_BLACK)
    parts.append(cup)
    if lod < 2:
        cup2 = disc("cup2", (0.0932, -0.034, 1.480), (1, 0, 0), 0.0125, 0.003, 8, CELL_METAL)
        parts.append(cup2)
    # boom: from the cup, down and forward along the cheek to just in front of the mouth corner
    bp = [Vector((0.088, -0.034, 1.470)), Vector((0.093, -0.060, 1.448)), Vector((0.088, -0.095, 1.425)),
          Vector((0.070, -0.128, 1.408)), Vector((0.040, -0.150, 1.398))]
    boom = tube("boom", bp, 0.0016, 4 if lod else 5, True, CELL_BLACK)
    parts.append(boom)
    tipb = disc("miccap", (0.040, -0.150, 1.398), (-0.55, -0.8, -0.1), 0.0045, 0.010, 8 if lod < 2 else 6, CELL_BLACK)
    parts.append(tipb)
    ob = mu.join(parts, "Tina_Headset_L%d" % lod)
    mu.set_group_weight(ob, "mixamorig:Head", 1.0)
    return ob



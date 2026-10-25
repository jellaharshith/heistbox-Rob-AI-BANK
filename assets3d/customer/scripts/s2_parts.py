# Stage 2: build HI shells and LO parts from the full-res body. Run: blender -b stage1.blend -P s2_parts.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import random
random.seed(7); np.random.seed(7)

for n in ("Cube", "Camera", "Light"):
    if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
bm = bpy.data.objects["Body_full"]; rig = bpy.data.objects["Armature_Customer"]
M0 = bm.matrix_world.copy()
bm.parent = None; bm.matrix_world = Matrix.Identity(4)
me = bm.data
nv = len(me.vertices)
co = get_co(me)
nrm = np.empty(nv * 3); me.vertex_normals.foreach_get('vector', nrm); nrm = nrm.reshape(-1, 3)
bones = [b.name for b in rig.data.bones]
short = [b.split(":")[1] for b in bones]
bidx = {b: i for i, b in enumerate(bones)}
vgname = {vg.index: vg.name for vg in bm.vertex_groups}
W = np.zeros((nv, len(bones)))
attrs = {k: np.zeros(nv) for k in ("lips", "ears", "fingernails", "body", "scalp")}
for v in me.vertices:
    for g in v.groups:
        n = vgname[g.group]
        if n in bidx: W[v.index, bidx[n]] = g.weight
        elif n in attrs: attrs[n][v.index] = g.weight
inbody = attrs["body"] > 0.5
dom = np.array([short[i] for i in W.argmax(1)])
hasw = W.sum(1) > 0.01
bh = {b.name.split(":")[1]: np.array(b.head_local) for b in rig.data.bones}
bt = {b.name.split(":")[1]: np.array(b.tail_local) for b in rig.data.bones}
z = co[:, 2]
polys = [tuple(p.vertices) for p in me.polygons]
loops_uv = me.uv_layers["UVMap"].uv
uvarr = np.empty(len(loops_uv) * 2); loops_uv.foreach_get('vector', uvarr); uvarr = uvarr.reshape(-1, 2)
pl = [p.loop_start for p in me.polygons]

def isin(names): return np.isin(dom, names)
LH, RH = [n for n in short if n.startswith("LeftHand")], [n for n in short if n.startswith("RightHand")]
handdom = isin(LH + RH)
def wdist(side):
    wr = bt[side + "ForeArm"]
    return np.linalg.norm(co - wr, axis=1)
near_wrist = np.zeros(nv, bool)
for side in ("Left", "Right"):
    near_wrist |= (wdist(side) < 0.07) & isin([side + "ForeArm"])
far_wrist = np.zeros(nv, bool)
for side in ("Left", "Right"):
    far_wrist |= (wdist(side) >= 0.035) & isin([side + "ForeArm"])

M_head = inbody & isin(["Head", "Neck"])
# fix pass: trim the skin well below the (tilted) jacket neckline so its ragged lower edge never shows over the collar
M_head &= (z > 1.545 + 0.35 * (co[:, 1] + 0.005) - 0.02)
M_hands = inbody & (handdom | near_wrist)
torso = ["Spine", "Spine1", "Spine2", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm"]
legs = ["Hips", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"]
JHEM = 0.93
M_jacket = inbody & ((isin(torso) | far_wrist | (isin(["Neck", "Head"]) & (z < 1.572)) |
                      (isin(["Hips", "LeftUpLeg", "RightUpLeg"]) & (z > JHEM))))
M_jeans = inbody & isin(legs) & (z <= 1.045) & (z >= 0.085)
M_shoes = inbody & (isin(["LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"]) |
                    (isin(["LeftLeg", "RightLeg"]) & (z < 0.09)))
M_shoes &= (z < 0.14)

def faces_of(mask):
    return [i for i, p in enumerate(polys) if all(mask[v] for v in p)]

def shell(name, mask, off, keep_uv=False):
    fids = faces_of(mask)
    used = sorted({v for i in fids for v in polys[i]})
    remap = {v: k for k, v in enumerate(used)}
    src = np.array(used)
    c = co[src] + nrm[src] * off[src][:, None]
    faces = [tuple(remap[v] for v in polys[i]) for i in fids]
    ob = new_obj(name, c, faces)
    ob["src"] = 1
    for k_, arr_ in attrs.items():
        a_ = ob.data.attributes.new(k_, "FLOAT", "POINT"); a_.data.foreach_set("value", arr_[src].astype(np.float32))
    uvs = None
    if keep_uv:
        uvs = [[uvarr[pl[i] + k] for k in range(len(polys[i]))] for i in fids]
    return ob, src, faces, uvs

coll_hi = bpy.data.collections.new("HI"); bpy.context.scene.collection.children.link(coll_hi)
coll_lo = bpy.data.collections.new("LO"); bpy.context.scene.collection.children.link(coll_lo)
def to_coll(ob, c):
    for cc in ob.users_collection: cc.objects.unlink(ob)
    c.objects.link(ob)

# ---------- offsets
wd = np.minimum(wdist("Left"), wdist("Right"))
off_jacket = 0.018 + 0.022 * smooth(z, 1.555, 1.60) * isin(["Neck"]) + 0.012 * smooth(z, 1.0, 0.93)
off_jacket = off_jacket + 0.012 * smooth(wd, 0.14, 0.04) * far_wrist + 0.016 * smooth(z, 1.46, 1.53)  # fix pass: thicker neck/shoulder area so skin never pokes through the collar
off_jeans = 0.010 + 0.012 * smooth(z, 0.35, 0.09)
off_shoes = 0.013 + 0.006 * isin(["LeftToeBase", "RightToeBase"])
off_zero = np.zeros(nv)

parts = {}
def build(name, mask, off, target, keep_uv=False, dec_group=None, sole=False):
    ob, src, faces, uvs = shell("H_" + name, mask, off, keep_uv)
    if sole:
        for v in ob.data.vertices:
            if v.co.z < 0.05: v.co.z -= 0.015 * (1 - min(1, max(0, (v.co.z - 0.02) / 0.03)))
    to_coll(ob, coll_hi)
    parts[name] = dict(hi=ob, src=src, faces=faces, uvs=uvs)
    return ob

hs = build("skin_head", M_head, off_zero, 0, keep_uv=True)
hh = build("skin_hands", M_hands, off_zero, 0, keep_uv=True)
hj = build("jacket", M_jacket, off_jacket, 0)
hn = build("jeans", M_jeans, off_jeans, 0)
ho = build("shoes", M_shoes, off_shoes, 0, sole=True)
for k, p in parts.items():
    print("HI", k, len(p["hi"].data.vertices), tri_count(p["hi"].data))

# ---------- fix pass: clean planar (tilted) collar cut instead of the ragged dominant-bone / z threshold edge
def cut_collar(name, y0=-0.005, z0=1.545, k=0.35):
    global W
    p = parts[name]; ob = p["hi"]; me_ = ob.data
    S0 = Source(get_co(me_), p["faces"]); W0 = W[p["src"]]
    bmx = bmesh.new(); bmx.from_mesh(me_)
    bmesh.ops.bisect_plane(bmx, geom=list(bmx.verts) + list(bmx.edges) + list(bmx.faces), dist=1e-6,
                           plane_co=(0, y0, z0), plane_no=(0, -k, 1), clear_outer=True)
    bmx.to_mesh(me_); bmx.free()
    me_.update()
    c_ = get_co(me_)
    Wn = S0.interp(c_, [W0])[0]
    base = W.shape[0]
    W = np.vstack([W, Wn])
    p["src"] = np.arange(base, base + len(c_))
    p["faces"] = [tuple(pp.vertices) for pp in me_.polygons]
    print("COLLAR cut", name, len(c_), "verts")
cut_collar("jacket")

# ---------- smooth shells (remove anatomical bumps)
def smooth_shell(ob, iters, lam=0.5):
    bmx = bmesh.new(); bmx.from_mesh(ob.data); bmx.verts.ensure_lookup_table()
    fixed = {v.index for v in bmx.verts if any(e.is_boundary for e in v.link_edges)}
    pts = np.array([v.co[:] for v in bmx.verts])
    nb = [[e.other_vert(v).index for e in v.link_edges] for v in bmx.verts]
    for _ in range(iters):
        new = pts.copy()
        for i, n in enumerate(nb):
            if i in fixed or not n: continue
            new[i] = pts[i] * (1 - lam) + pts[n].mean(0) * lam
        pts = new
    for v, p in zip(bmx.verts, pts): v.co = p
    bmx.to_mesh(ob.data); bmx.free()
smooth_shell(parts["jacket"]["hi"], 22)
smooth_shell(parts["jeans"]["hi"], 4)
# ---------- high-res fabric detail (displacement) for normal bake'
def add_displace(ob, scale, strength, name):
    tex = bpy.data.textures.new(name, 'CLOUDS'); tex.noise_scale = scale; tex.noise_depth = 2
    m = ob.modifiers.new(name, 'DISPLACE'); m.texture = tex; m.strength = strength; m.mid_level = 0.5
    m.texture_coords = 'OBJECT'; m.texture_coords_object = None
    return m
# subdivide first so the displacement has geometry to work with
for k in ("jacket", "jeans"):
    ob = parts[k]["hi"]
    sub = ob.modifiers.new("sub", 'SUBSURF'); sub.levels = 1; sub.render_levels = 1; sub.subdivision_type = 'SIMPLE'
    add_displace(ob, 0.06 if k == "jacket" else 0.045, 0.006 if k == "jacket" else 0.005, "wr_" + k)
    add_displace(ob, 0.012, 0.0012, "fw_" + k)

# ---------- LO parts: decimate
def lo_from(name, target, keepw=None):
    p = parts[name]
    ob = p["hi"]
    # mesh without modifiers (base mesh) for decimation
    tmp = bpy.data.objects.new("tmp", ob.data.copy()); bpy.context.scene.collection.objects.link(tmp)
    if keepw is not None:
        vg = tmp.vertex_groups.new(name="keep")
        for i, w in enumerate(keepw): vg.add([i], float(w), 'REPLACE')
    m = decimate_to(tmp, target, vgroup="keep" if keepw is not None else None, factor=1.0)
    bpy.data.objects.remove(tmp)
    lo = bpy.data.objects.new("L_" + name, m); coll_lo.objects.link(lo)
    p["lo"] = lo
    return lo

# face-protect weights for head
hsrc = parts["skin_head"]["src"]
yc, ez = -0.024, None
def eye_info(side):
    gi = bm.vertex_groups["helper-%s-eye" % side].index
    pts = np.array([v.co[:] for v in me.vertices if any(g.group == gi and g.weight > .5 for g in v.groups)])
    return (pts.min(0) + pts.max(0)) / 2, (pts.max(0) - pts.min(0)) / 2
EL, ELr = eye_info("l"); ER, ERr = eye_info("r")
print("EYE", EL, ELr, ER, "ZMIN", co[inbody,2].min())
ez = EL[2]
hc = co[hsrc]
face = smooth(-(hc[:, 1] - yc), 0.03, 0.07) * smooth(1.0 - np.abs(hc[:, 2] - (ez - 0.035)) / 0.1, 0.0, 0.3)
keepw_head = 0.25 + 0.75 * face
keepw_head = np.where(hc[:, 2] < 1.56, 0.3, keepw_head)
lo_from("skin_head", 3300, keepw_head)
lo_from("skin_hands", 900)
def bweights(name):
    bmx = bmesh.new(); bmx.from_mesh(parts[name]["hi"].data); bmx.verts.ensure_lookup_table()
    w = np.array([1.0 if any(e.is_boundary for e in v.link_edges) else 0.15 for v in bmx.verts]); bmx.free()
    return w
lo_from("jacket", 3700, bweights("jacket"))
lo_from("jeans", 2300, bweights("jeans"))
lo_from("shoes", 900, bweights("shoes"))
for k, p in list(parts.items()):
    print("LO", k, len(p["lo"].data.vertices), tri_count(p["lo"].data))

# ---------- skin LO: UV by per-loop transfer from MPFB UVs
def transfer_uv(k):
    p = parts[k]
    hi = p["hi"].data
    src_co = get_co(hi)
    faces = p["faces"]
    # UV islands of the HI shell (faces sharing a vertex with identical UV are connected)
    par = list(range(len(faces)))
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    keymap = {}
    for fi, f in enumerate(faces):
        for ci, v in enumerate(f):
            u = p["uvs"][fi][ci]
            key = (v, round(float(u[0]), 4), round(float(u[1]), 4))
            if key in keymap: par[find(fi)] = find(keymap[key])
            else: keymap[key] = fi
    isl = np.array([find(i) for i in range(len(faces))])
    S_all = Source(src_co, faces)
    tri_face = []
    for fi, f in enumerate(faces):
        for i in range(1, len(f) - 1): tri_face.append(fi)
    tri_face = np.array(tri_face)
    tri_uv = []
    for fi, f in enumerate(faces):
        for i in range(1, len(f) - 1):
            tri_uv.append((p["uvs"][fi][0], p["uvs"][fi][i], p["uvs"][fi][i + 1]))
    tri_uv = np.array(tri_uv)
    srcs = {}
    def island_source(iid):
        if iid not in srcs:
            idx = np.where(isl == iid)[0]
            S = Source(src_co, [faces[i] for i in idx])
            # tri -> uv for this island (same fan order)
            tuv = []
            for i in idx:
                f = faces[i]
                for j in range(1, len(f) - 1):
                    tuv.append((p["uvs"][i][0], p["uvs"][i][j], p["uvs"][i][j + 1]))
            srcs[iid] = (S, np.array(tuv))
        return srcs[iid]
    lo = p["lo"].data
    lco = get_co(lo)
    uvl = lo.uv_layers.new(name="UVMap")
    for poly in lo.polygons:
        cen = np.mean([lco[v] for v in poly.vertices], axis=0)
        (a_, b_, c_), w_, tid = S_all.query(cen)
        iid = isl[tri_face[tid]]
        S, tuv = island_source(iid)
        for li in poly.loop_indices:
            v = lo.loops[li].vertex_index
            (a, b, c), w, t2 = S.query(lco[v])
            uvl.data[li].uv = tuple(tuv[t2][0] * w[0] + tuv[t2][1] * w[1] + tuv[t2][2] * w[2])
for k in ("skin_head", "skin_hands"):
    lo = parts[k]["lo"]; lo.data.uv_layers.new(name="UVMap")
    select_only(lo)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")

# ---------- smart-project cloth LO parts
for k in ("jacket", "jeans", "shoes"):
    lo = parts[k]["lo"]
    select_only(lo)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(80 if k != 'shoes' else 89), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')

# ---------- hair cap, hair cards, eyes, lashes (LO only, weighted 100% to Head)
RH_ = 0.095
tt = np.clip((yc - co[:, 1]) / RH_, -1, 1)
zmin_h = ez + 0.045 + 0.03 * np.maximum(tt, 0) - 0.09 * np.maximum(-tt, 0)
M_cap = inbody & isin(["Head"]) & (z > zmin_h)
off_cap = 0.011 + 0.010 * smooth(z, ez + 0.06, ez + 0.12)
cap_hi, csrc, cfaces, _ = shell("H_hair", M_cap, off_cap)
to_coll(cap_hi, coll_hi); cap_hi.hide_render = True
tmp = bpy.data.objects.new("tmp", cap_hi.data.copy()); bpy.context.scene.collection.objects.link(tmp)
m = decimate_to(tmp, 420); bpy.data.objects.remove(tmp)
cap = bpy.data.objects.new("L_hair_cap", m); coll_lo.objects.link(cap)
parts["hair_cap"] = dict(lo=cap, hi=None)
ccap = get_co(cap.data)
cap.data.uv_layers.new(name="UVMap")
select_only(cap)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=0.004, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
uvh = cap.data.uv_layers.new(name="UVHair")
for poly in cap.data.polygons:
    for li in poly.loop_indices:
        c_ = ccap[cap.data.loops[li].vertex_index]
        uvh.data[li].uv = ((c_[0] + 0.1) / 0.2, (c_[1] - yc + 0.1) / 0.2)
cap.data.uv_layers.active_index = 0
names = [u.name for u in cap.data.uv_layers]
print("CAPUV", names)

# cards along the cap boundary
bmc = bmesh.new(); bmc.from_mesh(cap.data); bmc.verts.ensure_lookup_table(); bmc.normal_update()
bverts = [v for v in bmc.verts if any(e.is_boundary for e in v.link_edges)]
cverts, cfaces2, cuv0, cuv1 = [], [], [], []
rng = random.Random(3)
def tile_uv(var, u, v):   # variant tile in atlas strip
    return (0.1 * var + 0.1 * u * 0.96 + 0.002, 0.89 + 0.11 * (1 - v) * 0.96 + 0.002)
for v in bverts:
    p = np.array(v.co); n = np.array(v.normal); n = n / (np.linalg.norm(n) + 1e-9)
    t_ = np.clip((yc - p[1]) / RH_, -1, 1)
    L = (0.032 + rng.random() * 0.018) if t_ > 0.35 else ((0.05 + rng.random() * 0.025) if t_ < -0.2 else 0.03 + rng.random() * 0.02)
    d = np.array([0, 0, -1.0]) + n * 0.45; d /= np.linalg.norm(d)
    tang = np.cross(np.array([0, 0, -1.0]), n)
    if np.linalg.norm(tang) < 1e-6: tang = np.array([1.0, 0, 0])
    tang /= np.linalg.norm(tang)
    w = 0.03
    var = rng.randrange(5)
    base = len(cverts)
    rows = [(0.0, w / 2, 0.0), (0.5, w * 0.5, 0.004), (1.0, w * 0.5, 0.006)]
    for k, (f, hw, push) in enumerate(rows):
        c0 = p + d * L * f + n * push
        cverts.append(c0 - tang * hw); cverts.append(c0 + tang * hw)
    for k in range(2):
        a = base + 2 * k
        cfaces2.append((a, a + 1, a + 3, a + 2))
    var_ = var
    for k, f in enumerate((0.0, 0.5, 1.0)):
        cuv1.append(tile_uv(var_, 0, f)); cuv1.append(tile_uv(var_, 1, f))
bmc.free()
cards = new_obj("L_hair_cards", np.array(cverts), cfaces2, coll_lo)
cm = cards.data
for nm, arr in (("UVMap", cuv1), ("UVHair", cuv1)):
    layer = cm.uv_layers.new(name=nm)
    for poly in cm.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = arr[cm.loops[li].vertex_index]
# UVHair for cards = region-local coords (U, V-0.89): applied after final pack (s3); mark cards UV as fixed
cards["fixed_uv"] = 1
parts["hair_cards"] = dict(lo=cards, hi=None)

# eyes
def make_eye(name, c, r):
    bmx = bmesh.new()
    bmesh.ops.create_uvsphere(bmx, u_segments=12, v_segments=8, radius=r)
    for v in bmx.verts: v.co.y, v.co.z = v.co.z, v.co.y  # poles toward Y -> irrelevant
    bmesh.ops.rotate(bmx, verts=bmx.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    dele = [v for v in bmx.verts if v.co.y > 0.25 * r]
    bmesh.ops.delete(bmx, geom=dele, context='VERTS')
    for v in bmx.verts: v.co += Vector(c)
    mme = bpy.data.meshes.new(name); bmx.to_mesh(mme); bmx.free()
    return mme
EYE_R = 0.0132
eyeL = make_eye("eyeL", EL, EYE_R); eyeR = make_eye("eyeR", ER, EYE_R)
eo = bpy.data.objects.new("L_eyes", eyeL); coll_lo.objects.link(eo)
eo2 = bpy.data.objects.new("tmpR", eyeR); coll_lo.objects.link(eo2)
select_only(eo2, eo); bpy.ops.object.join()
eo = bpy.context.view_layer.objects.active; eo.name = "L_eyes"
em = eo.data
for nm in ("UVMap", "UVHair"):
    lay = em.uv_layers.new(name=nm)
    for poly in em.polygons:
        for li in poly.loop_indices:
            p_ = em.vertices[em.loops[li].vertex_index].co
            cc = EL if p_.x > 0 else ER
            lay.data[li].uv = (0.5 + (p_.x - cc[0]) / (2 * EYE_R) * (1 if nm == "UVMap" else 1), 0.5 + (p_.z - cc[2]) / (2 * EYE_R))
em.polygons.foreach_set("use_smooth", [True] * len(em.polygons))
parts["eyes"] = dict(lo=eo, hi=None)

# lashes: one alpha strip per eye (single material), UV -> shared tile [0.5,0.75]x[0.89,1.0]
def lash_strip(name, c, side):
    N = 8
    verts, faces, uvs = [], [], []
    for i in range(N + 1):
        s = i / N
        dx = (s - 0.5) * 0.031
        ax = -0.0     # inner->outer direction handled by side
        x = c[0] + side * ((s - 0.5) * 0.031 + 0.0)
        arch = 0.0072 * (1 - (2 * s - 1) ** 2) + 0.0032 + 0.003 * max(0, s - 0.6)
        zb = c[2] + arch - 0.0006
        rr = EYE_R + 0.0012
        dxx = x - c[0]; dzz = zb - c[2]
        yb = c[1] - math.sqrt(max(rr * rr - dxx * dxx - dzz * dzz, 0.0))
        # lash extends up/out and forward
        out = np.array([side * (0.3 + 0.6 * s), -0.0, 1.0]); out /= np.linalg.norm(out)
        ln = 0.0062 + 0.0045 * s
        verts.append((x, yb, zb)); verts.append((x + out[0] * ln, yb - 0.0035, zb + out[2] * ln))
        # tile uv: u along strip (inner->outer = 0..1), v 0 base .. 1 tip
        u = s
        uvs.append((0.5 + 0.25 * u * 0.96 + 0.005, 0.89 + 0.002)); uvs.append((0.5 + 0.25 * u * 0.96 + 0.005, 0.89 + 0.11 * 0.96))
    for i in range(N):
        a = 2 * i
        faces.append((a, a + 2, a + 3, a + 1) if side > 0 else (a, a + 1, a + 3, a + 2))
    return verts, faces, uvs
lv, lf, luv = [], [], []
for c_, sd in ((EL, 1), (ER, -1)):
    v_, f_, u_ = lash_strip("l", c_, sd)
    base = len(lv); lv += v_; lf += [tuple(i + base for i in f) for f in f_]; luv += u_
lash = new_obj("L_lashes", np.array(lv), lf, coll_lo)
lm = lash.data
for nm in ("UVMap", "UVHair"):
    lay = lm.uv_layers.new(name=nm)
    for poly in lm.polygons:
        for li in poly.loop_indices:
            lay.data[li].uv = luv[lm.loops[li].vertex_index]
lash["fixed_uv"] = 1
parts["lashes"] = dict(lo=lash, hi=None)

# ensure UVHair exists on every LO part; hi-less parts get weights = Head
HEAD = bidx["mixamorig:Head"]
for k in ("hair_cap", "hair_cards", "eyes", "lashes"):
    lo = parts[k]["lo"]
    Wk = np.zeros((len(lo.data.vertices), len(bones))); Wk[:, HEAD] = 1.0
    parts[k]["W"] = Wk
for k, p in parts.items():
    me_ = p["lo"].data
    if "UVHair" not in me_.uv_layers: me_.uv_layers.new(name="UVHair")
    if "UVMap" not in me_.uv_layers: me_.uv_layers.new(name="UVMap")
    for poly in me_.polygons: poly.use_smooth = True

# ---------- per-vertex weights + masks onto LO via barycentric transfer from HI source
def lo_weights(k, extra=None):
    p = parts[k]
    S = Source(get_co(p["hi"].data), p["faces"])
    lco = get_co(p["lo"].data)
    arrs = [W[p["src"]]] + ([extra[k]] if extra and k in extra else [])
    res = S.interp(lco, arrs)
    p["W"] = res[0]
    return res
for k in list(parts):
    if parts[k]["hi"] is not None: lo_weights(k)

import pickle
pickle.dump(dict(W={k: parts[k]["W"] for k in parts}, EL=EL, ER=ER, ELr=ELr,
                 bones=bones, bh=bh, bt=bt), open(os.path.join(ROOT, "stage2_data.pkl"), "wb"))
# keep source arrays for shape-key transfer later
np.savez_compressed(os.path.join(ROOT, "stage2_src.npz"), src_head=parts["skin_head"]["src"])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "stage2.blend"))
print("DONE")












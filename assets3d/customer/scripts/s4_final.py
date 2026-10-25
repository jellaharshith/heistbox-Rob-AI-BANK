# Stage 4: assemble LOD0/1/2 skinned meshes with shape keys, final material, phone prop. Run: blender -b stage3.blend -P s4_final.py
import sys, os, pickle, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
O = bpy.data.objects
sc = bpy.context.scene
D = pickle.load(open(os.path.join(ROOT, "stage2_data.pkl"), "rb"))
srcnpz = np.load(os.path.join(ROOT, "stage2_src.npz"))
bones = D["bones"]; nb_ = len(bones)
ORDER = ["skin_head", "mouth", "skin_hands", "jacket", "jeans", "shoes", "hair_cap", "hair_cards", "eyes", "lashes"]
LOname = {"mouth": None, "skin_head": "L_skin_head", "skin_hands": "L_skin_hands", "jacket": "L_jacket", "jeans": "L_jeans", "shoes": "L_shoes",
          "hair_cap": "L_hair_cap", "hair_cards": "L_hair_cards", "eyes": "L_eyes", "lashes": "L_lashes"}

# ---------- face shape-key recipes (weights of MPFB unit targets)
U = lambda n: "u_" + n
RECIPES = {
 "viseme_sil": {},
 "viseme_PP": {"mouth-compression": 1.0},
 "viseme_FF": {"mouth-upward-retraction": 0.6, "mouth-open": 0.12},
 "viseme_TH": {"mouth-open": 0.25, "mouth-protusion": 0.35},
 "viseme_DD": {"mouth-open": 0.32, "mouth-upward-retraction": 0.2},
 "viseme_kk": {"mouth-open": 0.38},
 "viseme_CH": {"mouth-pursing": 0.55, "mouth-open": 0.22},
 "viseme_SS": {"mouth-retraction": 0.5, "mouth-corner-puller": 0.25, "mouth-open": 0.08},
 "viseme_nn": {"mouth-open": 0.16},
 "viseme_RR": {"mouth-pursing": 0.45, "mouth-open": 0.2},
 "viseme_aa": {"mouth-open": 0.85},
 "viseme_E": {"mouth-open": 0.3, "mouth-corner-puller": 0.55},
 "viseme_I": {"mouth-open": 0.2, "mouth-corner-puller": 0.45, "mouth-retraction": 0.3},
 "viseme_O": {"mouth-pursing": 0.8, "mouth-open": 0.38},
 "viseme_U": {"mouth-pursing": 1.0, "mouth-open": 0.1},
 "eyeBlinkLeft": {"eye-left-closure": 1.0},
 "eyeBlinkRight": {"eye-right-closure": 1.0},
 "mouthSmile": {"mouth-corner-puller": 1.0, "mouth-elevation": 0.35},
 "browUp": {"eyebrows-left-up": 1.0, "eyebrows-right-up": 1.0},
 "browDown": {"eyebrows-left-down": 1.0, "eyebrows-right-down": 1.0},
 "jawOpen": {"mouth-open": 1.0},
}
UNITS = sorted({k for r in RECIPES.values() for k in r})

body = O["Body_full"]
bkeys = body.data.shape_keys.key_blocks
basis = get_co(body.data)
src_head = srcnpz["src_head"]
unit_delta = {}
for u in UNITS:
    kb = bkeys[U(u)]
    a = np.empty(len(body.data.vertices) * 3); kb.data.foreach_get("co", a)
    unit_delta[u] = (a.reshape(-1, 3) - basis)[src_head]
hi_head = O["H_skin_head"]
hi_head_co = get_co(hi_head.data)
hi_faces = [tuple(p.vertices) for p in hi_head.data.polygons]
S_head = Source(hi_head_co, hi_faces)
stack = np.concatenate([unit_delta[u] for u in UNITS], axis=1)   # (n_hi, 3*len(units))

def face_deltas(points):
    """returns {key: (n,3)} for given points (world)"""
    r = S_head.interp(points, [stack])[0].reshape(len(points), len(UNITS), 3)
    out = {}
    for name, rec in RECIPES.items():
        d = np.zeros((len(points), 3))
        for un, w in rec.items(): d += w * r[:, UNITS.index(un), :]
        out[name] = d
    return out

# ---------- generic part data extraction
def part_data(name):
    ob = O[LOname[name]]; me = ob.data
    co = get_co(me)
    faces = [tuple(p.vertices) for p in me.polygons]
    loops_v = np.array([l.vertex_index for l in me.loops])
    uv = {}
    for ln in ("UVMap", "UVHair"):
        a = np.empty(len(me.loops) * 2); me.uv_layers[ln].data.foreach_get("uv", a); uv[ln] = a.reshape(-1, 2)
    return dict(co=co, faces=faces, uv=uv, W=D["W"][name], poly_loops=[(p.loop_start, p.loop_total) for p in me.polygons])

def combine(name, plist, rigobj=None):
    """plist: list of part dicts. returns object with mesh, groups, shape keys"""
    cos, faces, uv0, uv1, Ws, dl = [], [], [], [], [], {}
    off = 0
    loop_uv0, loop_uv1 = [], []
    for p in plist:
        cos.append(p["co"]); Ws.append(p["W"])
        for f in p["faces"]: faces.append(tuple(v + off for v in f))
        for (ls, lt) in p["poly_loops"]:
            loop_uv0.extend(p["uv"]["UVMap"][ls:ls + lt]); loop_uv1.extend(p["uv"]["UVHair"][ls:ls + lt])
        off += len(p["co"])
    co = np.concatenate(cos); W = np.concatenate(Ws)
    ob = new_obj(name, co, faces)
    me = ob.data
    for ln, arr in (("UVMap", loop_uv0), ("UVHair", loop_uv1)):
        lay = me.uv_layers.new(name=ln)
        lay.data.foreach_set("uv", np.array(arr, dtype=np.float32).ravel())
    for p_ in me.polygons: p_.use_smooth = True
    set_weights(ob, W, bones)
    return ob, co

def add_shape_keys(ob, co, faceverts_mask):
    """faceverts_mask: bool array of verts that receive face deltas"""
    idx = np.where(faceverts_mask)[0]
    dl = face_deltas(co[idx])
    ob.shape_key_add(name="Basis")
    for name in RECIPES:
        kb = ob.shape_key_add(name=name)
        arr = np.array(co, dtype=np.float64)
        arr[idx] += dl[name]
        kb.data.foreach_set("co", arr.astype(np.float32).ravel())
        kb.value = 0.0
        kb.slider_min = 0.0; kb.slider_max = 1.0

def make_mouth():
    """teeth (2 ribbons) + tongue + dark cavity dome; flat-colour tiles in the atlas top-right (painted in s3)."""
    verts, faces, ftile = [], [], []
    def add(vs, fs, tile):
        b = len(verts); verts.extend(vs)
        for f in fs: faces.append(tuple(i + b for i in f)); ftile.append(tile)
    def ribbon(ztop, h, t, ydelta, n=10, half=0.026, tile=0):
        xs = np.linspace(-half, half, n + 1)
        vs = []
        for x in xs:
            y = -0.1405 + 16.0 * x * x + ydelta
            prof = ((0, 0), (0, -h), (t, -h), (t, 0))
            for dy, dz in prof: vs.append((x, y + dy, ztop + dz))
        fs = []
        for i in range(n):
            for k in range(4):
                a = i * 4 + k; b = i * 4 + (k + 1) % 4
                fs.append((a, b, b + 4, a + 4))
        fs.append((3, 2, 1, 0)); e = n * 4; fs.append((e, e + 1, e + 2, e + 3))
        add(vs, fs, tile)
    ribbon(1.5785, 0.0075, 0.004, 0.0, tile=0)
    ribbon(1.5655, 0.0075, 0.004, 0.002, tile=0)
    # tongue: flattened ellipsoid
    def ellipsoid(c, r, nseg, nring, tile, inward=False, half=False):
        vs = []; fs = []
        rings = nring
        for j in range(rings + 1):
            ph = (math.pi if not half else math.pi / 2) * j / rings
            for i in range(nseg):
                th = 2 * math.pi * i / nseg
                if half: vs.append((c[0] + r[0] * math.sin(ph) * math.cos(th), c[1] + r[1] * math.cos(ph), c[2] + r[2] * math.sin(ph) * math.sin(th)))
                else: vs.append((c[0] + r[0] * math.sin(ph) * math.cos(th), c[1] + r[1] * math.cos(ph), c[2] + r[2] * math.sin(ph) * math.sin(th)))
        for j in range(rings):
            for i in range(nseg):
                a = j * nseg + i; b = j * nseg + (i + 1) % nseg
                f = (a, b, b + nseg, a + nseg)
                fs.append(f if inward else f[::-1])
        add(vs, fs, tile)
    ellipsoid((0, -0.113, 1.5545), (0.020, 0.026, 0.0065), 8, 4, 1)
    ellipsoid((0, -0.140, 1.565), (0.0285, 0.048, 0.0195), 10, 3, 2, inward=True, half=True)
    co = np.array(verts, dtype=np.float64)
    co[:, 2] += 0.0275   # lip slit of this mesh sits at z~1.598 (measured from jawOpen deltas + renders)
    tcen = [(0.8125, 0.945), (0.875, 0.945), (0.9375, 0.945)]
    uvl = []; pl = []
    for f, t_ in zip(faces, ftile):
        pl.append((len(uvl), len(f))); uvl.extend([tcen[t_]] * len(f))
    # triangulate-count check
    W_ = np.zeros((len(co), nb_)); W_[:, bones.index("mixamorig:Head")] = 1.0
    uvl = np.array(uvl)
    print("MOUTH tris", sum(len(f) - 2 for f in faces), "verts", len(co))
    return dict(co=co, faces=faces, uv={"UVMap": uvl, "UVHair": uvl.copy()}, W=W_, poly_loops=pl)

PD = {n: part_data(n) for n in ORDER if n != "mouth"}
PD["mouth"] = make_mouth()

# ---------- LOD0
lod0, co0 = combine("CHAR_Customer_LOD0", [PD[n] for n in ORDER])
mask0 = np.zeros(len(co0), bool)
o_ = 0
for n in ORDER:
    c = len(PD[n]["co"])
    if n in ("skin_head", "mouth", "lashes"): mask0[o_:o_ + c] = True
    o_ += c
add_shape_keys(lod0, co0, mask0)
print("LOD0 tris", tri_count(lod0.data), "verts", len(lod0.data.vertices))

# ---------- LOD1/2: per-part decimation of the LOD0 parts
def decimated_part(n, target, keep_all=False):
    src = PD[n]
    ob = O[LOname[n]]
    if n == "hair_cards":
        return None
    tmp = bpy.data.objects.new("tmp", ob.data.copy()); sc.collection.objects.link(tmp)
    me = decimate_to(tmp, target, symmetry=False)
    bpy.data.objects.remove(tmp)
    # weights by barycentric transfer from LOD0 part
    S = Source(src["co"], src["faces"])
    pts = get_co(me)
    Wn = S.interp(pts, [src["W"]])[0]
    faces = [tuple(p.vertices) for p in me.polygons]
    uv = {}
    for ln in ("UVMap", "UVHair"):
        if ln in me.uv_layers:
            a = np.empty(len(me.loops) * 2); me.uv_layers[ln].data.foreach_get("uv", a); uv[ln] = a.reshape(-1, 2)
        else: uv[ln] = np.zeros((len(me.loops), 2))
    d = dict(co=pts, faces=faces, uv=uv, W=Wn, poly_loops=[(p.loop_start, p.loop_total) for p in me.polygons])
    bpy.data.meshes.remove(me)
    return d

def cards_subset(k):
    p = PD["hair_cards"]; ncards = len(p["co"]) // 6
    keep = [i for i in range(ncards) if i % k == 0]
    co, W, faces, uvm, uvh, pl = [], [], [], [], [], []
    for new_i, i in enumerate(keep):
        co.append(p["co"][i * 6:(i + 1) * 6]); W.append(p["W"][i * 6:(i + 1) * 6])
        for f in range(2):
            fi = i * 2 + f
            faces.append(tuple(v - i * 6 + new_i * 6 for v in p["faces"][fi]))
            ls, lt = p["poly_loops"][fi]
            pl.append((len(uvm), lt)); uvm.extend(p["uv"]["UVMap"][ls:ls + lt]); uvh.extend(p["uv"]["UVHair"][ls:ls + lt])
    return dict(co=np.concatenate(co), W=np.concatenate(W), faces=faces, uv={"UVMap": np.array(uvm), "UVHair": np.array(uvh)}, poly_loops=pl)

LODS = {1: dict(skin_head=1500, skin_hands=480, jacket=2000, jeans=1150, shoes=450, hair_cap=250, eyes=100, cards=2),
        2: dict(skin_head=700, skin_hands=200, jacket=800, jeans=480, shoes=200, hair_cap=110, eyes=60, cards=5)}
lod_objs = [lod0]
for L, tg in LODS.items():
    parts_ = []
    names_ = []
    for n in ORDER:
        if n == "hair_cards": parts_.append(cards_subset(tg["cards"]))
        elif n == "mouth":
            if L == 1: parts_.append(PD["mouth"])
            else: continue
        elif n == "lashes":
            if L == 1: parts_.append(PD["lashes"])
            else: continue
        else:
            parts_.append(decimated_part(n, tg[n]))
        names_.append(n)
    ob, co = combine("CHAR_Customer_LOD%d" % L, parts_)
    if L == 1:
        m_ = np.zeros(len(co), bool); o_ = 0
        for n, p in zip(names_, parts_):
            c = len(p["co"])
            if n in ("skin_head", "mouth", "lashes"): m_[o_:o_ + c] = True
            o_ += c
        add_shape_keys(ob, co, m_)
    print("LOD%d tris" % L, tri_count(ob.data), "verts", len(ob.data.vertices))
    lod_objs.append(ob)

pickle.dump({}, open(os.path.join(ROOT, "_dummy.pkl"), "wb"))

# ---------- rig + collection + material
rig = O["Armature_Customer"]; rig.name = "CHAR_Customer"; rig.data.name = "CHAR_Customer_Armature"
for o in list(O):
    if o.name.startswith(("H_", "L_")) or o.name == "Body_full": bpy.data.objects.remove(o)
for c in list(bpy.data.collections):
    if c.name in ("HI", "LO"): bpy.data.collections.remove(c)
col = bpy.data.collections.new("CHAR_Customer"); sc.collection.children.link(col)
for o in [rig] + lod_objs:
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o)

def make_final_material():
    m = bpy.data.materials.new("MAT_Customer"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); pr = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(pr.outputs[0], out.inputs[0])
    def img(name, fn, cs):
        n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(ROOT, "textures", fn))
        n.image.colorspace_settings.name = cs; n.image.alpha_mode = 'STRAIGHT'; n.label = name; return n
    bc = img("BaseColor", "T_Customer_BaseColor.png", "sRGB"); orm = img("ORM", "T_Customer_ORM.png", "Non-Color")
    nm = img("Normal", "T_Customer_Normal.png", "Non-Color")
    nt.links.new(bc.outputs["Color"], pr.inputs["Base Color"])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[1], pr.inputs["Roughness"]); nt.links.new(sep.outputs[2], pr.inputs["Metallic"])
    nmn = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(nm.outputs["Color"], nmn.inputs["Color"])
    nt.links.new(nmn.outputs[0], pr.inputs["Normal"])
    # alpha: clip at 0.5 (round) so the exporter writes alphaMode MASK
    rnd = nt.nodes.new('ShaderNodeMath'); rnd.operation = 'ROUND'
    nt.links.new(bc.outputs["Alpha"], rnd.inputs[0]); nt.links.new(rnd.outputs[0], pr.inputs["Alpha"])
    # occlusion via glTF Material Output group
    ng = bpy.data.node_groups.get("glTF Material Output") or bpy.data.node_groups.new("glTF Material Output", 'ShaderNodeTree')
    if "Occlusion" not in [i.name for i in ng.interface.items_tree]:
        ng.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = ng
    nt.links.new(sep.outputs[0], g.inputs["Occlusion"])
    try: m.surface_render_method = 'DITHERED'
    except Exception: pass
    m.use_backface_culling = False
    return m
mat = make_final_material()
for o in lod_objs:
    o.data.materials.clear(); o.data.materials.append(mat)
    mod = o.modifiers.new("Armature", 'ARMATURE'); mod.object = rig
    o.parent = rig
    o.matrix_parent_inverse = rig.matrix_world.inverted()
# meshes visible: LOD0 only in viewport; keep all exported
lod_objs[1].hide_viewport = True; lod_objs[2].hide_viewport = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "stage4.blend"))
print("DONE4")


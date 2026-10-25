# Stage 3: UV density + pack, procedural bake -> textures/*.png.  Run: blender -b stage2.blend -P s3_bake.py
import sys, os, zlib, struct, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import dsl, mats
from dsl import set_pass
sc = bpy.context.scene
TEX = os.path.join(ROOT, "textures"); os.makedirs(TEX, exist_ok=True)
RES = 1024
O = bpy.data.objects
t0 = time.time()

# ---------------- UV density + pack
def uv_area(me, layer="UVMap"):
    uv = me.uv_layers[layer].data; a = 0.0
    for p in me.polygons:
        pts = [uv[l].uv for l in p.loop_indices]
        s = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
            s += x1 * y2 - x2 * y1
        a += abs(s) / 2
    return a
def mesh_area(me): return sum(p.area for p in me.polygons)
dens = {"L_skin_head": 1.25, "L_skin_hands": 0.9, "L_jacket": 0.5, "L_jeans": 0.5, "L_shoes": 0.6, "L_hair_cap": 0.6, "L_eyes": 1.0}
for n, d in dens.items():
    me = O[n].data
    s = d * math.sqrt(mesh_area(me) / max(uv_area(me), 1e-12))
    for l in me.uv_layers["UVMap"].data:
        l.uv = (l.uv[0] * s, l.uv[1] * s)
    me.uv_layers.active_index = [u.name for u in me.uv_layers].index("UVMap")
    print("UVDENS", n, round(s, 3))

sc.tool_settings.use_uv_select_sync = True
objs = [O[n] for n in dens]
bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
try:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.006)
except Exception as e:
    print("PACKERR", e); bpy.ops.uv.pack_islands(margin=0.006)
bpy.ops.object.mode_set(mode='OBJECT')
SC = 0.885
allu = []
for o in objs:
    for l in o.data.uv_layers["UVMap"].data:
        l.uv = (l.uv[0] * SC, l.uv[1] * SC); allu.append(l.uv[:])
allu = np.array(allu); print("UVBOUNDS", allu.min(0), allu.max(0))
# cards / lashes: UVHair = (U, V-0.89)
for n in ("L_hair_cards", "L_lashes"):
    me = O[n].data
    for a, b in zip(me.uv_layers["UVMap"].data, me.uv_layers["UVHair"].data):
        b.uv = (a.uv[0], a.uv[1] - 0.89)

# ---------------- bake setup
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.use_denoising = False
sc.cycles.samples = 8
if sc.world is None: sc.world = bpy.data.worlds.new("w")
sc.world.light_settings.distance = 0.18
def mkimg(name, fill):
    im = bpy.data.images.new(name, RES, RES, alpha=True, float_buffer=True)
    im.colorspace_settings.name = 'Non-Color'
    px = np.empty((RES, RES, 4), np.float32); px[:] = fill
    im.pixels.foreach_set(px.ravel()); im.update()
    return im
IM = {"COLOR": mkimg("bk_color", (0.35, 0.3, 0.28, 1)), "ROUGH": mkimg("bk_rough", (0.6, 0.6, 0.6, 1)),
      "METAL": mkimg("bk_metal", (0, 0, 0, 1)), "ALPHA": mkimg("bk_alpha", (1, 1, 1, 1)),
      "AO": mkimg("bk_ao", (1, 1, 1, 1)), "NORMAL": mkimg("bk_normal", (0.5, 0.5, 1.0, 1))}

M = {"skin": mats.mat_skin(), "jacket": mats.mat_jeans.__globals__["mat_jacket"](), "jeans": mats.mat_jeans(),
     "shoes": mats.mat_shoes(), "eyes": mats.mat_eyes(), "cap": mats.mat_hair_cap(), "cards": mats.mat_hair_cards(),
     "lash": mats.mat_lashes()}
HI = {"skin": ["H_skin_head", "H_skin_hands"], "jacket": ["H_jacket"], "jeans": ["H_jeans"], "shoes": ["H_shoes"]}
for k, ns in HI.items():
    for n in ns:
        o = O[n]; o.data.materials.clear(); o.data.materials.append(M[k])
        for p in o.data.polygons: p.use_smooth = True
LOP = {"skin": ["L_skin_head", "L_skin_hands"], "jacket": ["L_jacket"], "jeans": ["L_jeans"], "shoes": ["L_shoes"],
       "eyes": ["L_eyes"], "cap": ["L_hair_cap"], "cards": ["L_hair_cards"], "lash": ["L_lashes"]}
OWN = ("eyes", "cap", "cards", "lash")
tgt = bpy.data.materials.new("BAKE_TGT"); tgt.use_nodes = True
tn = tgt.node_tree.nodes.new('ShaderNodeTexImage'); tgt.node_tree.nodes.active = tn
def prep_target(mat):
    nt = mat.node_tree
    n = [x for x in nt.nodes if x.type == 'TEX_IMAGE' and x.label == "BAKEIMG"]
    if not n:
        n = nt.nodes.new('ShaderNodeTexImage'); n.label = "BAKEIMG"
    else: n = n[0]
    nt.nodes.active = n; n.select = True
    return n
for k in OWN:
    for n in LOP[k]:
        o = O[n]; o.data.materials.clear(); o.data.materials.append(M[k])
for k in HI:
    for n in LOP[k]:
        o = O[n]; o.data.materials.clear(); o.data.materials.append(tgt)
        for p in o.data.polygons: p.use_smooth = True
for k in OWN:
    for n in LOP[k]:
        for p in O[n].data.polygons: p.use_smooth = True
imgnode_tgt = prep_target(tgt)
imgnodes = {k: prep_target(M[k]) for k in OWN}

def bake(part, passname, btype, from_hi, samples=8):
    sc.cycles.samples = samples
    img = IM[passname]
    for n in LOP[part]:
        o = O[n]
        node = imgnode_tgt if part not in OWN else imgnodes[part]
        node.image = img
        mt = o.data.materials[0]; mt.node_tree.nodes.active = node
        bpy.ops.object.select_all(action='DESELECT')
        if from_hi:
            for hn in HI[part]: O[hn].select_set(True)
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.bake(type=btype, margin=8, margin_type='EXTEND', use_selected_to_active=bool(from_hi),
                            cage_extrusion=0.03, max_ray_distance=0.06, normal_space='TANGENT',
                            use_clear=False, uv_layer="UVMap")
for m in M.values(): pass
def set_all(which):
    for m in M.values(): set_pass(m, which)

# hide helpers
for o in O:
    if o.type == 'MESH' and o.name.startswith("H_"): o.hide_render = False
O["Body_full"].hide_render = True

for which in ("COLOR", "ROUGH", "METAL", "ALPHA"):
    set_all(which)
    for part in LOP:
        bake(part, which, 'EMIT', part in HI, samples=2)
    print("BAKED", which, round(time.time() - t0), flush=True)
set_all("COLOR")
for part in HI:
    bake(part, "NORMAL", 'NORMAL', True, samples=4)
print("BAKED NORMAL", round(time.time() - t0), flush=True)
# AO from low-poly (HI hidden)
for o in O:
    if o.name.startswith("H_"): o.hide_render = True
for part in LOP:
    skip = ("L_hair_cards", "L_lashes")
    for n in skip: O[n].hide_render = part not in ("cards", "lash")
    # AO shader result isn't material dependent
    bake(part, "AO", 'AO', False, samples=48)
for n in ("L_hair_cards", "L_lashes"): O[n].hide_render = False
print("BAKED AO", round(time.time() - t0), flush=True)

# ---------------- write PNGs (pure python encoder)
def write_png(path, arr):  # arr uint8 (H,W,4), origin top-left
    h, w, c = arr.shape
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))
    def chunk(t, d):
        c_ = struct.pack(">I", len(d)) + t + d
        return c_ + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + \
          chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)
def getpx(name):
    a = np.empty(RES * RES * 4, np.float32); IM[name].pixels.foreach_get(a)
    return a.reshape(RES, RES, 4)[::-1]       # flip: blender origin bottom-left
def srgb(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
q = lambda a: np.clip(np.round(a * 255), 0, 255).astype(np.uint8)
col = getpx("COLOR"); al = getpx("ALPHA"); ao = getpx("AO"); ro = getpx("ROUGH"); me_ = getpx("METAL"); nr = getpx("NORMAL")
base = np.dstack([srgb(col[..., 0]), srgb(col[..., 1]), srgb(col[..., 2]), al[..., 0]])
orm = np.dstack([ao[..., 0], ro[..., 0], me_[..., 0], np.ones((RES, RES))])
nrm = np.dstack([nr[..., 0], nr[..., 1], nr[..., 2], np.ones((RES, RES))])
# ---- fix pass: mouth-interior flat patches (teeth / tongue / cavity) in the top-right free atlas area
MOUTH_TILES = {"teeth": (800, (0.90, 0.88, 0.80), 0.35), "tongue": (864, (0.70, 0.28, 0.30), 0.45), "cavity": (928, (0.025, 0.008, 0.01), 0.8)}
for nm_, (c0_, rgb_, rough_) in MOUTH_TILES.items():
    sl = (slice(2, 110), slice(c0_, c0_ + 64))
    base[sl] = np.array([rgb_[0], rgb_[1], rgb_[2], 1.0]); orm[sl] = np.array([1.0, rough_, 0.0, 1.0]); nrm[sl] = np.array([0.5, 0.5, 1.0, 1.0])
write_png(os.path.join(TEX, "T_Customer_BaseColor.png"), q(base))
write_png(os.path.join(TEX, "T_Customer_ORM.png"), q(orm))
write_png(os.path.join(TEX, "T_Customer_Normal.png"), q(nrm))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "stage3.blend"))
print("DONE3", round(time.time() - t0))

"""ENV_BankHall builder. Run: blender -b -P build_env.py
Starts from a COPY of heistbox_assets.blend (empties kept exactly), rebuilds the hall modular / trim-sheet textured / merged by material."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import texlib as T, matlib as ML

ROOT = r"C:\Users\Shaik\Downloads\heistbox\assets3d"
ENV = ROOT + r"\env"
TEX = ENV + r"\textures"

bpy.ops.wm.open_mainfile(filepath=ROOT + r"\heistbox_assets.blend")
bpy.ops.wm.save_as_mainfile(filepath=ENV + r"\ENV_BankHall.blend")   # work on copy only

# ---------------- cleanup: keep empties only
empties = [o for o in bpy.data.objects if o.type == 'EMPTY']
EMPTY_NAMES = ["SPAWN_Player", "SPAWN_Customer", "CAM_Overview", "CAM_VaultL", "CAM_VaultM", "CAM_VaultR", "ANCHOR_LaserTarget"]
assert sorted(e.name for e in empties) == sorted(EMPTY_NAMES), [e.name for e in empties]
for o in list(bpy.data.objects):
    if o.type != 'EMPTY':
        bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
for m in list(bpy.data.materials): bpy.data.materials.remove(m)
for me in list(bpy.data.meshes): bpy.data.meshes.remove(me)
for l in list(bpy.data.lights): bpy.data.lights.remove(l)
for c in list(bpy.data.cameras): bpy.data.cameras.remove(c)
envc = bpy.data.collections.new("ENV_BankHall")
bpy.context.scene.collection.children.link(envc)
for e in empties:
    for c in list(e.users_collection): c.objects.unlink(e)
    envc.objects.link(e)

# ---------------- textures (1024)
def mk(name, gen, seed):
    col, rough, metal, nrm = gen(seed)
    T.save_png(f"{name}_BaseColor", col, f"{TEX}\\{name}_BaseColor.png", True)
    T.save_png(f"{name}_ORM", T.orm(1.0, rough, metal), f"{TEX}\\{name}_ORM.png", False)
    T.save_png(f"{name}_Normal", nrm, f"{TEX}\\{name}_Normal.png", False)
    return [bpy.data.images[f"{name}_{k}"] for k in ("BaseColor", "ORM", "Normal")]

IMG = {
    "Marble": mk("Marble", T.make_marble, 3),
    "Wall": mk("Wall", T.make_wall, 10),
    "Brass": mk("Brass", T.make_brass, 20),
    "Wood": mk("Wood", T.make_wood, 30),
}
ao_img = bpy.data.images.new("Hall_AO", 1024, 1024, alpha=False)
ao_img.colorspace_settings.name = 'Non-Color'
ao_img.generated_color = (1, 1, 1, 1)

MATS = ["Marble", "Wall", "Brass", "Wood", "Glass", "Lamp", "Steel"]
mats = {}
for k in ("Marble", "Wall", "Brass", "Wood"):
    mats[k] = ML.pbr_mat("MAT_" + k, IMG[k][0], IMG[k][1], IMG[k][2], ao=ao_img)
mats["Glass"] = ML.flat_mat("MAT_Ice", (0.55, 0.8, 1.0), 0.05, 0.0, alpha=0.22)
mats["Lamp"] = ML.flat_mat("MAT_Lamp", (0.05, 0.05, 0.05), 0.5, 0.0, emit=(1.0, 0.82, 0.55), strength=3.0)
mats["Steel"] = ML.flat_mat("MAT_Steel", (0.35, 0.42, 0.5), 0.35, 0.9)
TILE = {"Marble": 2.0, "Wall": 2.0, "Brass": 0.6, "Wood": 1.0, "Glass": 1.0, "Lamp": 1.0, "Steel": 1.0}

# ---------------- geometry builder (single bmesh, material per face)
bm = bmesh.new()
uv0 = bm.loops.layers.uv.new("UVMap")
uv1 = bm.loops.layers.uv.new("UV_AO")

def _finish(verts, mat, cull=(), faces=None):
    if faces is None: faces = {f for v in verts for f in v.link_faces}
    mi = MATS.index(mat)
    t = TILE[mat]
    dele = []
    for f in faces:
        f.material_index = mi
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        key = ('+' if n[ax] > 0 else '-') + 'xyz'[ax]
        if key in cull:
            dele.append(f); continue
        for l in f.loops:
            p = l.vert.co
            a, b = [(1, 2), (0, 2), (0, 1)][ax]
            l[uv0].uv = (p[a] / t, p[b] / t)
    if dele:
        bmesh.ops.delete(bm, geom=dele, context='FACES')

def box(c, s, mat, cull=(), bevel=0.0, rotz=0.0):
    old = set(bm.faces)
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r['verts']
    m = Matrix.Translation(c) @ Matrix.Rotation(rotz, 4, 'Z') @ Matrix.Diagonal((*s, 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=vs)
    bm.normal_update()
    if bevel > 0 and not cull:
        es = list({e for v in vs for e in v.link_edges})
        res = bmesh.ops.bevel(bm, geom=es, offset=bevel, segments=1, affect='EDGES')
        bm.normal_update(); bm.faces.ensure_lookup_table()
        _finish(None, mat, cull, faces={f for f in bm.faces if f not in old})
        return
    bm.normal_update()
    _finish(vs, mat, cull)

def cyl(c, r, depth, mat, axis='z', segs=16, cap=True, r2=None):
    res = bmesh.ops.create_cone(bm, cap_ends=cap, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    vs = res['verts']
    rot = {'z': Matrix.Identity(4), 'x': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ rot, verts=vs)
    bm.normal_update()
    _finish(vs, mat)

def ring(c, rin, rout, thick, mat, axis='z', segs=48, cull=()):
    """annulus in XY plane thickness along z (centered), rotated for axis."""
    vs = []; faces = []
    h = thick / 2
    def ringverts(r, z):
        return [bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z)) for i in range(segs)]
    ot, it, ob, ib = ringverts(rout, h), ringverts(rin, h), ringverts(rout, -h), ringverts(rin, -h)
    vs = ot + it + ob + ib
    for i in range(segs):
        j = (i + 1) % segs
        faces.append(bm.faces.new((ot[i], ot[j], it[j], it[i])))        # top (+z)
        faces.append(bm.faces.new((ob[j], ob[i], ib[i], ib[j])))        # bottom
        faces.append(bm.faces.new((ob[i], ob[j], ot[j], ot[i])))        # outer
        faces.append(bm.faces.new((it[i], it[j], ib[j], ib[i])))        # inner
    rot = {'z': Matrix.Identity(4), 'y': Matrix.Rotation(math.pi / 2, 4, 'X'), 'x': Matrix.Rotation(math.pi / 2, 4, 'Y')}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ rot, verts=vs)
    bm.normal_update()
    _finish(vs, mat, cull)

W, D, H = 16.0, 12.0, 4.6
yb, rec, aw = 6.0, 1.8, 3.6
xs = [-4.6, 0.0, 4.6]
FLOOR_ONLY = ('-z', '+x', '-x', '+y', '-y')   # keep only the +z face

# ---- floor, inlays
box((0, 0, -0.05), (W, D, 0.1), "Marble", cull=('-z',))
box((0, yb + rec / 2, -0.05), (W, rec, 0.1), "Marble", cull=('-z',))
for sy in (-1, 1):
    box((0, sy * 5.3, 0.003), (14.8, 0.1, 0.006), "Brass", cull=FLOOR_ONLY)
for sx in (-1, 1):
    box((sx * 7.3, 0, 0.003), (0.1, 10.7, 0.006), "Brass", cull=FLOOR_ONLY)
ring((0, -0.0, 0.003), 1.5, 1.6, 0.006, "Brass", segs=48, cull=('-z', ))
ring((0, 0, 0.003), 0.75, 0.8, 0.006, "Brass", segs=32, cull=('-z',))

# ---- walls (original footprint)
box((0, -D / 2, H / 2), (W, 0.2, H), "Wall", cull=('-z', '+z'))
box((-W / 2, 0, H / 2), (0.2, D, H), "Wall", cull=('-z', '+z'))
box((W / 2, 0, H / 2), (0.2, D, H), "Wall", cull=('-z', '+z'))
box((0, yb + rec, H / 2), (W, 0.2, H), "Wall", cull=('-z', '+z'))
edges = [-W / 2, xs[0] - aw / 2, xs[0] + aw / 2, xs[1] - aw / 2, xs[1] + aw / 2, xs[2] - aw / 2, xs[2] + aw / 2, W / 2]
pillars = []
for i in range(0, len(edges), 2):
    x0, x1 = edges[i], edges[i + 1]
    if x1 - x0 > 0.01:
        pillars.append((x0, x1))
        box(((x0 + x1) / 2, yb, H / 2), (x1 - x0, 0.2, H), "Wall", cull=('-z', '+z'))
for i, x in enumerate(xs):
    for s in (-1, 1):
        box((x + s * aw / 2, yb + rec / 2, H / 2), (0.15, rec, H), "Wall", cull=('-z', '+z'))
    box((x, yb - 0.05, 3.4), (aw + 0.3, 0.1, 0.12), "Brass", bevel=0.01)
    for s in (-1, 1):  # brass door-frame posts
        box((x + s * (aw / 2 - 0.1), yb - 0.07, 1.7), (0.12, 0.14, 3.4), "Brass", cull=('-z',))
    cyl_c = (x, yb + rec - 0.16, 1.6)
    ring(cyl_c, 1.2, 1.5, 0.12, "Brass", axis='y', segs=40)
# alcove ceiling extension
box((0, yb + rec / 2, H + 0.05), (W, rec, 0.1), "Wall", cull=('+z',))
# lamp over each alcove
for x in xs:
    box((x, yb + 0.9, H - 0.02), (1.2, 1.0, 0.04), "Lamp", cull=('+z', '+x', '-x', '+y', '-y'))

# ---- wall dressing helper: skirting (marble) + dado (wood) + rail (brass) along a wall run
def dressing(a0, a1, fixed, axis, sign):
    """axis 'x': run along x at y=fixed, interior normal sign (+1 faces +y). axis 'y': run along y at x=fixed."""
    L = a1 - a0; mid = (a0 + a1) / 2
    def put(depth, z0, z1, mat, bev=0.0):
        zc = (z0 + z1) / 2; hz = z1 - z0
        off = fixed + sign * (0.1 + depth / 2)
        if axis == 'x': box((mid, off, zc), (L, depth, hz), mat, bevel=bev, cull=('-z',) if z0 == 0 else ())
        else: box((off, mid, zc), (depth, L, hz), mat, bevel=bev, cull=('-z',) if z0 == 0 else ())
    put(0.07, 0.0, 0.25, "Marble", 0.008)
    put(0.04, 0.25, 1.1, "Wood")
    put(0.08, 1.1, 1.14, "Brass", 0.01)
    # cornice
    put(0.22, H - 0.25, H, "Wall", 0.01)
    put(0.26, H - 0.30, H - 0.25, "Brass", 0.008)

dressing(-W / 2 + 0.1, W / 2 - 0.1, -D / 2, 'x', +1)
dressing(-D / 2 + 0.1, yb - 0.1, -W / 2, 'y', +1)
dressing(-D / 2 + 0.1, yb - 0.1, W / 2, 'y', -1)
for x0, x1 in pillars:
    dressing(x0, x1, yb, 'x', -1)

# ---- pilasters
def pilaster(c, axis):
    sx, sy = (0.5, 0.2) if axis == 'x' else (0.2, 0.5)
    off = {'x': (0, 0.1), 'y': (0.1, 0)}[axis]
    box((c[0], c[1], 2.15), (sx, sy, 3.7), "Marble", bevel=0.012)
    box((c[0], c[1], 0.3), (sx + 0.1, sy + 0.1, 0.12), "Brass", bevel=0.008)
    box((c[0], c[1], 4.05), (sx + 0.12, sy + 0.12, 0.16), "Brass", bevel=0.008)
for y in (-4.0, -1.3, 1.3, 4.0):
    pilaster((-W / 2 + 0.1 + 0.2 + 0.0 - 0.0, y), 'y')
    pilaster((W / 2 - 0.1 - 0.2, y), 'y')
for x in (-6.0, -3.0, 3.0, 6.0):
    pilaster((x, -D / 2 + 0.1 + 0.2), 'x')

# ---- coffered ceiling + lamps
box((0, 0, H + 0.05), (W, D, 0.1), "Wall", cull=('+z',))
for y in (-2.0, 2.0):
    box((0, y, H - 0.125), (W - 0.4, 0.3, 0.25), "Wall", cull=('+z',), bevel=0)
for x in (-4.0, 0.0, 4.0):
    box((x, 0, H - 0.2), (0.3, D - 0.4, 0.1), "Wall", cull=('+z',))
for x in (-6, -2, 2, 6):
    for y in (-4, 0, 4):
        box((x, y, H - 0.02), (1.4, 1.4, 0.04), "Lamp", cull=('+z', '+x', '-x', '+y', '-y'))

# ---- teller counter (y=0, top z 1.14)
box((0, 0, 0.53), (5.9, 0.9, 1.06), "Wood", cull=('-z',))
for i in range(6):
    box((-2.5 + i, -0.465, 0.55), (0.85, 0.03, 0.7), "Wood", cull=('+y',))
box((0, 0, 1.10), (6.2, 1.2, 0.08), "Marble", bevel=0.01)
box((0, -0.52, 1.0), (6.1, 0.05, 0.1), "Brass", bevel=0.008)
cyl((0, -0.52, 0.15), 0.025, 5.6, "Brass", axis='x', segs=10)
for x in (-2.7, 0, 2.7):
    box((x, -0.5, 0.15), (0.05, 0.06, 0.05), "Brass", cull=('-z',))
box((0, 0.25, 1.49), (6.0, 0.04, 0.7), "Glass")
box((0, 0.25, 1.16), (6.06, 0.07, 0.04), "Brass", bevel=0.006)
box((0, 0.25, 1.85), (6.06, 0.07, 0.04), "Brass", bevel=0.006)
for x in (-3.0, -1.0, 1.0, 3.0):
    box((x, 0.25, 1.5), (0.06, 0.07, 0.74), "Brass", bevel=0.006)
# teller desk extension behind counter (Tina side shelf)
box((0, 1.6, 0.4), (5.0, 0.5, 0.8), "Wood", cull=('-z',))
box((0, 1.6, 0.82), (5.1, 0.6, 0.04), "Marble")

# ---- queue stanchions + ropes
for x in (3.5, 5.0, 6.5):
    cyl((x, -3.0, 0.02), 0.16, 0.04, "Brass", segs=12)
    cyl((x, -3.0, 0.5), 0.025, 0.9, "Brass", segs=8)
    cyl((x, -3.0, 0.97), 0.045, 0.06, "Brass", segs=8)
for x in (4.25, 5.75):
    box((x, -3.0, 0.88), (1.5 - 0.1, 0.025, 0.025), "Wood")

# ---- benches along left wall
for y in (-3.5, 2.5):
    box((-7.35, y, 0.45), (0.5, 1.8, 0.06), "Wood", bevel=0.01)
    box((-7.6, y, 0.75), (0.06, 1.8, 0.55), "Wood", cull=())
    for dy in (-0.8, 0.8):
        box((-7.35, y + dy, 0.21), (0.4, 0.05, 0.42), "Brass", cull=('-z',))

# ---- vault floor plates
for n, x, m in (("L", xs[0], "Brass"), ("M", xs[1], "Steel"), ("R", xs[2], "Steel")):
    box((x, yb + 0.9, 0.015), (aw - 0.3, 1.4, 0.03), m, cull=('-z',))

# ---------------- mesh object
bm.normal_update()
me = bpy.data.meshes.new("ENV_Hall_tmp")
bm.to_mesh(me); bm.free()
for k in MATS:
    me.materials.append(mats[k])
obj = bpy.data.objects.new("ENV_Hall_tmp", me)
envc.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
me.shade_smooth() if False else None

# smooth shading off (hard-surface); unique AO UV
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=1e-5) if False else None
me.uv_layers.active_index = 1
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.6, correct_aspect=True, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
me.uv_layers.active_index = 1
me.uv_layers[1].active_render = True
print("tris before bake:", sum(len(p.vertices) - 2 for p in me.polygons))

# ---------------- bake AO
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 64
sc.cycles.use_denoising = False
if sc.world is None:
    sc.world = bpy.data.worlds.new("W")
sc.world.use_nodes = True
sc.world.light_settings.distance = 1.6
sc.render.bake.margin = 6
sc.render.bake.use_clear = True
for m in mats.values():  # active node = AO image for all materials
    nt = m.node_tree
    a = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image == ao_img), None)
    if a is None:
        a = ML.tex_node(nt, ao_img, (-600, -600), uvname="UV_AO")
    nt.nodes.active = a
    a.select = True
bpy.ops.object.bake(type='AO')
ao_img.filepath_raw = TEX + r"\Hall_AO.png"
ao_img.file_format = 'PNG'
ao_img.save()
me.uv_layers.active_index = 0; me.uv_layers[0].active_render = True
# lamps/glass/steel: AO not exported (no ORM) -> fine. Remove unused AO node from flat mats so exporter ignores them
for k in ("Glass", "Lamp", "Steel"):
    nt = mats[k].node_tree
    for n in list(nt.nodes):
        if n.type in ('TEX_IMAGE', 'UVMAP'): nt.nodes.remove(n)

# ---------------- split by material -> merged-by-material objects
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL')
bpy.ops.object.mode_set(mode='OBJECT')
parts = []
for o in list(envc.objects):
    if o.type == 'MESH':
        mname = o.data.materials[0].name if o.data.materials else None
        base = [k for k in MATS if (mats[k].name == mname)][0] if mname else "X"
        o.name = "ENV_" + base
        o.data.name = "ENV_" + base
        parts.append(o)
        # drop unused material slots
        while len(o.data.materials) > 1:
            o.data.materials.pop(index=1 if o.data.materials[0].name == mname else 0)
for o in parts:
    o.select_set(False)

bpy.ops.wm.save_mainfile()
tot = 0
for o in parts:
    t = sum(len(p.vertices) - 2 for p in o.data.polygons)
    tot += t
    print("OBJ", o.name, "tris", t, "mats", [m.name for m in o.data.materials])
print("TOTAL TRIS", tot)





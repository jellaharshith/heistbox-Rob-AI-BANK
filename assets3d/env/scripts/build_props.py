"""Props: PROP_CashSmall, PROP_CashHeist, PROP_Megaphone, PROP_WantedPoster, PROP_Terminal. Run: blender -b -P build_props.py"""
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(__file__))
import texlib as T, matlib as ML

ENV = r"C:\Users\Shaik\Downloads\heistbox\assets3d\env"
TEX = ENV + r"\textures"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.render.fps = 30
coll = bpy.data.collections.new("PROPS"); sc.collection.children.link(coll)

# ---------------- atlas 1024: regions in pixels (x0,y0,x1,y1) y bottom-up
R = {
    "env_front": (0, 744, 512, 1024), "env_back": (512, 744, 1024, 1024), "paper": (0, 704, 64, 744),
    "bills_side": (0, 512, 256, 704), "bill_top": (256, 512, 768, 704),
    "crate_wood": (0, 256, 512, 512), "crate_label": (512, 256, 1024, 512),
    "red": (0, 128, 128, 256), "white": (128, 128, 256, 256), "black": (256, 128, 384, 256), "steel": (384, 128, 512, 256),
    "brass": (512, 128, 640, 256), "darkwood": (640, 128, 768, 256), "grey": (768, 128, 896, 256), "rubber": (896, 128, 1024, 256),
    "bezel": (0, 0, 128, 128), "cyan": (128, 0, 256, 128), "gunmetal": (256, 0, 384, 128),
}
SOLID = {"red": ((0.62, 0.07, 0.05), 0.4, 0), "white": ((0.85, 0.85, 0.82), 0.45, 0), "black": ((0.025, 0.025, 0.03), 0.6, 0),
         "steel": ((0.58, 0.6, 0.63), 0.32, 1), "brass": ((0.78, 0.58, 0.22), 0.3, 1), "darkwood": ((0.12, 0.06, 0.03), 0.5, 0),
         "grey": ((0.3, 0.3, 0.33), 0.6, 0), "rubber": ((0.04, 0.04, 0.045), 0.85, 0), "bezel": ((0.08, 0.09, 0.1), 0.45, 0),
         "cyan": ((0.1, 0.8, 0.95), 0.4, 0), "gunmetal": ((0.14, 0.15, 0.17), 0.4, 1)}
A = 1024
bc = np.zeros((A, A, 3)); orm = np.zeros((A, A, 3)); orm[..., 0] = 1.0; orm[..., 1] = 0.7
def fill(name, color, rough, metal):
    x0, y0, x1, y1 = R[name]
    bc[y0:y1, x0:x1] = color; orm[y0:y1, x0:x1, 1] = rough; orm[y0:y1, x0:x1, 2] = metal
for k, (c, r, m) in SOLID.items(): fill(k, c, r, m)
fill("paper", (0.82, 0.76, 0.6), 0.8, 0)
# envelope
def region_arr(name): x0, y0, x1, y1 = R[name]; return y1 - y0, x1 - x0
h, w = region_arr("env_front")
ef = np.ones((h, w, 3)) * np.array((0.84, 0.77, 0.6))
n = T.fnoise(512, 1.3, 5)[:h, :w]; ef *= (0.93 + 0.1 * n[..., None])
ef[:8] = (0.55, 0.12, 0.1); ef[-8:] = (0.55, 0.12, 0.1); ef[:, :8] = (0.55, 0.12, 0.1); ef[:, -8:] = (0.55, 0.12, 0.1)
T.blit(ef, T.text_mask("$25", 140), w / 2, h / 2, (0.08, 0.2, 0.1))
x0, y0, x1, y1 = R["env_front"]; bc[y0:y1, x0:x1] = ef; orm[y0:y1, x0:x1, 1] = 0.8; orm[y0:y1, x0:x1, 2] = 0
eb = np.ones((h, w, 3)) * np.array((0.8, 0.73, 0.57)) * (0.93 + 0.1 * n[..., None])
yy, xx = np.mgrid[0:h, 0:w]
flap = (yy > h * 0.5 + (np.abs(xx - w / 2) * -0.95 + w / 2 * 0.95) * 0.0 - 0) & (yy > h - 1 - (h * 0.55) * (1 - np.abs(xx - w / 2) / (w / 2)) * 1.0 + 0)
edge = np.abs(yy - (h - 1 - (h * 0.55) * (1 - np.abs(xx - w / 2) / (w / 2)))) < 3
eb[edge] = (0.4, 0.33, 0.22)
x0, y0, x1, y1 = R["env_back"]; bc[y0:y1, x0:x1] = eb; orm[y0:y1, x0:x1, 1] = 0.8; orm[y0:y1, x0:x1, 2] = 0
# bills
h, w = region_arr("bills_side")
sl = np.ones((h, w, 3)) * np.array((0.2, 0.36, 0.22))
sl[(np.arange(h) % 4) < 1] = (0.78, 0.82, 0.7)
x0, y0, x1, y1 = R["bills_side"]; bc[y0:y1, x0:x1] = sl; orm[y0:y1, x0:x1, 1] = 0.75; orm[y0:y1, x0:x1, 2] = 0
h, w = region_arr("bill_top")
bt = np.ones((h, w, 3)) * np.array((0.38, 0.55, 0.38)) * (0.9 + 0.15 * T.fnoise(512, 1.5, 8)[:h, :w][..., None])
bt[:10] = (0.2, 0.34, 0.2); bt[-10:] = (0.2, 0.34, 0.2); bt[:, :10] = (0.2, 0.34, 0.2); bt[:, -10:] = (0.2, 0.34, 0.2)
yy, xx = np.mgrid[0:h, 0:w]
oval = ((xx - w / 2) / 90.0) ** 2 + ((yy - h / 2) / 62.0) ** 2 < 1
bt[oval] = bt[oval] * 0.6 + 0.4 * np.array((0.8, 0.85, 0.7))
T.blit(bt, T.text_mask("100", 70), w / 2, h / 2, (0.12, 0.25, 0.14))
x0, y0, x1, y1 = R["bill_top"]; bc[y0:y1, x0:x1] = bt; orm[y0:y1, x0:x1, 1] = 0.75; orm[y0:y1, x0:x1, 2] = 0
# crate wood
wcol, wr, _, _ = T.make_wood(41)
h, w = region_arr("crate_wood")
cw = wcol[:h, :w] * 1.6
x0, y0, x1, y1 = R["crate_wood"]; bc[y0:y1, x0:x1] = np.clip(cw, 0, 1); orm[y0:y1, x0:x1, 1] = wr[:h, :w]; orm[y0:y1, x0:x1, 2] = 0
# label
h, w = region_arr("crate_label")
lb = np.ones((h, w, 3)) * np.array((0.86, 0.8, 0.62))
lb[:12] = (0.5, 0.08, 0.06); lb[-12:] = (0.5, 0.08, 0.06); lb[:, :12] = (0.5, 0.08, 0.06); lb[:, -12:] = (0.5, 0.08, 0.06)
s = 12
mk = T.text_mask("$4,975", 7 * s)
T.blit(lb, mk, w / 2, h / 2, (0.05, 0.05, 0.05))
x0, y0, x1, y1 = R["crate_label"]; bc[y0:y1, x0:x1] = lb; orm[y0:y1, x0:x1, 1] = 0.7; orm[y0:y1, x0:x1, 2] = 0
img_bc = T.save_png("Props_BaseColor", bc, TEX + r"\Props_BaseColor.png", True)
img_orm = T.save_png("Props_ORM", orm, TEX + r"\Props_ORM.png", False)

# runtime textures: plain emissive placeholder images
ph, pw = 768, 512
pimg = np.ones((ph, pw, 3)) * np.array((0.78, 0.7, 0.52)) * (0.9 + 0.15 * T.fnoise(512, 1.4, 12)[:1, :1][..., None])
pn = T.fnoise(768, 1.3, 13)[:ph, :pw]
pimg = np.array((0.78, 0.7, 0.52)) * (0.88 + 0.2 * pn[..., None])
pimg[:14] = pimg[-14:] = (0.2, 0.12, 0.08); pimg[:, :14] = pimg[:, -14:] = (0.2, 0.12, 0.08)
T.blit(pimg, T.text_mask("WANTED", 77), pw / 2, ph - 120, (0.12, 0.05, 0.03))
yy, xx = np.mgrid[0:ph, 0:pw]
head = ((xx - pw / 2) / 85.0) ** 2 + ((yy - 420) / 100.0) ** 2 < 1
body = ((xx - pw / 2) / 170.0) ** 2 + ((yy - 250) / 130.0) ** 2 < 1
sil = (head | body) & (yy > 130 + 0 * xx)
pimg[sil] = (0.25, 0.2, 0.15)
T.blit(pimg, T.text_mask("REWARD", 50), pw / 2, 105, (0.12, 0.05, 0.03))
T.blit(pimg, T.text_mask("$4,975", 60), pw / 2, 50, (0.4, 0.05, 0.03))
img_poster = T.save_png("PosterRuntime", pimg, TEX + r"\PosterRuntime.png", True)
sh, sw = 320, 512
simg = np.ones((sh, sw, 3)) * np.array((0.01, 0.04, 0.05))
simg[(np.arange(sh) % 4) < 1] *= 1.8
simg[:6] = simg[-6:] = (0.1, 0.7, 0.85); simg[:, :6] = simg[:, -6:] = (0.1, 0.7, 0.85)
T.blit(simg, T.text_mask("PAIR BANK", 42), sw / 2, sh - 80, (0.2, 0.9, 1.0))
T.blit(simg, T.text_mask(">READY_", 32), sw / 2, 110, (0.1, 0.8, 0.4))
img_screen = T.save_png("ScreenRuntime", simg, TEX + r"\ScreenRuntime.png", True)

MAT_P = ML.pbr_mat("MAT_Props", img_bc, img_orm)
MAT_POSTER = ML.runtime_mat("MAT_PosterRuntime", img_poster)
MAT_SCREEN = ML.runtime_mat("MAT_ScreenRuntime", img_screen)

# ---------------- builder
class B:
    def __init__(self, name, mats):
        self.name = name; self.bm = bmesh.new(); self.mats = mats
        self.uv = self.bm.loops.layers.uv.new("UVMap")
    def _uvrect(self, region, a, b):
        x0, y0, x1, y1 = R[region]; i = 3
        return ((x0 + i + a * (x1 - x0 - 2 * i)) / A, (y0 + i + b * (y1 - y0 - 2 * i)) / A)
    def box(self, c, s, region, rot=(0, 0, 0), bevel=0.0):
        """region: str or dict {'+z':..,'default':..}. Faces fill the region (planar per face)."""
        bm = self.bm
        old = set(bm.faces)
        r = bmesh.ops.create_cube(bm, size=1.0); vs = r['verts']
        if bevel > 0:
            bmesh.ops.bevel(bm, geom=list({e for v in vs for e in v.link_edges}), offset=bevel / max(s), segments=1, affect='EDGES')
            vs = [v for v in bm.verts if v.is_valid and v not in self._old] if False else None
        bm.faces.ensure_lookup_table(); bm.normal_update()
        faces = [f for f in bm.faces if f not in old]
        for f in faces:
            nrm = f.normal; ax = max(range(3), key=lambda i: abs(nrm[i]))
            key = ('+' if nrm[ax] > 0 else '-') + 'xyz'[ax]
            reg = region if isinstance(region, str) else region.get(key, region.get('default'))
            for l in f.loops:
                p = l.vert.co + Vector((.5, .5, .5))
                a, b = {'+z': (p.x, p.y), '-z': (p.x, 1 - p.y), '-y': (p.x, p.z), '+y': (1 - p.x, p.z), '+x': (p.y, p.z), '-x': (1 - p.y, p.z)}[key]
                l[self.uv].uv = self._uvrect(reg, a, b)
            f.material_index = 0
        vv = {v for f in faces for v in f.verts}
        m = Matrix.Translation(c) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[0], 4, 'X') @ Matrix.Diagonal((*s, 1.0))
        bmesh.ops.transform(bm, matrix=m, verts=list(vv))
    def cyl(self, c, r1, r2, depth, region, axis='y', segs=16, front_region=None, rot=(0, 0, 0)):
        """axis y: radius r1 at +y end, r2 at -y end."""
        bm = self.bm
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r1, radius2=r2, depth=depth)
        vs = res['verts']
        rm = {'z': Matrix.Identity(4), 'y': Matrix.Rotation(math.pi / 2, 4, 'X'), 'x': Matrix.Rotation(math.pi / 2, 4, 'Y')}[axis]
        m = Matrix.Translation(c) @ Matrix.Rotation(rot[2], 4, 'Z') @ Matrix.Rotation(rot[0], 4, 'X') @ rm
        bmesh.ops.transform(bm, matrix=m, verts=vs)
        bm.normal_update()
        axv = (m.to_3x3() @ Vector((0, 0, 1))).normalized()
        for f in {f for v in vs for f in v.link_faces}:
            reg = region
            if front_region and f.normal.dot(axv) > 0.95: reg = front_region
            f.material_index = 0
            for l in f.loops: l[self.uv].uv = self._uvrect(reg, .5, .5)
    def quad(self, c, size, rot, matidx, region=None):
        """plane facing -Y (before rot), UV fills 0-1 (or region)"""
        bm = self.bm
        w, h = size
        pts = [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)]
        m = Matrix.Translation(c) @ Matrix.Rotation(rot[0], 4, 'X')
        vs = [bm.verts.new(m @ Vector(p)) for p in pts]
        f = bm.faces.new(vs)   # winding gives normal -Y
        if f.normal.y > 0: f.normal_flip()
        f.material_index = matidx
        for l, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            l[self.uv].uv = uv
    def build(self):
        bm = self.bm
        bm.normal_update()
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me); bm.free()
        for m in self.mats: me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        coll.objects.link(o)
        return o

# ---- shared CASH_Bundle mesh data: unit-size banded bill stack (bills_side/bill_top + paper band).
# Used as linked-duplicate child objects (different node scale) of PROP_CashHeist (12 bundles) and PROP_CashSmall (1 bill
# sticking out of the envelope) -> ONE glTF mesh referenced by 13 nodes.
b = B("CASH_Bundle", [MAT_P])
b.box((0, 0, 0), (1, 1, 1), {'+z': 'bill_top', 'default': 'bills_side'})
b.box((0, 0, 0), (0.03 / 0.14, 0.13 / 0.125, 0.082 / 0.08), 'paper')
_bo = b.build()
BUNDLE = _bo.data; bpy.data.objects.remove(_bo)
def bundle_child(name, parent, loc, scale):
    o = bpy.data.objects.new(name, BUNDLE); coll.objects.link(o)
    o.parent = parent; o.location = loc; o.scale = scale
    return o

# ---- PROP_CashSmall: "$25" envelope, lying flat, +Z up
b = B("PROP_CashSmall", [MAT_P])
b.box((0, 0, 0.007), (0.22, 0.12, 0.014), {'+z': 'env_front', '-z': 'env_back', 'default': 'paper'}, bevel=0.002)
_cs = b.build()
# a small bill sticking out of the top edge (shared bundle mesh, scaled)
bundle_child("PROP_CashSmall_Bill", _cs, (0.0, 0.065, 0.011), (0.12, 0.03, 0.004))

# ---- PROP_Bill: single double-sided bill for burst FX (2 tris, origin at centre, lying flat, 0.156 x 0.066 m)
bm_ = bmesh.new(); uvl = bm_.loops.layers.uv.new("UVMap")
_bw, _bh = 0.156, 0.066
bv = [bm_.verts.new(p) for p in ((-_bw / 2, -_bh / 2, 0), (_bw / 2, -_bh / 2, 0), (_bw / 2, _bh / 2, 0), (-_bw / 2, _bh / 2, 0))]
bf = bm_.faces.new(bv); bm_.normal_update()
_x0, _y0, _x1, _y1 = R["bill_top"]
for l, (u, v) in zip(bf.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
    l[uvl].uv = ((_x0 + 3 + u * (_x1 - _x0 - 6)) / A, (_y0 + 3 + v * (_y1 - _y0 - 6)) / A)
bme = bpy.data.meshes.new("PROP_Bill"); bm_.to_mesh(bme); bm_.free(); bme.materials.append(MAT_P)
bobj = bpy.data.objects.new("PROP_Bill", bme); coll.objects.link(bobj)
MAT_P.use_backface_culling = False

# ---- PROP_CashHeist: open crate with stacked bundles, "$4,975" label on front (-Y)
b = B("PROP_CashHeist", [MAT_P])
cw_, cd_, ch_, t = 0.52, 0.36, 0.26, 0.025
CW = 'crate_wood'
b.box((0, 0, t / 2), (cw_, cd_, t), CW)
b.box((0, -cd_ / 2 + t / 2, ch_ / 2), (cw_, t, ch_), {'-y': 'crate_label', 'default': CW})  # front with label? label replaced below
b.box((0, cd_ / 2 - t / 2, ch_ / 2), (cw_, t, ch_), CW)
b.box((-cw_ / 2 + t / 2, 0, ch_ / 2), (t, cd_ - 2 * t, ch_), CW)
b.box((cw_ / 2 - t / 2, 0, ch_ / 2), (t, cd_ - 2 * t, ch_), CW)
for sx in (-1, 1):  # corner battens
    for sy in (-1, 1):
        b.box((sx * (cw_ / 2 - 0.02), sy * (cd_ / 2 - 0.02), ch_ / 2 + 0.005), (0.04, 0.04, ch_ + 0.01), 'darkwood')
_pending = []
for layer in range(2):
    for i in range(3):
        for j in range(2):
            x = -0.15 + i * 0.15 + (0.0 if layer == 0 else 0.0); y = -0.07 + j * 0.14
            z = t + 0.04 + layer * 0.082
            _bn = len(_pending)
            _pending.append(("PROP_CashHeist_Bundle.%02d" % _bn, (x, y, z), (0.14, 0.125, 0.08)))
_ch = b.build()
for _n, _l, _s in _pending: bundle_child(_n, _ch, _l, _s)

# ---- PROP_Megaphone: wall mounted, plate on wall at y=0, horn points -Y
b = B("PROP_Megaphone", [MAT_P])
b.box((0, 0.01, 0), (0.16, 0.02, 0.16), 'gunmetal', bevel=0.004)
for dx in (-0.055, 0.055):
    for dz in (-0.055, 0.055):
        b.cyl((dx, 0.0, dz), 0.008, 0.008, 0.012, 'brass', segs=6)
b.box((0, -0.04, -0.075), (0.035, 0.1, 0.05), 'steel')
b.cyl((0, -0.11, 0), 0.075, 0.075, 0.16, 'red', segs=16)                 # body
b.cyl((0, -0.30, 0), 0.075, 0.16, 0.22, 'red', segs=16)                  # horn
b.cyl((0, -0.425, 0), 0.16, 0.175, 0.03, 'white', segs=16, front_region='black')   # rim + speaker face
b.box((0, -0.12, -0.12), (0.05, 0.055, 0.12), 'rubber', bevel=0.006)    # handle
b.box((0, -0.075, -0.1), (0.02, 0.02, 0.04), 'cyan')                     # trigger/led
b.cyl((0, -0.11, 0), 0.082, 0.082, 0.03, 'steel', segs=16)               # mount clamp
b.build()

# ---- PROP_WantedPoster: wood frame + poster plane (MAT_PosterRuntime), faces -Y
b = B("PROP_WantedPoster", [MAT_P, MAT_POSTER])
fw, fh, fd, fb = 0.60, 0.85, 0.03, 0.055
b.box((0, 0, fh / 2 - fb / 2), (fw, fd, fb), 'darkwood', bevel=0.004)
b.box((0, 0, -fh / 2 + fb / 2), (fw, fd, fb), 'darkwood', bevel=0.004)
b.box((-fw / 2 + fb / 2, 0, 0), (fb, fd, fh - 2 * fb), 'darkwood', bevel=0.004)
b.box((fw / 2 - fb / 2, 0, 0), (fb, fd, fh - 2 * fb), 'darkwood', bevel=0.004)
b.box((0, 0.011, 0), (fw - 2 * fb, 0.008, fh - 2 * fb), 'darkwood')
b.quad((0, 0.0, 0), (fw - 2 * fb, fh - 2 * fb), (0, 0, 0), 1)
b.build()

# ---- PROP_Terminal: kiosk terminal, faces -Y
b = B("PROP_Terminal", [MAT_P, MAT_SCREEN])
b.box((0, 0, 0.02), (0.34, 0.26, 0.04), 'gunmetal', bevel=0.006)
b.box((0, 0.04, 0.13), (0.1, 0.08, 0.18), 'gunmetal', bevel=0.005)
tilt = math.radians(-12)
mc = Vector((0, 0.0, 0.34))
b.box(mc, (0.46, 0.05, 0.32), 'bezel', rot=(tilt, 0, 0), bevel=0.006)
fwd = Matrix.Rotation(tilt, 3, 'X') @ Vector((0, -1, 0))
b.quad(mc + fwd * 0.0255, (0.40, 0.25), (tilt, 0, 0), 1)
b.box((0, -0.13, 0.055), (0.30, 0.1, 0.02), 'black', rot=(math.radians(-8), 0, 0), bevel=0.003)
b.box((0.0, -0.125, 0.044), (0.31, 0.11, 0.01), 'gunmetal')
b.box((0.18, -0.05, 0.05), (0.05, 0.1, 0.02), 'cyan', bevel=0.003)  # card slot LED strip
b.build()

for o in coll.objects:
    if o.parent: continue
    me = o.data
    bpy.context.view_layer.objects.active = o
    print("PROP", o.name, "tris", sum(len(p.vertices) - 2 for p in me.polygons), "mats", [m.name for m in me.materials])
bpy.ops.wm.save_as_mainfile(filepath=ENV + r"\PROPS.blend")





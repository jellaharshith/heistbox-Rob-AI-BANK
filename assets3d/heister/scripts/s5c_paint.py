"""Stage 5c: paint BaseColor / ORM / Normal textures (1024) from UV-space position maps + baked AO / normal. Writes textures/*.png"""
import bpy, os, sys, json
import numpy as np
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
sys.path.insert(0, os.path.join(H, "scripts"))
from rast import raster, dilate
from noise import vnoise, fbm, ss, seg_dist
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s5hi.blend"))
O = bpy.data.objects
C = json.load(open(os.path.join(H, "scripts", "ctx.json")))
RES = 1024
objs = [O["CHAR_Heister_Body"], O["CHAR_Heister_Mask"], O["CHAR_Heister_Duffel"]]
R = raster(objs, RES)
filled = R["filled"]
arrs = [R["pos"], R["nrm"], R["part"], R["mpu"]]
dilate(arrs, filled, 12)
pos, nrm, part, mpu = R["pos"], R["nrm"], np.rint(R["part"]).astype(int), R["mpu"]
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
# world-ish texel coordinates (metres) for isotropic fabric patterns
gx, gy = np.meshgrid(np.arange(RES) + 0.5, np.arange(RES) + 0.5)
WU = gx / RES * mpu; WV = gy / RES * mpu
bake_n = np.load(os.path.join(H, "textures", "bake_normal.npy"))[..., :3]
bake_ao = np.load(os.path.join(H, "textures", "bake_ao.npy"))[..., 0]
eye_z = C["eye_z"]; hc = np.array(C["hc"]); hem = C["hem_z"]; neck = C["neck_z"]; fz = C["foot_z"]
cL = np.array(C["eyeL"]); cR = np.array(C["eyeR"])

def rgb(r, g, b):
    return np.array([r, g, b], np.float32) / 255.0

def mix(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]

def setc(img, m, color):
    img[m] = color

def tri(x):
    return np.abs(2 * (x - np.floor(x + 0.5)))

img = np.zeros((RES, RES, 3), np.float32) + rgb(120, 120, 120)
rough = np.full((RES, RES), 0.8, np.float32)
metal = np.zeros((RES, RES), np.float32)
height = np.zeros((RES, RES), np.float32)      # metres of fabric relief
P3 = pos
n1 = fbm(P3, 90, 3, 1); n2 = fbm(P3, 600, 2, 2); n3 = fbm(P3, 25, 3, 3)

# =================================================================== SKIN
m = part == 1
skin = rgb(190, 142, 116)
c = np.broadcast_to(skin, img.shape).copy()
c *= (0.92 + 0.16 * n1)[..., None]
c = c * (0.96 + 0.08 * n2)[..., None]
# cheeks / nose flush, forehead lighter
for cx in (cL[0], cR[0]):
    d = np.hypot(X - cx * 1.35, (Z - (eye_z - 0.04)) * 1.2)
    c = mix(c, rgb(205, 120, 105), 0.35 * ss(0.045, 0.0, d))
dn = np.hypot(X, Z - (eye_z - 0.04))
c = mix(c, rgb(200, 118, 100), 0.25 * ss(0.02, 0.0, dn))
c = mix(c, rgb(214, 168, 140), 0.25 * ss(eye_z + 0.02, eye_z + 0.05, Z))       # forehead
# eye sockets shadow
for ce in (cL, cR):
    d = np.hypot(X - ce[0], (Z - ce[2]) * 1.6)
    c = mix(c, rgb(120, 80, 75), 0.35 * ss(0.034, 0.012, d) * (Y < hc[1] - 0.03))
# ears
ear = (np.abs(X) > 0.068) & (Y > hc[1] - 0.04) & (Y < hc[1] + 0.05) & (Z > eye_z - 0.07) & (Z < eye_z + 0.03)
c = mix(c, rgb(205, 125, 110), 0.35 * ear.astype(np.float32))
# neck darker + hands tone variation
c = mix(c, rgb(165, 120, 98), 0.4 * ss(neck + 0.1, neck + 0.0, Z))
# lips
lipz = eye_z - 0.072
lips = ss(0.014, 0.008, np.hypot((X) / 1.6, Z - lipz)) * (Y < hc[1] - 0.03)
c = mix(c, rgb(168, 94, 92), 0.9 * lips)
# eyebrows
for ce, s in ((cL, 1), (cR, -1)):
    bx = (X - ce[0]) * s
    cen = 0.003
    bz = Z - (eye_z + 0.028 + 0.006 * bx / 0.02)
    inb = ((bx - cen) / 0.024) ** 2 + (bz / (0.0048 * (1 - 0.5 * ss(0.0, 0.024, bx)))) ** 2
    brow = ss(1.0, 0.55, inb) * (0.75 + 0.25 * fbm(P3, 1200, 1, 5)) * (Y < hc[1] - 0.04)
    c = mix(c, rgb(46, 31, 24), np.clip(brow, 0, 0.92))
# lashes / lid line
for ce in (cL, cR):
    q = ((X - ce[0]) / 0.0155) ** 2 + ((Z - (ce[2] + 0.002)) / 0.0075) ** 2
    lash = ss(0.55, 0.95, q) * ss(1.45, 1.05, q) * (Z > ce[2] - 0.002) * (Y < hc[1] - 0.04)
    c = mix(c, rgb(34, 24, 20), 0.85 * lash)
# buzz-cut hair / sideburns / nape
hair_top = ss(eye_z - 0.02, eye_z + 0.012, Z) * (((np.abs(X) > 0.074).astype(np.float32)) + (Y > hc[1] + 0.0)).clip(0, 1)
hair_nape = ss(eye_z - 0.085, eye_z - 0.05, Z) * ss(hc[1] + 0.02, hc[1] + 0.06, Y) * ss(eye_z - 0.0, eye_z - 0.03, Z)
side = ss(eye_z - 0.045, eye_z - 0.015, Z) * ss(0.065, 0.085, np.abs(X)) * (Y < hc[1] + 0.02) * (Y > hc[1] - 0.04)
stip = fbm(P3, 900, 2, 7)
hair = np.clip(np.maximum.reduce([hair_top, hair_nape, side * 0.8]) * (0.45 + stip * 0.9), 0, 1)
hair = np.where(Z > eye_z - 0.1, hair, 0)
c = mix(c, rgb(30, 22, 18), hair * 0.88)
# stubble on jaw / cheeks (lower face, partly under mask)
stub = ss(eye_z - 0.02, eye_z - 0.06, Z) * (np.abs(X) < 0.075) * (Z > eye_z - 0.12) * (Y < hc[1] - 0.02) * (fbm(P3, 1100, 1, 8) > 0.5)
c = mix(c, rgb(110, 80, 68), 0.0 * stub)
img[m] = c[m]
rough[m] = (0.52 + 0.12 * n1 - 0.08 * ss(eye_z - 0.06, eye_z + 0.0, Z) * (np.abs(X) < 0.03) + 0.1 * hair)[m]
height[m] = (0.00015 * n2)[m]

# =================================================================== HOODIE / HOOD / CORDS
hood_c = rgb(33, 35, 41)
m = np.isin(part, [2, 11])
c = np.broadcast_to(hood_c, img.shape).copy()
c *= (0.88 + 0.28 * n1)[..., None] * (0.94 + 0.12 * n2)[..., None]
band = ss(hem + 0.07, hem + 0.045, Z) * (Z > hem - 0.02)
c = mix(c, rgb(26, 27, 32), 0.6 * band)
# stitch lines (pocket outline) + hem seam
ztop = hem + 0.19
front = (nrm[..., 1] < -0.35)
dash = (np.sin(WU * 2 * np.pi / 0.006 + WV * 2 * np.pi / 0.006) > 0)
st = np.zeros(RES * RES, np.float32).reshape(RES, RES)
for s in (1, -1):
    dd = seg_dist(X * s, Z, (0.165, ztop - 0.005), (0.105, ztop - 0.095))
    st = np.maximum(st, ss(0.0025, 0.0010, dd))
st = np.maximum(st, ss(0.0012, 0.0004, np.abs(Z - (hem + 0.052))) * (np.abs(X) < 0.5))
c = mix(c, rgb(78, 80, 92), 0.7 * st * dash * front)
# elbow wear / shoulder fade
for s in (1, -1):
    e = np.array(C["elbow"]) * np.array([s, 1, 1])
    d = np.linalg.norm(pos - e, axis=2)
    c = mix(c, rgb(55, 57, 66), 0.35 * ss(0.1, 0.0, d))
# small chest print (white bracket glyph) to give the hoodie character
gl = (np.abs(X) < 0.045) & (np.abs(Z - (neck - 0.095)) < 0.032) & front
frame = ((np.abs(np.abs(X) - 0.045) < 0.0035) & (np.abs(Z - (neck - 0.095)) < 0.032)) | ((np.abs(np.abs(Z - (neck - 0.095)) - 0.032) < 0.0035) & (np.abs(X) < 0.045))
frame = frame & (tri(X * 40) > 0.15) & front
c = mix(c, rgb(205, 190, 140), 0.85 * frame.astype(np.float32))
img[m] = c[m]
rough[m] = (0.9 - 0.08 * st)[m]
height[m] = (0.0004 * fbm(np.stack([WU, WV, WU * 0], -1), 330, 2, 21))[m]
# cords
m = part == 10
cord = np.broadcast_to(rgb(196, 190, 172), img.shape).copy() * (0.9 + 0.2 * n2)[..., None]
zc = Z[m].min() if m.any() else 0
tip = ss(zc + 0.024, zc + 0.016, Z)
cord = mix(cord, rgb(190, 150, 60), tip)
img[m] = cord[m]; rough[m] = (0.75 - 0.35 * tip)[m]; metal[m] = (0.8 * tip)[m]

# =================================================================== PANTS / POCKETS
m = np.isin(part, [3, 12])
pc = np.broadcast_to(rgb(56, 59, 43), img.shape).copy()
pc *= (0.86 + 0.3 * n1)[..., None] * (0.93 + 0.14 * n2)[..., None]
twill = 0.5 + 0.5 * np.sin((WU + WV) * 2 * np.pi / 0.0032)
pc *= (0.95 + 0.07 * twill)[..., None]
pc = mix(pc, rgb(72, 76, 56), 0.45 * (part == 12))
# dirt at ankles/knees
pc = mix(pc, rgb(70, 60, 44), 0.6 * ss(fz + 0.28, fz + 0.06, Z) * (0.5 + 0.5 * n3))
for s in (1, -1):
    k = np.array(C["knee"]) * np.array([s, 1, 1])
    d = np.linalg.norm(pos - k, axis=2)
    pc = mix(pc, rgb(80, 82, 62), 0.3 * ss(0.12, 0.02, d))
# side seam stitch
seam = ss(0.0025, 0.0008, np.abs(np.abs(X) - C["thigh_outer"])) * (Z > fz + 0.1)
pc = mix(pc, rgb(96, 98, 70), 0.6 * seam * dash)
# button-flap pocket stitch
img[m] = pc[m]
rough[m] = (0.88 - 0.05 * twill)[m]
height[m] = (0.00035 * twill)[m]

# =================================================================== SHOES
m = part == 4
ymin = C["shoe_ymin"]
sc_ = np.broadcast_to(rgb(206, 204, 197), img.shape).copy() * (0.93 + 0.12 * n1)[..., None]
sc_ = mix(sc_, rgb(150, 138, 120), 0.65 * ss(0.08, 0.034, Z) * (0.4 + 0.6 * n3))            # dirt near sole
sc_ = mix(sc_, rgb(188, 186, 180), ss(ymin + 0.075, ymin + 0.06, Y))                        # toe cap
lac = (np.abs(np.abs(X) - C["foot_x"]) < 0.03) & (Y > ymin + 0.065) & (Y < ymin + 0.19) & (nrm[..., 2] > 0.25)
sc_ = mix(sc_, rgb(238, 238, 232), 0.9 * lac * (0.5 + 0.5 * np.clip(np.sin(Y * 2 * np.pi / 0.0165) * 1.5, 0, 1)))
# accent swoosh + heel tab
sw = seg_dist(Y, Z, (ymin + 0.12, 0.042), (ymin + 0.28, 0.105))
sc_ = mix(sc_, rgb(32, 44, 80), ss(0.0085, 0.0045, sw) * (np.abs(X) > 0.04))
ymax = Y[m].max() if m.any() else 0
sc_ = mix(sc_, rgb(32, 44, 80), ss(ymax - 0.055, ymax - 0.04, Y) * ss(0.06, 0.075, Z))
# sole wall + outsole
sole = ss(0.037, 0.031, Z)
sc_ = mix(sc_, rgb(232, 224, 200), sole)
sc_ = mix(sc_, rgb(88, 70, 52), ss(0.012, 0.004, Z))
img[m] = sc_[m]
rough[m] = (0.55 + 0.22 * sole)[m]
height[m] = (0.0004 * n2)[m]

# =================================================================== GLOVES
m = part == 5
gc = np.broadcast_to(rgb(26, 24, 24), img.shape).copy() * (0.8 + 0.5 * n1)[..., None]
gc = mix(gc, rgb(52, 50, 50), 0.4 * ss(0.4, 0.8, nrm[..., 2]) * (n3 > 0.5))
gc = mix(gc, rgb(90, 90, 90), 0.35 * ss(0.0012, 0.0004, np.abs(tri(WU * 2 * np.pi / 0.0078 / (2 * np.pi)) - 0.5)) * dash)
img[m] = gc[m]
rough[m] = (0.48 + 0.2 * n2)[m]
height[m] = (0.0006 * n2)[m]

# =================================================================== BEANIE
m = part == 6
ang = np.arctan2(X, Y - hc[1])
rib = tri(ang * 56 / (2 * np.pi))
s_back = np.clip((Y - (hc[1] - 0.03)) / 0.09, 0, 1)
thr = eye_z + 0.028 - 0.085 * s_back + 0.04 * ss(0.065, 0.09, np.abs(X)) * (1 - s_back)
bc = np.broadcast_to(rgb(30, 31, 36), img.shape).copy() * (0.85 + 0.3 * n1)[..., None]
bc *= (0.8 + 0.4 * rib)[..., None] * (0.93 + 0.14 * n2)[..., None]
cuff = ss(thr + 0.042, thr + 0.036, Z)
bc = mix(bc, rgb(48, 49, 56), 0.7 * cuff)
img[m] = bc[m]
rough[m] = 0.93
height[m] = (0.0018 * rib)[m]

# =================================================================== MASK
m = part == 7
mc = np.broadcast_to(rgb(15, 15, 17), img.shape).copy() * (0.8 + 0.5 * n1)[..., None]
grid = 0.5 + 0.5 * np.sin(WU * 2 * np.pi / 0.0026) * np.sin(WV * 2 * np.pi / 0.0026)
mc *= (0.9 + 0.2 * grid)[..., None]
# zipper-mouth graphic
lz = eye_z - 0.072
mline = ss(0.0014, 0.0006, np.abs(Z - lz)) * (np.abs(X) < 0.034)
tick = (tri(X * 1.0 / 0.0075) > 0.5) * ss(0.0065, 0.0055, np.abs(Z - lz)) * (np.abs(X) < 0.034)
teeth = np.maximum(mline, 0.9 * tick * (np.abs(Z - lz) > 0.0014))
mc = mix(mc, rgb(214, 210, 200), 0.9 * np.clip(teeth, 0, 1))
img[m] = mc[m]
rough[m] = 0.92
height[m] = (0.0004 * grid)[m]
metal[m] = (0.0 * mline)[m]

# =================================================================== DUFFEL
m = part == 8
cx_, cy_, cz_ = C["duffel_c"]; R_ = C["duffel_r"]; L_ = C["duffel_L"]
rr = np.hypot(Y - cy_, Z - cz_)
bag = (rr < R_ * 1.1) & (np.abs(X) < L_ + 0.03)
handle = (~bag) & (rr < R_ + 0.085) & (Z > cz_ + R_ * 0.9) & (np.abs(X) < 0.11)
dc = np.broadcast_to(rgb(92, 80, 50), img.shape).copy() * (0.85 + 0.3 * n1)[..., None]
cross = 0.5 + 0.5 * np.sin(WU * 2 * np.pi / 0.0030) * np.sin(WV * 2 * np.pi / 0.0030)
dc *= (0.92 + 0.12 * cross)[..., None]
dc = mix(dc, rgb(52, 47, 36), ss(L_ * 0.74, L_ * 0.78, np.abs(X)))        # end panels
zipm = ss(0.0075, 0.0035, np.abs(Y - cy_)) * (Z > cz_ + R_ * 0.7) * bag
dc = mix(dc, rgb(176, 152, 80), zipm * (0.5 + 0.5 * (tri(X / 0.0054) > 0.5)))
# logo patch on the back face
patch = (Y > cy_ + R_ * 0.55) & (np.abs(X) < 0.075) & (np.abs(Z - cz_) < 0.045) & bag
dc = mix(dc, rgb(150, 28, 30), 0.95 * patch)
inner = (Y > cy_ + R_ * 0.55) & (np.abs(X) < 0.066) & (np.abs(Z - cz_) < 0.036) & (np.abs(np.abs(X) - 0.066) < 0.003) & bag
dc = mix(dc, rgb(230, 225, 210), 0.9 * inner)
dc = mix(dc, rgb(30, 30, 32), ((~bag) & ~handle).astype(np.float32))          # webbing straps
dc = mix(dc, rgb(74, 46, 30), handle.astype(np.float32))                      # leather handles
img[m] = dc[m]
rough[m] = np.where(handle, 0.5, np.where(bag, 0.82, 0.7))[m]
metal[m] = (0.6 * zipm)[m]
height[m] = (0.0005 * cross)[m]

# =================================================================== EYES (reserved box)
u0, v0, sz = json.load(open(os.path.join(H, "scripts", "uvinfo.json")))["eye_box"]
px0, py0, pw = int(u0 * RES), int(v0 * RES), int(sz * RES)
ex, ey = np.meshgrid(np.arange(RES) + 0.5, np.arange(RES) + 0.5)
a = ((ex / RES - u0) / sz) * 2 - 1
b = ((ey / RES - v0) / sz) * 2 - 1
inbox = (np.abs(a) <= 1.0) & (np.abs(b) <= 1.0)
r = np.hypot(a, b)
ang = np.arctan2(b, a)
sclera = rgb(226, 218, 208) * (1 - 0.18 * ss(0.55, 1.0, r))[..., None]
sclera = mix(sclera, rgb(200, 120, 110), 0.25 * ss(0.8, 1.0, r) * (fbm(np.stack([ang * 3, r * 3, 0 * r], -1), 2, 2, 31) > 0.55))
iris_c = mix(np.broadcast_to(rgb(92, 150, 120) * 0.0 + rgb(105, 66, 36), img.shape).copy(), rgb(150, 112, 62), ss(0.18, 0.4, r))
iris_c *= (0.8 + 0.4 * fbm(np.stack([ang * 6, r * 8, 0 * r], -1), 1.0, 2, 33))[..., None]
iris_c = mix(iris_c, rgb(38, 24, 16), ss(0.38, 0.46, r))
e = mix(sclera, iris_c, ss(0.47, 0.44, r))
e = mix(e, rgb(6, 6, 6), ss(0.2, 0.17, r))
hl = np.hypot(a + 0.16, b - 0.16)
e = mix(e, rgb(255, 255, 255), ss(0.075, 0.05, hl))
e = mix(e, rgb(255, 255, 255), 0.7 * ss(0.035, 0.02, np.hypot(a - 0.14, b + 0.14)))
img[inbox] = e[inbox]
rough[inbox] = (0.12 + 0.0 * r)[inbox]
metal[inbox] = 0
height[inbox] = 0

# =================================================================== AO / roughness / normal composition
img = np.clip(img, 0, 1)
ao = np.clip(bake_ao, 0, 1)
ao = ao * 0.75 + 0.25
ao[inbox] = 1.0
orm = np.stack([ao, np.clip(rough, 0.05, 1), np.clip(metal, 0, 1)], -1)
# normal: baked + fabric relief
nb = bake_n * 2 - 1
nb[bake_n[..., 2] < 0.45] = np.array([0, 0, 1], np.float32)       # rays that hit hidden/unrelated surface -> flat
texel = np.maximum(mpu / RES, 1e-5)
gyh, gxh = np.gradient(height)
dn = np.stack([-gxh / texel, -gyh / texel, np.zeros_like(height)], -1)
dn[inbox] = 0
nn = nb + dn * 1.0
nn[..., 2] = np.maximum(nn[..., 2], 0.2)
nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
nn[inbox] = np.array([0, 0, 1], np.float32)
normal = nn * 0.5 + 0.5
out = {"Heister_BaseColor": img, "Heister_ORM": orm, "Heister_Normal": normal}
for name, arr in out.items():
    a4 = np.concatenate([arr, np.ones((RES, RES, 1), np.float32)], -1).astype(np.float32)
    im = bpy.data.images.new(name, RES, RES, alpha=False)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(a4.ravel())
    im.filepath_raw = os.path.join(H, "textures", name + ".png")
    im.file_format = 'PNG'
    im.save()
    print("saved", name)




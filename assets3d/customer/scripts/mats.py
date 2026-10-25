# procedural materials (evaluated on HI / own parts and baked)
import bpy
from dsl import *

EC = (0.02994, -0.12812, 1.67712)   # eye centre (left); right is mirrored
EYE_R = 0.0132

def lin(r, g, b):  # sRGB 0-255 -> linear tuple
    f = lambda c: ((c / 255.0) / 12.92) if c / 255.0 <= 0.04045 else (((c / 255.0) + 0.055) / 1.055) ** 2.4
    return (f(r), f(g), f(b))

def new_mat(name):
    m = bpy.data.materials.new(name); return m, NB(m)

def mat_skin():
    m, nb = new_mat("BK_skin")
    x, y, z, P = pos(); ax = absv(x)
    ez = EC[2]; ex = EC[0]
    n_big = noise(P, 7.0, 2.0); n_pore = noise(P, 220.0, 3.0, 0.6); n_mid = noise(P, 45.0, 3.0)
    base = mixc(n_big, lin(196, 140, 112), lin(214, 156, 124))
    col = mulc(base, 0.88 + 0.24 * n_pore)
    front = step(-0.085, -0.115, y)
    # cheek blush
    dc = sqrtv((ax - 0.043) * (ax - 0.043) + (z - (ez - 0.040)) * (z - (ez - 0.040)))
    col = mixc(front * step(0.032, 0.004, dc) * 0.5, col, lin(205, 110, 98))
    # nose tip / nostril warmth
    dn = sqrtv(x * x + (z - (ez - 0.047)) * (z - (ez - 0.047)))
    col = mixc(front * step(0.016, 0.003, dn) * 0.35, col, lin(208, 118, 100))
    # under-eye shadow
    de = sqrtv((ax - ex) * (ax - ex) + (z - (ez - 0.012)) * (z - (ez - 0.012)))
    col = mixc(front * step(0.022, 0.006, de) * 0.35, col, lin(140, 100, 100))
    # eyebrows
    zc = ez + 0.0215 + 0.0075 * (1 - ((ax - 0.040) * (ax - 0.040)) / (0.026 * 0.026))
    th = 0.0046 * (1 - 0.65 * step(0.034, 0.062, ax)) + 0.0006
    dz = absv(z - zc)
    brow = step(th, th * 0.35, dz) * step(0.008, 0.016, ax) * step(0.066, 0.054, ax) * front
    brow = brow * (0.75 + 0.25 * n_mid)
    col = mixc(brow * 0.92, col, lin(42, 28, 20))
    # stubble / shadow on lower face
    jaw = step(ez - 0.040, ez - 0.062, z) * step(ez - 0.115, ez - 0.095, z) * front * step(0.07, 0.045, ax)
    stub = jaw * step(0.5, 0.75, n_pore) * 0.55 + jaw * 0.12
    col = mixc(stub, col, lin(95, 70, 62))
    # lips / ears / nails
    lips = attr("lips"); ears = attr("ears"); nails = attr("fingernails")
    col = mixc(step(0.2, 0.7, lips), col, lin(176, 92, 88))
    col = mixc(step(0.2, 0.7, ears) * 0.45, col, lin(205, 118, 100))
    col = mixc(step(0.2, 0.7, nails) * 0.7, col, lin(230, 175, 160))
    # knuckles / hands redness
    rough = 0.55 + 0.18 * (n_pore - 0.5) + step(0.2, 0.7, lips) * (-0.2) + step(0.2, 0.7, nails) * (-0.28)
    finish(nb, col, rough, 0.0, 1.0)
    return m

def mat_jacket():
    m, nb = new_mat("BK_jacket")
    x, y, z, P = pos(); ax = absv(x)
    canvas = lin(176, 128, 62)
    n1 = noise(P, 180.0, 2.0); n2 = noise(P, 9.0, 3.0)
    # weave
    weave = 0.5 + 0.5 * sinv(z * 1500.0) * sinv(x * 1500.0 + y * 1500.0)
    col = mulc(mixc(n2, lin(168, 120, 56), lin(188, 138, 70)), 0.90 + 0.10 * weave + 0.06 * (n1 - 0.5))
    # rib knit: hem, collar, cuffs
    wl = sqrtv(0.0 * x + 1.0) * 0.0
    rib_hem = step(1.005, 0.975, z) * step(1.2, 0.5, z)       # lower body only
    rib_col = step(1.545, 1.56, z)
    rib = vmax(rib_hem, rib_col)
    xs = fract(x * 150.0 + y * 150.0)
    ribpat = 0.75 + 0.25 * sinv(x * 700.0 + y * 700.0 + 10.0 * z)
    col = mixc(rib * 0.95, col, mulc(lin(70, 52, 38), ribpat))
    # zipper (centre front)
    zip_m = step(0.0032, 0.0016, ax) * step(-0.05, -0.09, y) * step(1.56, 1.55, z) * step(0.96, 0.98, z)
    teeth = 0.5 + 0.5 * sinv(z * 900.0)
    col = mixc(zip_m, col, mulc(lin(185, 180, 170), 0.6 + 0.4 * teeth))
    # slash pockets (angled lines)
    pk = absv(z - (1.07 - 0.28 * (ax - 0.17))) 
    pk_line = step(0.0021, 0.0008, pk) * step(0.13, 0.15, ax) * step(0.215, 0.195, ax) * step(-0.0, -0.06, y)
    col = mixc(pk_line * 0.8, col, lin(88, 60, 26))
    # chest patch
    patch = step(0.0, 0.003, 0.045 - absv(x - 0.085)) * step(0.0, 0.003, 0.028 - absv(z - 1.40)) * step(-0.06, -0.09, y)
    col = mixc(patch, col, lin(32, 74, 98))
    # shoulder / side seams
    seam = step(0.0017, 0.0007, absv(ax - 0.176)) * step(1.5, 1.45, z) * step(0.0, 0.01, y + 0.0) * 0.0
    # wear
    col = mulc(col, 0.93 + 0.07 * noise(P, 3.0, 4.0))
    rough = 0.82 - 0.1 * zip_m + 0.12 * rib + 0.05 * (n1 - 0.5)
    metal = zip_m * step(0.55, 0.9, teeth) * 0.0 + zip_m * 1.0
    finish(nb, col, rough, metal, 1.0)
    return m

def mat_jeans():
    m, nb = new_mat("BK_jeans")
    x, y, z, P = pos(); ax = absv(x)
    n1 = noise(P, 150.0, 2.0); n2 = noise(P, 6.0, 4.0, 0.6); n3 = noise(P, 22.0, 3.0)
    twill = 0.5 + 0.5 * sinv((z * 1.0 + x * 0.7 + y * 0.7) * 1200.0)
    base = mixc(n2, lin(46, 68, 108), lin(78, 108, 150))
    col = mulc(base, 0.86 + 0.10 * twill + 0.08 * (n1 - 0.5))
    # fade at thighs/knees and hem
    fade = step(0.45, 0.75, n3) * step(0.25, 0.55, z) * 0.4 + step(0.12, 0.05, z) * 0.35
    col = mixc(fade, col, lin(120, 150, 185))
    # fly seam + stitching
    fly = step(0.0028, 0.0012, ax) * step(-0.05, -0.09, y) * step(1.0, 0.95, z) * step(0.80, 0.86, z)
    col = mixc(fly * 0.9, col, lin(205, 140, 60))
    # side seams
    sd = step(0.0018, 0.0007, absv(absv(x) - 0.205 + (0.0)))
    # waistband
    wb = step(0.0012, 0.0004, absv(z - 1.03)) 
    col = mixc(wb * 0.6, col, lin(205, 140, 60))
    rough = 0.88 + 0.08 * (n1 - 0.5) - 0.1 * fade
    finish(nb, col, rough, 0.0, 1.0)
    return m

def mat_shoes():
    m, nb = new_mat("BK_shoes")
    x, y, z, P = pos(); ax = absv(x)
    n1 = noise(P, 90.0, 3.0); n2 = noise(P, 12.0, 3.0)
    upper = mulc(lin(228, 226, 218), 0.88 + 0.12 * n2)
    sole = mulc(lin(214, 190, 150), 0.9 + 0.1 * n1)
    col = mixc(step(0.032, 0.022, z), upper, sole)
    # toe cap darker rubber and heel tab accent
    toe = step(-0.17, -0.20, y) * step(0.07, 0.05, z)
    col = mixc(toe * 0.5, col, lin(190, 188, 180))
    # laces
    lace = step(0.5, 0.8, 0.5 + 0.5 * sinv(y * 520.0)) * step(0.075, 0.09, z) * step(0.03, 0.02, ax - 0.19 + 0.19) * step(-0.05, -0.17, y) * step(0.13, 0.11, z)
    col = mixc(lace * 0.6, col, lin(250, 250, 245))
    # accent stripe
    stripe = step(0.0035, 0.0015, absv(z - 0.056)) * step(-0.04, -0.12, y)
    col = mixc(stripe, col, lin(170, 40, 36))
    col = mulc(col, 0.9 + 0.1 * noise(P, 3.0, 4.0))
    rough = 0.55 + 0.35 * step(0.032, 0.022, z) + 0.1 * (n1 - 0.5)
    finish(nb, col, rough, 0.0, 1.0)
    return m

def mat_eyes():
    m, nb = new_mat("BK_eyes")
    x, y, z, P = pos(); ax = absv(x)
    dx = ax - EC[0]; dz = z - EC[2]
    r = sqrtv(dx * dx + dz * dz)
    ang = atan2(dz, dx)
    streak = noise(combine(ang * 3.0, r * 220.0, 0.0), 6.0, 2.0)
    iris_in = mixc(streak, lin(120, 78, 36), lin(70, 42, 20))
    iris = mixc(step(0.0034, 0.0062, r), lin(150, 105, 50), iris_in)
    limbus = step(0.0056, 0.0066, r)
    col = mixc(step(0.0067, 0.0059, r), lin(232, 224, 214), mixc(limbus * 0.9, iris, lin(26, 18, 12)))
    # sclera slight veining/shade toward corners
    col = mixc(step(0.0067, 0.0059, r) * 0.0 + (1 - step(0.0067, 0.0059, r)) * step(0.008, 0.013, r) * 0.4, col, lin(190, 150, 140))
    pupil = step(0.0027, 0.0021, r)
    col = mixc(pupil, col, lin(6, 5, 5))
    hl = sqrtv((dx + 0.0028) * (dx + 0.0028) + (dz - 0.0034) * (dz - 0.0034))
    col = mixc(step(0.0017, 0.0010, hl), col, (1.0, 1.0, 1.0))
    hl2 = sqrtv((dx - 0.0030) * (dx - 0.0030) + (dz + 0.0030) * (dz + 0.0030))
    col = mixc(step(0.0009, 0.0005, hl2) * 0.5, col, (1.0, 1.0, 1.0))
    finish(nb, col, 0.12, 0.0, 1.0)
    return m

def mat_hair_cap():
    m, nb = new_mat("BK_hair_cap")
    u, v = uvmap("UVHair")
    du = u - 0.5; dv = v - 0.5
    r = sqrtv(du * du + dv * dv); ang = atan2(dv, du)
    # position for noise
    streak = noise(combine(ang * 6.0, r * 40.0, 0.0), 14.0, 4.0, 0.7)
    fine = noise(combine(ang * 40.0, r * 60.0, 1.0), 20.0, 2.0)
    col = mixc(streak, lin(40, 26, 18), lin(92, 62, 40))
    col = mulc(col, 0.8 + 0.4 * fine)
    finish(nb, col, 0.55 + 0.2 * streak, 0.0, 1.0)
    return m

def card_local():
    """region-local tile coordinates from UVHair (atlas strip): returns (lu, lv, var)"""
    u, v = uvmap("UVHair")   # UVHair on cards = (U, V - 0.89) in atlas units
    return u, v

def mat_hair_cards():
    m, nb = new_mat("BK_hair_cards")
    u, v = uvmap("UVHair")
    var = fn1('FLOOR', u * 10.0 + 0.0001) if False else None
    lu = fract(u * 10.0)                     # 0..1 within tile
    tv = 1.0 - v / 0.11                      # 0 root .. 1 tip
    vid = (u * 10.0) - lu                    # tile id as float
    # strands along v
    s1 = noise(combine(lu * 18.0, vid * 7.0, tv * 1.2), 3.0, 3.0, 0.6)
    s2 = noise(combine(lu * 40.0, vid * 3.0, tv * 0.6), 2.0, 2.0)
    col = mixc(s1, lin(34, 22, 15), lin(98, 66, 42))
    col = mulc(col, 0.75 + 0.5 * s2)
    root_dark = step(0.0, 0.35, tv)
    col = mulc(col, 0.55 + 0.45 * root_dark)
    # lock shape: width tapers to a point, slight asymmetry per tile
    half = 0.5 * (1.0 - tv ** 1.6) + 0.04
    cen = 0.5 + 0.08 * sinv(vid * 5.0 + tv * 3.0)
    inside = step(half, half - 0.18, absv(lu - cen)) 
    streak_gap = step(0.25, 0.4, s2) * 0.35 + 0.65
    alpha = inside * streak_gap * step(1.0, 0.92, tv)
    finish(nb, col, 0.6, 0.0, alpha)
    return m

def mat_lashes():
    m, nb = new_mat("BK_lashes")
    u, v = uvmap("UVHair")                  # (U - 0.5 offset not applied): U in [0.5,0.75]
    lu = (u - 0.5) / 0.25
    tv = v / 0.11
    stripe = 0.5 + 0.5 * sinv(lu * 150.0)
    lashmask = step(0.45, 0.7, stripe)
    length = 0.75 + 0.25 * sinv(lu * 37.0)
    alpha = lashmask * step(length, length - 0.2, tv) * step(0.0, 0.05, tv) + step(0.18, 0.05, tv) * 0.95
    alpha = clamp01(alpha)
    finish(nb, lin(14, 10, 9), 0.5, 0.0, alpha)
    return m


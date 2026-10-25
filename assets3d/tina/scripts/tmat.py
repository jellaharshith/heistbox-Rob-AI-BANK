"""Procedural bake-source materials + painted hair/eye/lash textures for Tina (numpy)."""
import sys, math
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
import bpy, numpy as np
import bake_utils as bk

# face decal frame (object-space front projection)
DX0, DX1 = -0.09, 0.09
DZ0, DZ1 = 1.36, 1.60


# ------------------------------------------------------------------ numpy drawing helpers
def _grid(w, h, x0, x1, z0, z1):
    xs = np.linspace(x0, x1, w, dtype=np.float32)
    zs = np.linspace(z0, z1, h, dtype=np.float32)
    X, Z = np.meshgrid(xs, zs)       # row 0 = z0 (bottom, as Blender images)
    return X, Z


def soft(d, edge):
    """1 inside (d<0), 0 outside, smooth over `edge` metres."""
    return np.clip(0.5 - d / edge, 0.0, 1.0)


def make_decal(w=768, h=1024):
    X, Z = _grid(w, h, DX0, DX1, DZ0, DZ1)
    rgba = np.zeros((h, w, 4), dtype=np.float32)

    def over(mask, color, strength=1.0):
        a = np.clip(mask * strength, 0, 1)[..., None]
        rgb = rgba[..., :3]
        cur_a = rgba[..., 3:4]
        out_a = a + cur_a * (1 - a)
        rgba[..., :3] = np.where(out_a > 1e-6, (np.array(color) * a + rgb * cur_a * (1 - a)) / np.maximum(out_a, 1e-6), 0)
        rgba[..., 3:4] = out_a

    rng = np.random.default_rng(3)
    ax = np.abs(X)
    # blush
    for sx in (-1, 1):
        d = np.sqrt(((X - sx * 0.052) / 0.034) ** 2 + ((Z - 1.455) / 0.026) ** 2) - 1.0
        over(np.clip(1 - np.sqrt(((X - sx * 0.052) / 0.034) ** 2 + ((Z - 1.455) / 0.026) ** 2), 0, 1) ** 1.5,
             (0.62, 0.17, 0.14), 0.22)
    # eye shadow + liner
    for sx in (-1, 1):
        ex = sx * 0.032
        d = np.sqrt(((X - ex) / 0.024) ** 2 + ((Z - 1.500) / 0.0105) ** 2)
        over(np.clip(1 - d, 0, 1) ** 1.2, (0.30, 0.15, 0.13), 0.38)
        line = np.abs(Z - (1.4930 + 0.004 * np.cos((X - ex) / 0.02 * 1.3))) - 0.0009
        over(soft(line, 0.0005) * (np.abs(X - ex) < 0.021), (0.025, 0.012, 0.01), 0.85)
    # eyebrows (arched, tapered, streaky)
    streak = 0.9 + 0.1 * np.sin(X * 2200 + np.sin(Z * 900) * 1.5) * np.sin(Z * 1800 + X * 300)
    for sx in (-1, 1):
        t = (ax - 0.012) / 0.042
        t = np.where(sx * X > 0, t, 2)
        t = np.where(t < 0, 2, t)
        zc = 1.5075 + 0.0075 * np.sin(np.clip(t, 0, 1) * math.pi * 0.92) ** 1.0 - 0.0015 * t
        half = 0.0040 * (1 - t ** 3) * (1 - 0.6 * (1 - np.clip(t / 0.25, 0, 1))) + 0.0004
        d = np.abs(Z - zc) - half
        m = soft(d, 0.0007) * (t <= 1.0)
        over(m * np.clip(streak, 0, 1), (0.030, 0.017, 0.011), 0.95)
    # lips
    lx = X / 0.0265
    inside = np.abs(lx) < 1.0
    lxc = np.clip(lx, -1, 1)
    zc = 1.4318
    up = zc + 0.0088 * (1 - lxc ** 2) ** 0.75 - 0.0022 * np.exp(-(X / 0.0035) ** 2) + 0.0014 * np.exp(-((np.abs(X) - 0.0065) / 0.004) ** 2)
    lo = zc - 0.0100 * (1 - lxc ** 2) ** 0.8
    lipm = soft(np.maximum(Z - up, lo - Z), 0.0008) * inside
    over(lipm, (0.46, 0.13, 0.14), 0.80)
    mline = soft(np.abs(Z - (zc - 0.0004 * lxc ** 2)) - 0.0005, 0.0005) * inside
    over(mline, (0.12, 0.025, 0.03), 0.9)
    # nostrils (dark under nose)
    for sx in (-1, 1):
        d = np.sqrt(((X - sx * 0.0105) / 0.0055) ** 2 + ((Z - 1.4495) / 0.0028) ** 2)
        over(np.clip(1 - d, 0, 1), (0.10, 0.03, 0.03), 0.55)
    return rgba


def decal_image(name="TinaFaceDecal"):
    rgba = make_decal()
    h, w = rgba.shape[:2]
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(rgba.ravel())
    img.alpha_mode = 'CHANNEL_PACKED'
    img.pack()
    return img


# ------------------------------------------------------------------ node helpers
class NB:
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.bsdf = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
        self.nt.links.new(self.bsdf.outputs[0], self.out.inputs[0])
        self.tc = self.n("ShaderNodeTexCoord")

    def n(self, t, **kw):
        node = self.nt.nodes.new(t)
        for k, v in kw.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def noise(self, scale, detail=3.0, rough=0.55, vec=None):
        nz = self.n("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = scale
        nz.inputs["Detail"].default_value = detail
        nz.inputs["Roughness"].default_value = rough
        self.link(vec or self.tc.outputs["Object"], nz.inputs["Vector"])
        return nz

    def mix(self, fac, a, b):
        m = self.n("ShaderNodeMix", data_type='RGBA')
        if isinstance(fac, (int, float)):
            m.inputs[0].default_value = fac
        else:
            self.link(fac, m.inputs[0])
        for i, v in ((6, a), (7, b)):
            if isinstance(v, (tuple, list)):
                m.inputs[i].default_value = (*v, 1.0) if len(v) == 3 else v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[2]

    def math(self, op, a, b=None, clamp=False):
        m = self.n("ShaderNodeMath", operation=op)
        m.use_clamp = clamp
        for i, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def bump(self, height_socket, strength, distance):
        b = self.n("ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = distance
        self.link(height_socket, b.inputs["Height"])
        self.link(b.outputs["Normal"], self.bsdf.inputs["Normal"])

    def set(self, name, v):
        if isinstance(v, (int, float)):
            self.bsdf.inputs[name].default_value = v
        elif isinstance(v, (tuple, list)):
            self.bsdf.inputs[name].default_value = (*v, 1.0) if len(v) == 3 else v
        else:
            self.link(v, self.bsdf.inputs[name])


def srgb(r, g, b):
    f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92
    return (f(r), f(g), f(b))


def mat_skin(decal):
    m = bpy.data.materials.new("HI_Skin")
    b = NB(m)
    base = b.mix(b.noise(38, 3).outputs["Fac"], srgb(222, 170, 146), srgb(205, 150, 128))
    base = b.mix(b.noise(160, 2).outputs["Fac"], base, srgb(232, 184, 160))
    # fine freckle/pore tint
    # decal mapped from object-space front projection
    mp = b.n("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-DX0 / (DX1 - DX0), 0, -DZ0 / (DZ1 - DZ0))
    mp.inputs["Scale"].default_value = (1 / (DX1 - DX0), 1, 1 / (DZ1 - DZ0))
    b.link(b.tc.outputs["Object"], mp.inputs["Vector"])
    sep = b.n("ShaderNodeSeparateXYZ"); b.link(mp.outputs[0], sep.inputs[0])
    com = b.n("ShaderNodeCombineXYZ"); b.link(sep.outputs["X"], com.inputs["X"]); b.link(sep.outputs["Z"], com.inputs["Y"])
    it = b.n("ShaderNodeTexImage"); it.image = decal; it.extension = 'CLIP'; it.interpolation = 'Linear'
    b.link(com.outputs[0], it.inputs["Vector"])
    gn = b.n("ShaderNodeNewGeometry")
    sepn = b.n("ShaderNodeSeparateXYZ"); b.link(gn.outputs["Normal"], sepn.inputs[0])
    # Normal is world space; character is at identity with the face toward -Y so it matches
    face = b.n("ShaderNodeMapRange"); face.clamp = True
    face.inputs["From Min"].default_value = -0.15; face.inputs["From Max"].default_value = -0.65
    b.link(sepn.outputs["Y"], face.inputs["Value"])
    a = b.math('MULTIPLY', it.outputs["Alpha"], face.outputs["Result"])
    col = b.mix(a, base, it.outputs["Color"])
    b.set("Base Color", col)
    n1 = b.noise(700, 3, 0.6)
    b.set("Roughness", b.math('ADD', 0.50, b.math('MULTIPLY', n1.outputs["Fac"], 0.18)))
    b.bump(b.noise(1300, 2, 0.6).outputs["Fac"], 0.35, 0.0006)
    return m


def mat_fabric(name, c1, c2, rough, bump_scale=600, bump_str=0.5, var_scale=220):
    m = bpy.data.materials.new(name)
    b = NB(m)
    col = b.mix(b.noise(var_scale, 2).outputs["Fac"], c1, c2)
    b.set("Base Color", col)
    b.set("Roughness", b.math('ADD', rough, b.math('MULTIPLY', b.noise(300, 2).outputs["Fac"], 0.1)))
    # weave: product of two sine bands in object space
    wv1 = b.n("ShaderNodeTexWave"); wv1.wave_type = 'BANDS'; wv1.bands_direction = 'X'
    wv1.inputs["Scale"].default_value = bump_scale * 0.18; wv1.inputs["Distortion"].default_value = 1.5
    b.link(b.tc.outputs["Object"], wv1.inputs["Vector"])
    wv2 = b.n("ShaderNodeTexWave"); wv2.wave_type = 'BANDS'; wv2.bands_direction = 'Z'
    wv2.inputs["Scale"].default_value = bump_scale * 0.18; wv2.inputs["Distortion"].default_value = 1.5
    b.link(b.tc.outputs["Object"], wv2.inputs["Vector"])
    h = b.math('ADD', b.math('MULTIPLY', wv1.outputs["Fac"], wv2.outputs["Fac"]),
               b.noise(bump_scale, 3, 0.7).outputs["Fac"])
    b.bump(h, bump_str, 0.0006)
    return m


def mat_leather(name, c1, rough):
    m = bpy.data.materials.new(name)
    b = NB(m)
    b.set("Base Color", c1)
    b.set("Roughness", b.math('ADD', rough, b.math('MULTIPLY', b.noise(120, 3).outputs["Fac"], 0.12)))
    vor = b.n("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 400
    b.link(b.tc.outputs["Object"], vor.inputs["Vector"])
    b.bump(vor.outputs["Distance"], 0.4, 0.0005)
    return m


def build_hi_materials():
    d = decal_image()
    return {
        "Skin": mat_skin(d),
        "Blazer": mat_fabric("HI_Blazer", srgb(24, 34, 72), srgb(34, 46, 92), 0.82, 650, 0.6),
        "Blouse": mat_fabric("HI_Blouse", srgb(234, 234, 238), srgb(246, 244, 246), 0.38, 900, 0.15, 90),
        "Trousers": mat_fabric("HI_Trousers", srgb(28, 30, 42), srgb(40, 42, 56), 0.78, 700, 0.5),
        "Shoes": mat_leather("HI_Shoes", srgb(20, 16, 16), 0.36),
    }


# ------------------------------------------------------------------ painted textures (hair / eyes / lashes / hardware)
def paint_hair(tex_a, tex_orm, atlas_size, rect):
    """Draw 4 hair-card variants into tex_a (albedo+alpha, linear) and ORM."""
    S = atlas_size
    u0, v0, u1, v1 = rect
    x0, x1, y0, y1 = int(u0 * S), int(u1 * S), int(v0 * S), int(v1 * S)
    W, H = x1 - x0, y1 - y0
    rng = np.random.default_rng(11)
    cw = W // 4
    base_dark = np.array(srgb(54, 33, 22), dtype=np.float32)
    base_light = np.array(srgb(92, 60, 38), dtype=np.float32)
    for var in range(4):
        cx0 = x0 + var * cw
        u = np.linspace(0, 1, cw, dtype=np.float32)[None, :]
        v = np.linspace(0, 1, H, dtype=np.float32)[:, None]      # root (bottom) -> tip (top)
        # strand clumps: sum of sines along u with slight wander along v
        nclump = 7 + var
        ph = rng.uniform(0, 6.28, size=3)
        wander = 0.05 * np.sin(v * 9 + ph[0]) + 0.03 * np.sin(v * 23 + ph[1])
        uu = u + wander
        clump = 0.5 + 0.5 * np.sin(uu * nclump * 2 * math.pi + ph[2])
        fine = 0.5 + 0.5 * np.sin(uu * 120 + np.sin(v * 5) * 2 + ph[0])
        # profile: card width tapering to the tip, clumps ending at different lengths
        endv = 0.75 + 0.25 * np.sin(uu * nclump * math.pi + ph[1])
        prof = np.clip(1 - np.abs(u - 0.5) * 2, 0, 1) ** 0.35 * 0.0 + 1.0
        alive = (v < endv).astype(np.float32)
        edge = np.clip((0.5 - np.abs(u - 0.5)) * 14, 0, 1)
        alpha = alive * edge * np.clip(clump * 1.6 + 0.35, 0, 1)
        alpha = np.clip((alpha - 0.45) * 8 + 0.5, 0, 1)                      # near-binary for alpha clip
        # taper at the very tip
        alpha *= np.clip((endv - v) * 25, 0, 1)
        tone = np.clip(0.30 + 0.35 * fine * (0.6 + 0.4 * clump) + 0.25 * v, 0, 1)
        col = base_dark[None, None, :] * (1 - tone[..., None]) + base_light[None, None, :] * tone[..., None]
        # darker at the root
        col *= (0.55 + 0.45 * np.clip(v * 3, 0, 1))[..., None]
        region = (slice(y0, y1), slice(cx0, cx0 + cw))
        tex_a[region + (slice(0, 3),)] = col
        tex_a[region + (3,)] = alpha
        tex_orm[region + (0,)] = 1.0
        tex_orm[region + (1,)] = 0.52
        tex_orm[region + (2,)] = 0.0


def paint_lashes(tex_a, tex_orm, S, rect):
    u0, v0, u1, v1 = rect
    x0, x1, y0, y1 = int(u0 * S), int(u1 * S), int(v0 * S), int(v1 * S)
    W, H = x1 - x0, y1 - y0
    u = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    v = np.linspace(0, 1, H, dtype=np.float32)[:, None]      # root bottom -> tip top
    # FIXPASS: fewer, thicker tapered strands (survive mip-mapping + alpha-test) and a thin root line, so the
    # lashes no longer collapse into one solid black band.
    n = 22
    alpha = np.zeros((H, W), dtype=np.float32)
    rng = np.random.default_rng(5)
    for k in range(n):
        uc = (k + 0.5 + rng.uniform(-0.15, 0.15)) / n
        ln = rng.uniform(0.62, 1.0)
        lean = 0.012 * v * (1 if k % 3 else -0.5)
        # half width (in px) tapers from 6.5 at the root to ~1 at the tip
        hw = (6.5 * (1 - v / ln) + 1.0)
        d = np.abs(u - uc - lean) * W
        m = np.clip((hw - d) / 1.2 + 0.5, 0, 1) * (v < ln)
        alpha = np.maximum(alpha, m)
    alpha = np.maximum(alpha, (v < 0.09) * 1.0)       # thin liner at the root
    alpha = np.clip((alpha - 0.4) * 6 + 0.5, 0, 1)
    region = (slice(y0, y1), slice(x0, x1))
    tex_a[region + (slice(0, 3),)] = np.array(srgb(14, 9, 8), dtype=np.float32)
    tex_a[region + (3,)] = alpha
    tex_orm[region + (0,)] = 1.0; tex_orm[region + (1,)] = 0.5; tex_orm[region + (2,)] = 0.0


def paint_eye(tex_a, tex_orm, S, rect, eye_r=0.0125):
    """Front-projected eye: sclera, hazel-brown iris with limbal ring, pupil, baked specular highlights."""
    u0, v0, u1, v1 = rect
    x0, x1, y0, y1 = int(u0 * S), int(u1 * S), int(v0 * S), int(v1 * S)
    W, H = x1 - x0, y1 - y0
    xs = (np.linspace(0, 1, W, dtype=np.float32) - 0.5) * 2 * eye_r
    zs = (np.linspace(0, 1, H, dtype=np.float32) - 0.5) * 2 * eye_r
    X, Z = np.meshgrid(xs, zs)
    r = np.sqrt(X ** 2 + Z ** 2)
    ang = np.arctan2(Z, X)
    sclera = np.array(srgb(236, 230, 226), dtype=np.float32)
    # slight veins/shade toward the rim
    col = np.empty((H, W, 3), dtype=np.float32)
    col[:] = sclera
    shade = np.clip((r - 0.007) / 0.006, 0, 1)
    col *= (1 - 0.18 * shade)[..., None]
    ir = 0.0060
    inside = np.clip((ir - r) / 0.0003, 0, 1)
    rr = r / ir
    fib = 0.5 + 0.5 * np.sin(ang * 46 + np.sin(rr * 9) * 1.5)
    rim = np.array(srgb(48, 30, 18), dtype=np.float32)
    mid = np.array(srgb(140, 92, 48), dtype=np.float32)
    cen = np.array(srgb(94, 128, 84), dtype=np.float32) * 0.0 + np.array(srgb(176, 128, 66), dtype=np.float32)
    t = np.clip(rr, 0, 1)[..., None]
    iris = cen * (1 - t) + mid * np.clip(t * 1.6, 0, 1) + 0
    iris = np.where(t > 0.7, mid * (1 - (t - 0.7) / 0.3) + rim * ((t - 0.7) / 0.3), iris)
    iris = iris * (0.78 + 0.35 * fib[..., None])
    col = col * (1 - inside[..., None]) + iris * inside[..., None]
    pupil = np.clip((0.0024 - r) / 0.0003, 0, 1)
    col = col * (1 - pupil[..., None]) + np.array([0.004, 0.004, 0.004], dtype=np.float32) * pupil[..., None]
    # specular highlights (window-like), baked
    h1 = np.clip((0.0017 - np.sqrt((X + 0.0030) ** 2 + (Z - 0.0034) ** 2)) / 0.0004, 0, 1)
    h2 = np.clip((0.0008 - np.sqrt((X - 0.0026) ** 2 + (Z + 0.0030) ** 2)) / 0.0003, 0, 1) * 0.6
    hl = np.clip(h1 + h2, 0, 1)
    col = col * (1 - hl[..., None]) + hl[..., None] * np.array([1.0, 1.0, 1.0], dtype=np.float32)
    region = (slice(y0, y1), slice(x0, x1))
    tex_a[region + (slice(0, 3),)] = col
    tex_a[region + (3,)] = 1.0
    tex_orm[region + (0,)] = 1.0
    tex_orm[region + (1,)] = 0.12 + 0.35 * (1 - inside) * 0 + 0.0
    tex_orm[region + (2,)] = 0.0


def paint_mouth_cells(tex_a, tex_orm, S, rect):
    """4 flat cells for the mouth interior: dark cavity, teeth, tongue, dark-red gum/back."""
    u0, v0, u1, v1 = rect
    cells = [srgb(18, 5, 7), srgb(228, 220, 204), srgb(178, 74, 82), srgb(70, 16, 22)]
    rough = [0.9, 0.35, 0.45, 0.6]
    cw = (u1 - u0) / 4
    for i, c in enumerate(cells):
        x0 = int((u0 + cw * i) * S); x1 = int((u0 + cw * (i + 1)) * S)
        y0 = int(v0 * S); y1 = int(v1 * S)
        tex_a[y0:y1, x0:x1, :3] = c
        tex_a[y0:y1, x0:x1, 3] = 1.0
        tex_orm[y0:y1, x0:x1, 0] = 1.0
        tex_orm[y0:y1, x0:x1, 1] = rough[i]
        tex_orm[y0:y1, x0:x1, 2] = 0.0


def paint_cells(tex_a, tex_orm, S, rect):
    u0, v0, u1, v1 = rect
    cells = [srgb(22, 22, 25), srgb(165, 168, 175), srgb(18, 26, 52), srgb(176, 140, 70)]
    rough = [0.45, 0.30, 0.8, 0.35]
    metal = [0.0, 0.9, 0.0, 0.9]
    cw = (u1 - u0) / 4
    for i, c in enumerate(cells):
        x0 = int((u0 + cw * i) * S); x1 = int((u0 + cw * (i + 1)) * S)
        y0 = int(v0 * S); y1 = int(v1 * S)
        tex_a[y0:y1, x0:x1, :3] = c
        tex_a[y0:y1, x0:x1, 3] = 1.0
        tex_orm[y0:y1, x0:x1, 0] = 1.0
        tex_orm[y0:y1, x0:x1, 1] = rough[i]
        tex_orm[y0:y1, x0:x1, 2] = metal[i]





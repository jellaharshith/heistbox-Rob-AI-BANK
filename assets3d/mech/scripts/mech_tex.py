"""Procedural texture sets (numpy). Arrays are (N,N,3) float32, row 0 = v=0 (bottom), values authored in
the image's own colorspace (sRGB for base/emissive, linear for ORM/normal)."""
import numpy as np

N = 1024


def _smooth(t):
    return t * t * (3 - 2 * t)


def vnoise(sx, sy, seed, n=N):
    """periodic value noise with sx x sy lattice cells, bilinear-smooth, range 0..1"""
    rng = np.random.RandomState(seed)
    g = rng.rand(sy, sx).astype(np.float32)
    x = np.arange(n, dtype=np.float32) * sx / n
    y = np.arange(n, dtype=np.float32) * sy / n
    x0 = np.floor(x).astype(int); fx = _smooth(x - x0); x0 %= sx; x1 = (x0 + 1) % sx
    y0 = np.floor(y).astype(int); fy = _smooth(y - y0); y0 %= sy; y1 = (y0 + 1) % sy
    a = g[np.ix_(y0, x0)]; b = g[np.ix_(y0, x1)]; c = g[np.ix_(y1, x0)]; d = g[np.ix_(y1, x1)]
    fxx = fx[None, :]; fyy = fy[:, None]
    return (a * (1 - fxx) + b * fxx) * (1 - fyy) + (c * (1 - fxx) + d * fxx) * fyy


def fbm(sx, sy, octaves, seed, n=N):
    t = np.zeros((n, n), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        t += amp * vnoise(sx * 2 ** o, sy * 2 ** o, seed + o * 17, n)
        tot += amp; amp *= 0.5
    return t / tot


def blur(a, r, axis=None):
    """periodic box blur radius r (pixels), 2 passes; axis None=both"""
    r = int(max(1, r))
    axes = (0, 1) if axis is None else (axis,)
    out = a.astype(np.float32)
    for ax in axes:
        for _ in range(2):
            acc = np.zeros_like(out)
            for s in range(-r, r + 1, max(1, r // 6)):
                acc += np.roll(out, s, axis=ax)
            cnt = len(range(-r, r + 1, max(1, r // 6)))
            out = acc / cnt
    return out


def grid():
    v, u = np.mgrid[0:N, 0:N].astype(np.float32)
    return (u + 0.5) / N, (v + 0.5) / N


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a + 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def band(x, a, b, soft=0.004):
    return smoothstep(a - soft, a + soft, x) * (1 - smoothstep(b - soft, b + soft, x))


def normal_from_height(h, k):
    dx = np.roll(h, -1, 1) - np.roll(h, 1, 1)
    dy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    nx, ny, nz = -dx * k, -dy * k, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l * .5 + .5, ny / l * .5 + .5, nz / l * .5 + .5], -1).astype(np.float32)


def cavity_ao(h, radius=10, k=3.0):
    return np.clip(1 - np.clip(blur(h, radius) - h, 0, None) * k, 0.2, 1).astype(np.float32)


def polyline_mask(pts, width_px, n=N):
    m = np.zeros((n, n), np.float32)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        L = int(np.hypot(x1 - x0, y1 - y0) * n * 1.5) + 2
        for t in np.linspace(0, 1, L):
            ix = int((x0 + (x1 - x0) * t) * n) % n; iy = int((y0 + (y1 - y0) * t) * n) % n
            m[iy, ix] = 1
    m = blur(m, width_px) * 1.0
    return np.clip(m / (m.max() + 1e-9) * 3.0, 0, 1)


def pack_orm(ao, rough, metal):
    return np.stack([ao, rough, metal], -1).astype(np.float32)


def _stack(c, shape):
    return np.stack([np.full(shape, c[i], np.float32) for i in range(3)], -1)


def lerp3(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


# ---------------------------------------------------------------- vault doors
def door_common():
    u, v = grid()
    X = (u - .5) * 2.2; Z = (v - .5) * 2.2
    R = np.hypot(X, Z); A = np.arctan2(Z, X)
    ring = band(R, 0.86, 1.02, 0.02)
    h = ring * 0.6 + band(R, 0.78, 0.80, 0.01) * -0.3
    # bolt heads on the ring (12)
    for i in range(12):
        a = i * np.pi / 6
        d = np.hypot(X - 0.93 * np.cos(a), Z - 0.93 * np.sin(a))
        h += (1 - smoothstep(0.045, 0.06, d)) * 0.4
    return u, v, X, Z, R, A, h


def tex_door_L():
    u, v, X, Z, R, A, h = door_common()
    n1 = fbm(6, 6, 5, 1); n2 = fbm(48, 3, 3, 2)           # blotch + brushed streaks (angular-ish)
    streak = vnoise(2, 400, 3)
    h = h + (n1 - .5) * 0.15 + (streak - .5) * 0.05
    # crack: jagged polyline from rim (30deg) toward centre, with branches
    def pt(r, a):
        return (0.5 + r * np.cos(a) / 2.2, 0.5 + r * np.sin(a) / 2.2)
    rng = np.random.RandomState(7)
    pts = [pt(1.08, np.radians(35))]
    r, a = 1.08, np.radians(35)
    while r > 0.42:
        r -= 0.07 + rng.rand() * 0.06; a += (rng.rand() - .5) * 0.22
        pts.append(pt(r, a))
    crack = polyline_mask(pts, 2)
    br = [pts[3]]; r, a = 0.8, np.radians(35) + 0.2
    for _ in range(5):
        r -= 0.06; a += 0.12 + (rng.rand() - .5) * .2; br.append(pt(r, a))
    crack = np.maximum(crack, polyline_mask(br, 1.5) * 0.9)
    h = h - crack * 1.2
    brass = np.array([0.90, 0.72, 0.34], np.float32)
    dark = np.array([0.42, 0.30, 0.13], np.float32)
    ao = cavity_ao(h, 9, 2.0)
    base = lerp3(_stack(brass, (N, N)), _stack(dark, (N, N)),
                 np.clip((n1 - .35) * 1.2 + (1 - ao) * 1.5 + smoothstep(1.0, 1.12, R) * .5, 0, 1))
    base *= (0.9 + 0.2 * n2)[..., None]
    base = lerp3(base, _stack([0.03, 0.02, 0.01], (N, N)), crack)
    rough = np.clip(0.30 + (n1 - .5) * 0.25 + (streak - .5) * 0.15 + crack * 0.4, 0.15, 0.9)
    metal = np.clip(1.0 - crack * 0.6, 0, 1)
    ao = np.minimum(ao, 1 - crack * 0.5)
    ao = np.where(R > 1.08, 0.5, ao)
    return dict(base=base, orm=pack_orm(ao, rough, metal), normal=normal_from_height(h, 5.0), emissive=None)


def tex_door_M():
    u, v, X, Z, R, A, h = door_common()
    n1 = fbm(8, 8, 5, 11); n2 = fbm(64, 64, 4, 12); n3 = fbm(16, 16, 3, 13)
    ice = np.array([0.55, 0.78, 0.97], np.float32)
    frost_col = np.array([0.93, 0.97, 1.0], np.float32)
    # frost grows from rim and from bottom
    grow = np.clip(smoothstep(0.55, 1.12, R) * .9 + (0.5 - Z / 2.2) * 0.35, 0, 1)
    frost = smoothstep(0.45, 0.62, n1 * 0.7 + n3 * 0.3 + grow * 0.6 - 0.35)
    crystals = smoothstep(0.62, 0.8, n2) * frost
    h = h * 0.6 + frost * 0.25 + crystals * 0.25 + (n2 - .5) * 0.1 * frost
    ao = cavity_ao(h, 9, 1.6)
    base = lerp3(_stack(ice, (N, N)) * (0.9 + 0.2 * n3)[..., None], _stack(frost_col, (N, N)), frost)
    base = base * (0.65 + 0.35 * ao)[..., None]
    rough = np.clip(0.28 + frost * 0.6 + (n2 - .5) * 0.1, 0.1, 1)
    metal = np.clip(0.25 * (1 - frost), 0, 1)
    emis = np.zeros((N, N, 3), np.float32)
    # red lockdown-bar swatch in bottom-right corner (outside the disc footprint)
    sw = (u > 0.88) & (v < 0.12)
    base[sw] = (0.85, 0.04, 0.04); rough[sw] = 0.4; metal[sw] = 0.0; ao[sw] = 1.0
    emis[sw] = (1.0, 0.05, 0.04)
    base = np.clip(base, 0, 1)
    return dict(base=base, orm=pack_orm(ao, rough, metal), normal=normal_from_height(h, 4.0), emissive=emis)


def tex_door_R():
    u, v, X, Z, R, A, h = door_common()
    streak = vnoise(3, 512, 21); n1 = fbm(6, 6, 5, 22); n2 = fbm(40, 40, 3, 23)
    h = h + (streak - .5) * 0.06 + (n1 - .5) * 0.1
    # airlock groove at r=0.70 + panel seams
    h += band(R, 0.66, 0.74, 0.01) * -0.5
    for i in range(8):
        a = i * np.pi / 4 + np.pi / 8
        d = np.abs(-np.sin(a) * X + np.cos(a) * Z)
        h += band(d, 0, 0.012, 0.004) * -0.3 * (R < 0.66)
    ao = cavity_ao(h, 9, 2.0)
    gun = np.array([0.22, 0.23, 0.26], np.float32)
    base = _stack(gun, (N, N)) * (0.8 + 0.4 * n1)[..., None] * (0.7 + 0.3 * ao)[..., None]
    base = np.clip(base, 0, 1)
    rough = np.clip(0.38 + (streak - .5) * 0.2 + (n1 - .5) * 0.2, 0.2, 0.8)
    metal = np.full((N, N), 0.95, np.float32)
    cyan = np.array([0.0, 0.9, 1.0], np.float32)
    ringm = band(R, 0.67, 0.73, 0.012)
    ticks = np.zeros((N, N), np.float32)
    for i in range(12):
        a = i * np.pi / 6 + np.pi / 12
        d = np.abs(-np.sin(a) * X + np.cos(a) * Z)
        along = X * np.cos(a) + Z * np.sin(a)
        ticks = np.maximum(ticks, band(d, 0, 0.018, 0.006) * band(along, 0.88, 0.99, 0.01))
    glow = np.maximum(ringm, ticks)
    emis = glow[..., None] * cyan
    base = lerp3(base, _stack([0.02, 0.35, 0.4], (N, N)), glow)
    ao = np.where(R > 1.08, 0.5, ao)
    return dict(base=base, orm=pack_orm(ao, rough, metal), normal=normal_from_height(h, 5.0), emissive=emis)


# ---------------------------------------------------------------- sentinel
def tex_sentinel():
    u, v = grid()
    h = np.zeros((N, N), np.float32)
    streak = vnoise(3, 700, 31)          # long along u = brushed horizontally
    n1 = fbm(5, 5, 4, 32)
    vb = np.clip((v - 0.3) / 0.7, 0, 1)   # 0 south pole .. 1 north pole
    body = v >= 0.3
    # panel seams: equator groove (vb=.5), 6 meridians, two latitudes
    seam = band(np.abs(vb - 0.5), 0, 0.012, 0.004)
    seam = np.maximum(seam, band(np.abs(vb - 0.78), 0, 0.006, 0.003))
    seam = np.maximum(seam, band(np.abs(vb - 0.22), 0, 0.006, 0.003))
    for i in range(6):
        seam = np.maximum(seam, band(np.abs(u - i / 6.0), 0, 0.004, 0.0015) * (np.abs(vb - 0.5) > 0.03))
        seam = np.maximum(seam, band(np.abs(u - 1.0 - i / 6.0), 0, 0.004, 0.0015) * 0)
    seam = np.maximum(seam, band(np.abs(u - 1.0), 0, 0.004, 0.0015))
    h = (streak - .5) * 0.08 + (n1 - .5) * 0.04 - seam * 0.6
    ao = cavity_ao(h, 7, 2.5)
    steel = np.array([0.66, 0.68, 0.71], np.float32)
    base = _stack(steel, (N, N)) * (0.85 + 0.3 * streak)[..., None] * (0.75 + 0.25 * ao)[..., None]
    base = base * (1 - 0.35 * seam)[..., None]
    rough = np.clip(0.33 + (streak - .5) * 0.25 + (n1 - .5) * 0.15 + seam * .3, 0.15, 0.8)
    metal = np.full((N, N), 1.0, np.float32)
    emis = np.zeros((N, N, 3), np.float32)
    # ring-light strip (v 0..0.04): cyan emissive
    m = v < 0.04
    base[m] = (0.4, 0.9, 1.0); emis[m] = (0.1, 0.9, 1.0); rough[m] = .4; metal[m] = 0.0; ao[m] = 1
    # dark gunmetal swatch for nozzle / pods (u .5-.6, v .05-.15)
    m = (u > 0.5) & (u < 0.6) & (v > 0.05) & (v < 0.15)
    base[m] = (0.10, 0.11, 0.13); rough[m] = .5; metal[m] = .9; ao[m] = 1
    # lens square u .02-.26, v .04-.28 centred (.14,.16) radius .12
    lu = (u - 0.14); lv = (v - 0.16); lr = np.hypot(lu, lv)
    sq = (u > 0.02) & (u < 0.26) & (v > 0.04) & (v < 0.28)
    bez = sq & (lr < 0.12)
    base[sq] = steel * 0.5
    base[bez & (lr > 0.088)] = (0.30, 0.31, 0.34); rough[bez & (lr > 0.088)] = .3
    glass = bez & (lr <= 0.088)
    base[glass] = (0.02, 0.03, 0.05); rough[glass] = 0.06; metal[glass] = 0.0; ao[glass] = 1
    iris = bez & (lr <= 0.05)
    k = np.clip(1 - lr / 0.05, 0, 1)
    base[iris] = (0.0, 0.25, 0.3)
    emis[iris] = (np.stack([0.0 + 0.7 * k, 0.8 + 0.2 * k, 1.0 * np.ones_like(k)], -1))[iris]
    glow_ring = bez & (lr > 0.058) & (lr < 0.068)
    emis[glow_ring] = (0.0, 0.5, 0.6)
    return dict(base=np.clip(base, 0, 1), orm=pack_orm(ao, rough, metal),
                normal=normal_from_height(h, 5.0), emissive=emis)


# ---------------------------------------------------------------- shredder
def tex_shredder():
    u, v = grid()
    streak = vnoise(2, 600, 41); n1 = fbm(4, 4, 4, 42)
    h = (streak - .5) * 0.08 + (n1 - .5) * 0.05
    # panel seams on main area
    seam = np.maximum(band(np.abs(v - 0.3), 0, 0.004, 0.0015), band(np.abs(u - 0.2), 0, 0.004, 0.0015))
    h -= seam * 0.5
    ao = cavity_ao(h, 6, 2.5)
    steel = np.array([0.5, 0.52, 0.55], np.float32)
    base = _stack(steel, (N, N)) * (0.85 + 0.3 * streak)[..., None]
    base *= (1 - 0.3 * seam)[..., None]
    rough = np.clip(0.4 + (streak - .5) * 0.3, 0.2, .8)
    metal = np.full((N, N), 0.95, np.float32)
    emis = np.zeros((N, N, 3), np.float32)
    def sw(u0, u1, col, r, m, e=None):
        mm = (u > u0) & (u < u1) & (v < 0.1)
        base[mm] = col; rough[mm] = r; metal[mm] = m; ao[mm] = 1
        if e is not None:
            emis[mm] = e
    sw(0.90, 0.92, (0.07, 0.07, 0.08), 0.6, 0.1)           # dark plastic
    sw(0.92, 0.94, (0.01, 0.01, 0.01), 0.9, 0.0)           # slot black
    sw(0.94, 0.96, (0.1, 0.9, 0.2), 0.5, 0.0, (0.1, 1.0, 0.2))   # green LED
    sw(0.96, 0.98, (1.0, 0.55, 0.05), 0.5, 0.0, (1.0, 0.5, 0.02))  # amber LED
    sw(0.98, 1.0, (0.9, 0.1, 0.1), 0.4, 0.0, (1.0, 0.1, 0.1))     # emitter red
    return dict(base=np.clip(base, 0, 1), orm=pack_orm(ao, rough, metal),
                normal=normal_from_height(h, 4.0), emissive=emis)

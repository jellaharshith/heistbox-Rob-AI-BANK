"""Procedural tileable PBR texture generation (numpy) + bitmap font. Run inside Blender."""
import numpy as np
import bpy

N = 1024

def fnoise(n, beta, seed, aniso=(1.0, 1.0)):
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((n, n))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(n)[:, None] * n / aniso[0]
    fx = np.fft.fftfreq(n)[None, :] * n / aniso[1]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    amp = 1.0 / f ** beta
    amp[0, 0] = 0
    r = np.real(np.fft.ifft2(F * amp))
    r = (r - r.min()) / (r.max() - r.min() + 1e-9)
    return r

def normal_from_height(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    return np.stack([(-dx / l) * .5 + .5, (-dy / l) * .5 + .5, nz / l * .5 + .5], -1)

def save_png(name, rgb, path, srgb=True, alpha=None):
    h, w = rgb.shape[:2]
    a = np.ones((h, w, 1)) if alpha is None else alpha[..., None]
    px = np.concatenate([np.clip(rgb, 0, 1), a], -1).astype(np.float32)
    img = bpy.data.images.get(name)
    if img: bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    img.pack() if False else None
    return img

def orm(ao, rough, metal):
    return np.stack([np.broadcast_to(ao, rough.shape), rough, np.broadcast_to(metal, rough.shape)], -1)

def lerp(a, b, t):
    a = np.array(a); b = np.array(b)
    return a + (b - a) * t[..., None]

U = np.linspace(0, 1, N, endpoint=False)
YY, XX = np.meshgrid(U, U, indexing='ij')   # YY = v (rows), XX = u

def make_marble(seed=3):
    w1 = fnoise(N, 2.2, seed); w2 = fnoise(N, 1.6, seed + 1)
    t = 2 * np.pi * (2 * XX + 1 * YY + 0.9 * (w1 - .5) * 2.2)
    vein = (1 - np.abs(np.sin(t))) ** 18
    t2 = 2 * np.pi * (3 * XX - 2 * YY + 1.3 * (w2 - .5) * 3)
    vein2 = ((1 - np.abs(np.sin(t2))) ** 40) * .6
    cl = fnoise(N, 2.8, seed + 2)
    base = lerp((0.018, 0.020, 0.028), (0.05, 0.055, 0.07), cl)
    v = np.clip(vein + vein2, 0, 1)
    col = lerp(base, (0.55, 0.57, 0.62), v * .55)
    rough = 0.10 + 0.08 * fnoise(N, 2.0, seed + 3) + 0.15 * v
    h = fnoise(N, 2.5, seed + 4) * .1 + v * .02
    return col, rough, np.zeros_like(rough), normal_from_height(h, 2.0)

def make_wall(seed=10):
    n1 = fnoise(N, 1.4, seed); n2 = fnoise(N, 0.6, seed + 1)
    col = lerp((0.10, 0.108, 0.13), (0.17, 0.18, 0.21), n1 * .7 + n2 * .3)
    # vertical panel grooves, period 1/2
    g = np.abs(((XX * 2) % 1.0) - 0.5)
    groove = np.clip((0.012 - np.minimum(g, 0.5 - g) * 0 - np.abs(((XX * 2) % 1.0) - 0.0)) / 0.012, 0, 1)
    groove = np.maximum(groove, np.clip((0.012 - (1 - ((XX * 2) % 1.0))) / 0.012, 0, 1))
    col = col * (1 - 0.5 * groove[..., None])
    h = n1 * .05 + n2 * .03 - groove * .06
    rough = 0.72 + 0.2 * n2
    return col, rough, np.zeros_like(rough), normal_from_height(h, 3.0)

def make_brass(seed=20):
    s = fnoise(N, 1.2, seed, aniso=(8.0, 0.4))
    s2 = fnoise(N, 0.8, seed + 1, aniso=(4.0, 0.5))
    col = lerp((0.62, 0.42, 0.13), (0.86, 0.66, 0.28), s * .6 + s2 * .4)
    rough = 0.22 + 0.22 * s2
    h = s * .04
    return col, rough, np.ones_like(rough), normal_from_height(h, 2.0)

def make_wood(seed=30):
    n = fnoise(N, 1.8, seed, aniso=(0.25, 6.0))
    rings = (np.sin(2 * np.pi * (6 * YY + 4 * (n - .5))) * .5 + .5)
    plank = np.floor(XX * 4)
    pid = ((plank * 0.37) % 1.0)
    seam = np.clip((0.006 - np.abs(((XX * 4) % 1.0) - 0.0)) / 0.006, 0, 1)
    seam = np.maximum(seam, np.clip((0.006 - (1 - ((XX * 4) % 1.0))) / 0.006, 0, 1))
    base = lerp((0.10, 0.045, 0.02), (0.20, 0.10, 0.05), rings * .6 + n * .4)
    col = base * (0.8 + 0.4 * pid[..., None]) * (1 - .7 * seam[..., None])
    rough = 0.45 + 0.2 * n
    h = rings * .03 - seam * .08
    return col, rough, np.zeros_like(rough), normal_from_height(h, 3.0)

# ---- 5x7 bitmap font
FONT = {
 '$': ["00100", "01111", "10100", "01110", "00101", "11110", "00100"],
 '0': ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
 '1': ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
 '2': ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
 '3': ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
 '4': ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
 '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
 '6': ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
 '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
 '8': ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
 '9': ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
 ',': ["00000", "00000", "00000", "00000", "00110", "00100", "01000"],
 '.': ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
 'W': ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
 'A': ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
 'N': ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
 'T': ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
 'E': ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
 'D': ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
 'P': ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
 'I': ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
 'R': ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
 'B': ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
 'K': ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
 'L': ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
 'O': ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
 'C': ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
 'S': ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
 'H': ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
 'Y': ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
 'U': ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
 'F': ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
 '>': ["01000", "00100", "00010", "00001", "00010", "00100", "01000"],
 '_': ["00000", "00000", "00000", "00000", "00000", "00000", "11111"],
 ' ': ["00000"] * 7,
}

def text_mask(text, hgt, width=None):
    """Return float mask (rows bottom-up not applied; row0 = top) of text scaled so text height ~hgt px."""
    s = max(1, int(hgt // 7))
    cols = []
    for ch in text:
        g = FONT.get(ch, FONT[' '])
        arr = np.array([[int(c) for c in row] for row in g], dtype=float)
        arr = np.kron(arr, np.ones((s, s)))
        cols.append(arr); cols.append(np.zeros((arr.shape[0], s)))
    m = np.concatenate(cols[:-1], 1)
    return m

def blit(img, mask, cx, cy, color):
    """img rows bottom-up (row0 = bottom). (cx,cy) center in pixels (y up)."""
    h, w = mask.shape
    m = mask[::-1]   # flip so text reads upright in bottom-up buffer
    x0 = int(cx - w / 2); y0 = int(cy - h / 2)
    H, W = img.shape[:2]
    xs0, ys0 = max(0, x0), max(0, y0)
    xs1, ys1 = min(W, x0 + w), min(H, y0 + h)
    if xs1 <= xs0 or ys1 <= ys0: return
    sub = m[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0][..., None]
    img[ys0:ys1, xs0:xs1] = img[ys0:ys1, xs0:xs1] * (1 - sub) + np.array(color) * sub

import numpy as np


def _hash(ix, iy, iz, seed=0):
    m = 0xffffffff
    h = (ix.astype(np.int64) * 73856093 ^ iy.astype(np.int64) * 19349663 ^ iz.astype(np.int64) * 83492791 ^ (seed * 2654435761)) & m
    h = ((h ^ (h >> 13)) * 1274126177) & m
    h = h ^ (h >> 16)
    return (h & 0xffff).astype(np.float32) / 65535.0


def vnoise(p, freq=1.0, seed=0):
    """3D value noise in [0,1]; p (...,3)"""
    q = np.asarray(p, dtype=np.float32) * freq
    i = np.floor(q); f = q - i
    f = f * f * (3 - 2 * f)
    ix, iy, iz = i[..., 0], i[..., 1], i[..., 2]
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    def h(dx, dy, dz):
        return _hash(ix + dx, iy + dy, iz + dz, seed)
    c000, c100, c010, c110 = h(0, 0, 0), h(1, 0, 0), h(0, 1, 0), h(1, 1, 0)
    c001, c101, c011, c111 = h(0, 0, 1), h(1, 0, 1), h(0, 1, 1), h(1, 1, 1)
    x00 = c000 + (c100 - c000) * fx; x10 = c010 + (c110 - c010) * fx
    x01 = c001 + (c101 - c001) * fx; x11 = c011 + (c111 - c011) * fx
    y0 = x00 + (x10 - x00) * fy; y1 = x01 + (x11 - x01) * fy
    return y0 + (y1 - y0) * fz


def fbm(p, freq=1.0, octaves=3, seed=0):
    a = 0.5; s = 0; tot = 0
    for o in range(octaves):
        s = s + a * vnoise(p, freq * (2 ** o), seed + o)
        tot += a; a *= 0.5
    return s / tot


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def seg_dist(px, pz, a, b):
    """distance in the (x,z) plane from points to segment a->b"""
    ax, az = a; bx, bz = b
    dx, dz = bx - ax, bz - az
    t = np.clip(((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz), 0, 1)
    return np.hypot(px - (ax + t * dx), pz - (az + t * dz))

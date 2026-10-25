import bpy, numpy as np


def raster(objs, res=1024, extra_attr="part"):
    """Rasterise object triangles in UV space. Returns dict of arrays (res,res,..): pos (obj space), nrm, part, mpu (metres per uv unit), mask."""
    pos = np.zeros((res, res, 3), np.float32)
    nrm = np.zeros((res, res, 3), np.float32)
    part = np.zeros((res, res), np.float32)
    mpu = np.zeros((res, res), np.float32)
    oid = np.zeros((res, res), np.int8)
    filled = np.zeros((res, res), bool)
    for oi, o in enumerate(objs):
        me = o.data
        me.calc_loop_triangles()
        P = np.zeros((len(me.vertices), 3), np.float32); me.vertices.foreach_get("co", P.ravel())
        Nv = np.zeros((len(me.vertices), 3), np.float32); me.vertices.foreach_get("normal", Nv.ravel())
        UV = np.zeros((len(me.loops), 2), np.float32); me.uv_layers.active.data.foreach_get("uv", UV.ravel())
        pa = np.zeros(len(me.vertices), np.float32)
        if extra_attr in me.attributes:
            me.attributes[extra_attr].data.foreach_get("value", pa)
        for t in me.loop_triangles:
            v = t.vertices; l = t.loops
            uv = UV[list(l)] * res
            x0 = int(max(np.floor(uv[:, 0].min()) - 1, 0)); x1 = int(min(np.ceil(uv[:, 0].max()) + 1, res - 1))
            y0 = int(max(np.floor(uv[:, 1].min()) - 1, 0)); y1 = int(min(np.ceil(uv[:, 1].max()) + 1, res - 1))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            a = uv[0]; b = uv[1]; c = uv[2]
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(den) < 1e-9:
                continue
            w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
            w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
            w2 = 1 - w0 - w1
            eps = -0.002
            m = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
            if not m.any():
                continue
            p3 = P[v[0]]; q3 = P[v[1]]; r3 = P[v[2]]
            area3 = np.linalg.norm(np.cross(q3 - p3, r3 - p3)) / 2
            areauv = abs(den) / 2 / (res * res)
            scale = np.sqrt(area3 / max(areauv, 1e-12))
            ys, xs = np.nonzero(m)
            W0 = w0[m][:, None]; W1 = w1[m][:, None]; W2 = w2[m][:, None]
            pos[y0 + ys, x0 + xs] = W0 * p3 + W1 * q3 + W2 * r3
            n = W0 * Nv[v[0]] + W1 * Nv[v[1]] + W2 * Nv[v[2]]
            nrm[y0 + ys, x0 + xs] = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
            part[y0 + ys, x0 + xs] = pa[v[0]]
            mpu[y0 + ys, x0 + xs] = scale
            oid[y0 + ys, x0 + xs] = oi
            filled[y0 + ys, x0 + xs] = True
    return dict(pos=pos, nrm=nrm, part=part, mpu=mpu, oid=oid, filled=filled)


def dilate(arrs, filled, iters=10):
    """extend filled texels into gutters (copy from neighbours)."""
    f = filled.copy()
    for _ in range(iters):
        nf = f.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            sh = np.roll(np.roll(f, dy, 0), dx, 1)
            take = sh & ~nf
            if take.any():
                for a in arrs:
                    src = np.roll(np.roll(a, dy, 0), dx, 1)
                    a[take] = src[take]
                nf |= take
        f = nf
    return f

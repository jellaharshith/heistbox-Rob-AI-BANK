"""Face helpers used by s5: viseme tuning on the transferred shape keys, dark mouth-interior recolour, mouth-part shape-key deltas."""
import sys
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina/scripts")
import numpy as np
import tlib

MZ = 1.4335          # lip slit height
MC = (0.0, 1.432)    # mouth centre (x, z)


def _co(kb, n):
    a = np.empty(n * 3, np.float32); kb.data.foreach_get("co", a); return a.reshape(-1, 3)


def _set(kb, co):
    kb.data.foreach_set("co", co.astype(np.float32).ravel())


def tune_visemes(J, skin_mask):
    """Post-edit PP/FF/aa/O/U (added on top of the MakeHuman-unit mix). skin_mask: bool array of verts that may move."""
    me = J.data
    n = len(me.vertices)
    kbs = me.shape_keys.key_blocks
    b = _co(kbs["Basis"], n)
    x, y, z = b[:, 0], b[:, 1], b[:, 2]
    front = (y < -0.105) & skin_mask
    w = np.clip(1 - ((x / 0.05) ** 2 + ((z - MC[1]) / 0.042) ** 2), 0, 1) ** 0.8 * front
    s = np.clip((z - MZ) / 0.006 + 0.5, 0, 1)          # 1 = upper lip, 0 = lower lip
    cen = np.exp(-(x / 0.022) ** 2) * w
    R = {}

    def edit(name, orig_scale, dx=0.0, dy=0.0, dz_up=0.0, dz_lo=0.0, xs=0.0):
        co = _co(kbs[name], n)
        d = (co - b) * orig_scale
        d[:, 0] += (-xs * x) * w + dx * w
        d[:, 1] += dy * w
        d[:, 2] += dz_up * s * w + dz_lo * (1 - s) * w
        _set(kbs[name], b + d)

    # PP: lips pressed together and thin, slightly drawn in, no smirk
    edit("viseme_PP", 0.35, dy=0.0018, dz_up=-0.0020, dz_lo=0.0022, xs=0.10)
    # FF: lower lip tucked up/back under the upper teeth, upper lip lifted to show them
    co = _co(kbs["viseme_FF"], n)
    d = (co - b) * 0.55
    d[:, 2] += 0.0030 * s * w + 0.0085 * (1 - s) * cen
    d[:, 1] += 0.0045 * (1 - s) * cen
    _set(kbs["viseme_FF"], b + d)
    # aa: wide open, a touch wider and the upper lip lifted
    edit("viseme_aa", 1.0, dz_up=0.0030, xs=-0.07)
    # O: round, lips pushed forward
    edit("viseme_O", 1.0, dy=-0.0070, xs=0.24)
    # U: small pursed round, lips pushed well forward
    edit("viseme_U", 1.0, dy=-0.0100, xs=0.30, dz_up=-0.0006, dz_lo=0.0010)


def recolor_interior(J, skin_mask):
    """Skin faces that line the mouth cavity (seen when the mouth opens) -> dark cavity UV cell. Returns face count."""
    me = J.data
    n = len(me.vertices)
    P = _co(me.shape_keys.key_blocks["viseme_aa"], n)
    B = _co(me.shape_keys.key_blocks["Basis"], n)
    C = np.array([0.0, -0.118, 1.421])
    uvl = me.uv_layers.active
    cnt = 0
    cx, cy = tlib.MC_GUM
    for p in me.polygons:
        vs = list(p.vertices)
        if not all(skin_mask[v] for v in vs):
            continue
        pts = P[vs]
        c = pts.mean(0)
        cb = B[vs].mean(0)
        # faces that bridge the lip slit (thin when closed) get stretched a lot by the open shape -> they are cavity too
        def _me(Q):
            return max(np.linalg.norm(Q[i] - Q[(i + 1) % len(Q)]) for i in range(len(Q)))
        stretched = abs(cb[0]) < 0.022 and cb[1] < -0.12 and 1.39 < c[2] < 1.45 and _me(pts) > 0.011 and _me(pts) > 2.0 * _me(B[vs])
        if stretched:
            for li in p.loop_indices:
                uvl.data[li].uv = (cx, cy)
            cnt += 1
            continue
        if not (abs(c[0]) < 0.034 and 1.396 < c[2] < 1.445 and c[1] > -0.152 and cb[1] > -0.1418 and 1.405 < cb[2] < 1.450):
            continue
        # normal in the open shape
        nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        ln = np.linalg.norm(nrm)
        if ln < 1e-12:
            continue
        nrm /= ln
        if np.dot(nrm, C - c) <= 0:
            continue
        for li in p.loop_indices:
            uvl.data[li].uv = (cx, cy)
        cnt += 1
    return cnt


def mouth_deltas(J, mouth_range, skin_mask):
    """Give the mouth-part vertices (index range) shape-key deltas sampled from the front lip vertices at the same height/side
    (upper parts from the upper lip, lower parts + tongue from the lower lip). Needs tuned skin keys."""
    me = J.data
    n = len(me.vertices)
    kbs = me.shape_keys.key_blocks
    B = _co(kbs["Basis"], n)
    lo, hi = mouth_range
    cand = np.nonzero(skin_mask & (B[:, 1] < -0.133) & (np.abs(B[:, 0]) < 0.04) & (B[:, 2] > 1.40) & (B[:, 2] < 1.47))[0]
    up = cand[B[cand, 2] >= 1.4355]
    lw = cand[(B[cand, 2] <= 1.4325)]
    for kb in kbs:
        if kb.name == "Basis":
            continue
        K = _co(kb, n)
        D = K - B
        out = K.copy()
        for v in range(lo, hi):
            pv = B[v]
            pool = up if v in _UPPER else lw
            az = 1.4372 if v in _UPPER else 1.4270      # fixed anchor height -> each part moves rigidly with its lip
            d2 = (B[pool, 0] - pv[0]) ** 2 + (B[pool, 2] - az) ** 2
            idx = np.argsort(d2)[:5]
            wgt = 1.0 / (np.sqrt(d2[idx]) + 0.003)
            out[v] = pv + (D[pool[idx]] * wgt[:, None]).sum(0) / wgt.sum()
        _set(kb, out)


_UPPER = set()


def set_upper(ids):
    _UPPER.clear(); _UPPER.update(ids)



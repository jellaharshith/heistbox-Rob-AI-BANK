import numpy as np
from noise import vnoise, fbm, ss, seg_dist


def tri(x):
    return np.abs(2 * (x - np.floor(x + 0.5)))   # triangle wave 0..1


def hi_height(P, N, part, C):
    """displacement (m) along normal for hi-res detail. C: context dict (landmarks + bones)."""
    n = len(P)
    X, Y, Z = P[:, 0], P[:, 1], P[:, 2]
    d = np.zeros(n, np.float32)
    pr = np.rint(part).astype(int)
    hem, neck, eye = C["hem_z"], C["neck_z"], C["eye_z"]
    hc = np.array(C["hc"])
    # ---------------- hoodie (2) / hood (11)
    m = np.isin(pr, [2, 11])
    if m.any():
        p = P[m]; x, y, z = p[:, 0], p[:, 1], p[:, 2]
        h = 0.0009 * fbm(p, 220, 2, 1) + 0.0035 * (fbm(p, 16, 3, 2) - 0.5)
        # elbow / waist creases
        for s in (1, -1):
            e = np.array(C["elbow"]) * np.array([s, 1, 1])
            dist = np.linalg.norm(p - e, axis=1)
            h += 0.004 * ss(0.14, 0.02, dist) * (tri(vnoise(p, 38, 3) * 3 + z * 30) - 0.5)
        h += 0.004 * ss(0.12, 0.0, np.abs(z - (hem + 0.1))) * (tri(z * 55 + 2 * vnoise(p, 18, 5)) - 0.5)
        # kangaroo pocket (front)
        front = N[m][:, 1] < -0.35
        ztop = hem + 0.19
        inx = ss(0.19, 0.17, np.abs(x)) * ss(hem - 0.02, hem + 0.005, z) * ss(ztop + 0.01, ztop - 0.005, z) * front
        # pocket raised panel with slanted slit grooves
        h += 0.0065 * inx
        for s in (1, -1):
            dd = seg_dist(x * s, z, (0.165, ztop - 0.005), (0.105, ztop - 0.095))
            h -= 0.005 * ss(0.006, 0.0015, dd) * front
        # hem rib band
        ang = np.arctan2(x, y - C["torso_cy"])
        band = ss(hem + 0.075, hem + 0.045, z) * (z > hem - 0.01)
        h += 0.0022 * band * tri(ang * 62 / (2 * np.pi))
        # cuff ribs
        for s, side in ((1, "L"), (-1, "R")):
            hand = np.array(C["hand_" + side]); ax = np.array(C["axis_" + side])
            q = p - hand
            t = q @ ax
            perp = q - np.outer(t, ax)
            u = np.cross(ax, [0, 0, 1.0]); u /= np.linalg.norm(u); v = np.cross(ax, u)
            a2 = np.arctan2(perp @ v, perp @ u)
            cm = ss(-0.06, -0.075, t) * 0 + ss(-0.065, -0.075, t) * 0
            cm = (t > -0.07) & (t < 0.01) & (np.linalg.norm(perp, axis=1) < 0.09)
            h += 0.002 * cm * tri(a2 * 26 / (2 * np.pi))
        # collar/hood folds stronger
        hm = pr[m] == 11
        h = h + hm * 0.006 * (tri(vnoise(p, 22, 7) * 4) - 0.5)
        d[m] = h
    # ---------------- cords
    m = pr == 10
    if m.any():
        p = P[m]
        d[m] = 0.0007 * np.sin(p[:, 2] * 2 * np.pi / 0.006 + np.arctan2(p[:, 0], p[:, 1]) * 3)
    # ---------------- pants (3) / pockets (12)
    m = np.isin(pr, [3, 12])
    if m.any():
        p = P[m]; x, y, z = p[:, 0], p[:, 1], p[:, 2]
        h = 0.0007 * fbm(p, 260, 2, 4) + 0.003 * (fbm(p, 14, 3, 5) - 0.5)
        for s in (1, -1):
            k = np.array(C["knee"]) * np.array([s, 1, 1])
            dist = np.linalg.norm(p - k, axis=1)
            h += 0.0045 * ss(0.17, 0.02, dist) * (tri(z * 44 + 3 * vnoise(p, 11, 6)) - 0.5)
        # crotch / hip creases
        h += 0.004 * ss(0.12, 0.0, np.abs(z - (hem - 0.05))) * (tri(z * 40 + 2 * vnoise(p, 14, 8)) - 0.5)
        # ankle gather
        fz = C["foot_z"]
        h += 0.003 * ss(fz + 0.2, fz + 0.06, z) * (tri(z * 70 + 2 * vnoise(p, 20, 9)) - 0.5)
        # side seams
        sd = np.abs(np.abs(x) - C["thigh_outer"])
        h -= 0.0016 * ss(0.004, 0.0008, sd) * (z > fz + 0.1)
        # waistband under hoodie
        d[m] = h
    # ---------------- shoes
    m = pr == 4
    if m.any():
        p = P[m]; x, y, z = p[:, 0], p[:, 1], p[:, 2]
        h = 0.0005 * fbm(p, 200, 2, 10)
        ymin = C["shoe_ymin"]
        top = N[m][:, 2] > 0.25
        laces = top * ss(ymin + 0.065, ymin + 0.08, y) * ss(ymin + 0.19, ymin + 0.17, y) * ss(0.032, 0.02, np.abs(np.abs(x) - C["foot_x"]))
        h += 0.0028 * laces * np.clip(np.sin(y * 2 * np.pi / 0.0165) * 1.5, 0, 1)
        h -= 0.0022 * ss(0.0025, 0.0006, np.abs(y - (ymin + 0.07))) * top          # toe cap seam
        h -= 0.0028 * ss(0.003, 0.0008, np.abs(z - 0.034))                         # sole / upper seam
        h += 0.0018 * (z < 0.03) * (0.5 + 0.5 * np.sin(y * 2 * np.pi / 0.01))      # sole wall ridges
        d[m] = h
    # ---------------- gloves
    m = pr == 5
    if m.any():
        p = P[m]
        d[m] = 0.0008 * fbm(p, 230, 2, 11) + 0.0015 * (fbm(p, 40, 2, 12) - 0.5)
    # ---------------- beanie
    m = pr == 6
    if m.any():
        p = P[m]; x, y, z = p[:, 0], p[:, 1], p[:, 2]
        ang = np.arctan2(x, y - hc[1])
        s_back = np.clip((y - (hc[1] - 0.03)) / 0.09, 0, 1)
        thr = eye + 0.028 - 0.085 * s_back + 0.04 * ss(0.065, 0.09, np.abs(x)) * (1 - s_back)
        h = 0.0019 * tri(ang * 56 / (2 * np.pi)) + 0.0006 * fbm(p, 240, 2, 13)
        cuff = ss(thr + 0.04, thr + 0.034, z)
        h = h * (1 - 0.4 * cuff) + 0.0035 * cuff - 0.002 * ss(0.002, 0.0005, np.abs(z - (thr + 0.037)))
        d[m] = h
    # ---------------- mask
    m = pr == 7
    if m.any():
        p = P[m]
        d[m] = 0.0006 * fbm(p, 320, 2, 14) + 0.0004 * np.sin(p[:, 2] * 2 * np.pi / 0.004) * 0
    # ---------------- duffel
    m = pr == 8
    if m.any():
        p = P[m]; x, y, z = p[:, 0], p[:, 1], p[:, 2]
        cx, cy, cz = C["duffel_c"]
        h = 0.0010 * fbm(p, 280, 2, 15) + 0.0035 * (fbm(p, 12, 3, 16) - 0.5)
        zip_ = ss(0.007, 0.002, np.abs(y - cy)) * (z > cz + C["duffel_r"] * 0.7)
        h += 0.0016 * zip_ * (0.5 + 0.5 * np.sin(x * 2 * np.pi / 0.005))
        h -= 0.002 * ss(0.004, 0.001, np.abs(np.abs(x) - (C["duffel_L"] * 0.78)))     # end panel seams
        d[m] = h
    return d


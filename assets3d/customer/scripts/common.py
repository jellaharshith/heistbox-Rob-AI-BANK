# common helpers
import bpy, bmesh, numpy as np, math, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)

def get_co(me):
    a = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get('co', a)
    return a.reshape(-1, 3)

def new_obj(name, co, faces, collection=None, edges=()):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(c) for c in co], list(edges), [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob

def smooth(a, e0, e1):
    t = np.clip((a - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def decimate_to(ob, target_tris, vgroup=None, factor=1.0, symmetry=True):
    cur = tri_count(ob.data)
    ratio = min(1.0, target_tris / max(cur, 1))
    m = ob.modifiers.new("dec", 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.ratio = ratio
    m.use_collapse_triangulate = True
    if symmetry:
        m.use_symmetry = True
        m.symmetry_axis = 'X'
    if vgroup:
        m.vertex_group = vgroup
        m.vertex_group_factor = factor
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    ob.modifiers.remove(m)
    return me

class Source:
    """triangle soup + BVH for barycentric transfer"""
    def __init__(self, co, faces):
        self.co = np.asarray(co)
        tris = []
        for f in faces:
            for i in range(1, len(f) - 1):
                tris.append((f[0], f[i], f[i + 1]))
        self.tris = np.array(tris)
        self.bvh = BVHTree.FromPolygons([tuple(c) for c in self.co], [tuple(t) for t in tris])

    def query(self, p):
        loc, nrm, idx, dist = self.bvh.find_nearest(Vector(p))
        if idx is None:
            return None
        a, b, c = self.tris[idx]
        A, B, C = self.co[a], self.co[b], self.co[c]
        P = np.array(loc)
        v0, v1, v2 = B - A, C - A, P - A
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-18:
            return (a, b, c), np.array([1., 0, 0]), idx
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        return (a, b, c), np.array([1 - v - w, v, w]), idx

    def interp(self, pts, arrays):
        """arrays: list of (n_src, k) arrays; returns list of (n_pts, k)"""
        out = [np.zeros((len(pts), a.shape[1])) for a in arrays]
        for i, p in enumerate(pts):
            r = self.query(p)
            (a, b, c), w, _ = r
            for o, arr in zip(out, arrays):
                o[i] = arr[a] * w[0] + arr[b] * w[1] + arr[c] * w[2]
        return out

def set_weights(ob, W, bone_names, maxinf=4):
    """W: (nv, nb) dense -> vertex groups, top-4 normalized"""
    for vg in list(ob.vertex_groups):
        ob.vertex_groups.remove(vg)
    groups = [ob.vertex_groups.new(name=n) for n in bone_names]
    for vi in range(W.shape[0]):
        row = W[vi]
        idx = np.argsort(-row)[:maxinf]
        s = row[idx].sum()
        if s <= 1e-9:
            continue
        for j in idx:
            if row[j] > 1e-4:
                groups[j].add([vi], float(row[j] / s), 'REPLACE')

def select_only(*obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[-1]

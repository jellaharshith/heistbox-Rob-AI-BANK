import bpy, bmesh, numpy as np, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree


def new_obj_from_bm(bm, name, coll=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    o = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def extract_faces(src, face_sel, name):
    """copy faces (bool list per polygon index) of src to new object, keeping deform layer; returns obj"""
    bm = bmesh.new(); bm.from_mesh(src.data)
    bm.faces.ensure_lookup_table()
    lay = bm.verts.layers.int.get("src")
    if lay is None:
        lay = bm.verts.layers.int.new("src")
        for v in bm.verts:
            v[lay] = v.index
    kill = [f for f in bm.faces if not face_sel[f.index]]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    o = new_obj_from_bm(bm, name)
    bm.free()
    return o


def src_idx(obj):
    a = np.zeros(len(obj.data.vertices), dtype=np.int32)
    obj.data.attributes["src"].data.foreach_get("value", a)
    return a


def islands(me):
    """vertex -> island id via face connectivity"""
    n = len(me.vertices)
    parent = list(range(n))
    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for p in me.polygons:
        vs = p.vertices
        for i in range(1, len(vs)):
            a, b = f(vs[0]), f(vs[i])
            if a != b:
                parent[a] = b
    return np.array([f(i) for i in range(n)])


def clip_mesh(P, N, Dv, tris, f, name, extra=None):
    """Clip triangle mesh to region f>=0 with exact cuts (Sutherland-Hodgman per tri).
    Returns object with vertices at P + N*D (offset applied); also returns arrays (pos0, nrm0) for the new verts."""
    vmap = {}; cmap = {}
    pos0 = []; nrm0 = []; dd = []; faces = []
    def vid(i):
        k = vmap.get(i)
        if k is None:
            k = len(pos0); vmap[i] = k
            pos0.append(P[i]); nrm0.append(N[i]); dd.append(Dv[i])
        return k
    def cut(a, b):
        key = (a, b) if a < b else (b, a)
        k = cmap.get(key)
        if k is None:
            t = f[a] / (f[a] - f[b])
            k = len(pos0); cmap[key] = k
            pos0.append(P[a] * (1 - t) + P[b] * t)
            nn = N[a] * (1 - t) + N[b] * t
            nrm0.append(nn / max(np.linalg.norm(nn), 1e-9))
            dd.append(Dv[a] * (1 - t) + Dv[b] * t)
        return k
    for tri in tris:
        a, b, c = tri
        fa, fb, fc = f[a] >= 0, f[b] >= 0, f[c] >= 0
        n_in = fa + fb + fc
        if n_in == 3:
            faces.append((vid(a), vid(b), vid(c)))
        elif n_in == 0:
            continue
        else:
            out = []
            vs = (a, b, c)
            for i in range(3):
                u, v = vs[i], vs[(i + 1) % 3]
                iu, iv = f[u] >= 0, f[v] >= 0
                if iu:
                    out.append(vid(u))
                if iu != iv:
                    out.append(cut(u, v))
            if len(out) == 3:
                faces.append(tuple(out))
            elif len(out) == 4:
                faces.append((out[0], out[1], out[2])); faces.append((out[0], out[2], out[3]))
    pos0 = np.array(pos0, dtype=np.float32); nrm0 = np.array(nrm0, dtype=np.float32); dd = np.array(dd, dtype=np.float32)
    me = bpy.data.meshes.new(name)
    me.from_pydata(pos0.tolist(), [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o, pos0, nrm0, dd


def faces_major(me, vmask):
    vm = np.asarray(vmask)
    out = []
    for p in me.polygons:
        k = sum(1 for i in p.vertices if vm[i])
        out.append(k >= (3 if len(p.vertices) == 4 else 2))
    return out


def faces_all_verts(me, vmask):
    vm = np.asarray(vmask)
    return [bool(all(vm[i] for i in p.vertices)) for p in me.polygons]


def vertex_normals(me):
    n = np.zeros((len(me.vertices), 3), dtype=np.float32)
    me.vertices.foreach_get("normal", n.ravel())
    return n


def coords(me):
    a = np.zeros((len(me.vertices), 3), dtype=np.float32)
    me.vertices.foreach_get("co", a.ravel())
    return a


def set_coords(me, a):
    me.vertices.foreach_set("co", np.asarray(a, dtype=np.float32).ravel())
    me.update()


def decimate_to(obj, tris, symmetric=False, protect_boundary=True):
    me = obj.data
    cur = sum(len(p.vertices) - 2 for p in me.polygons)
    if cur <= tris:
        return cur
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    md = obj.modifiers.new("dec", 'DECIMATE')
    if protect_boundary:
        bm = bmesh.new(); bm.from_mesh(me)
        vg = obj.vertex_groups.new(name="keep")
        vg.add([v.index for v in bm.verts if v.is_boundary], 1.0, 'REPLACE')
        bm.free()
        md.vertex_group = "keep"; md.vertex_group_factor = 1.0; md.invert_vertex_group = True
    md.decimate_type = 'COLLAPSE'
    md.ratio = max(0.01, tris / cur)
    md.use_collapse_triangulate = True
    md.use_symmetry = symmetric
    md.symmetry_axis = 'X'
    bpy.ops.object.modifier_apply(modifier=md.name)
    if "keep" in obj.vertex_groups:
        obj.vertex_groups.remove(obj.vertex_groups["keep"])
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


class Transfer:
    """nearest-surface barycentric transfer of per-vertex arrays from hi-res source mesh"""
    def __init__(self, src_obj):
        self.src = src_obj
        me = src_obj.data
        me.calc_loop_triangles()
        self.tris = np.array([[t.vertices[0], t.vertices[1], t.vertices[2]] for t in me.loop_triangles], dtype=np.int64)
        self.tri_poly = np.array([t.polygon_index for t in me.loop_triangles], dtype=np.int64)
        self.P = coords(me)
        self.bvh = BVHTree.FromPolygons([tuple(p) for p in self.P.tolist()], [tuple(t) for t in self.tris.tolist()])
        # map from loop_triangle index -> bvh polygon index equals tri index (we built from tris)

    def weights_for(self, dst_obj):
        """returns (idx (n,3) int, bary (n,3) float) of nearest triangle for each vertex of dst (object-space coords)"""
        co = coords(dst_obj.data)
        idx = np.zeros((len(co), 3), dtype=np.int64)
        bar = np.zeros((len(co), 3), dtype=np.float32)
        for i, c in enumerate(co):
            loc, nor, fi, dist = self.bvh.find_nearest(Vector(c.tolist()))
            tv = self.tris[fi]
            a, b, c3 = self.P[tv[0]], self.P[tv[1]], self.P[tv[2]]
            p = np.array(loc)
            v0, v1, v2 = b - a, c3 - a, p - a
            d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
            d20, d21 = v2 @ v0, v2 @ v1
            den = d00 * d11 - d01 * d01
            if abs(den) < 1e-14:
                w = np.array([1, 0, 0], dtype=np.float32)
            else:
                v = (d11 * d20 - d01 * d21) / den
                w_ = (d00 * d21 - d01 * d20) / den
                u = 1 - v - w_
                w = np.clip(np.array([u, v, w_]), 0, None)
                w = w / max(w.sum(), 1e-9)
            idx[i] = tv; bar[i] = w
        return idx, bar

    @staticmethod
    def apply(arr, idx, bar):
        """arr (nsrc, k) -> (ndst, k)"""
        return (arr[idx] * bar[:, :, None]).sum(axis=1)


def assign_weights(obj, W, names, maxinf=4, cutoff=0.01):
    """W (n, ngroups) dense; names list of group names; replaces all vertex groups."""
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    vgs = [obj.vertex_groups.new(name=n) for n in names]
    for i in range(W.shape[0]):
        row = W[i]
        top = np.argsort(-row)[:maxinf]
        s = sum(row[j] for j in top if row[j] > cutoff)
        if s <= 0:
            continue
        for j in top:
            if row[j] > cutoff:
                vgs[j].add([i], float(row[j] / s), 'REPLACE')


def src_weight_matrix(src_obj):
    me = src_obj.data
    names = [g.name for g in src_obj.vertex_groups]
    W = np.zeros((len(me.vertices), len(names)), dtype=np.float32)
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return W, names


def add_shape_keys(obj, deltas):
    """deltas: dict name -> (n,3) array added to current coords"""
    base = coords(obj.data)
    obj.shape_key_add(name="Basis")
    for name, d in deltas.items():
        k = obj.shape_key_add(name=name, from_mix=False)
        k.data.foreach_set("co", (base + d).astype(np.float32).ravel())
        k.value = 0.0





def relax_boundary(obj, zmin, iters=15, fac=0.5):
    """Laplacian-relax boundary verts (z>zmin) along their loop, re-projected onto the original surface."""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bvh = BVHTree.FromBMesh(bm)
    bverts = [v for v in bm.verts if v.is_boundary and v.co.z > zmin]
    nb = {}
    for v in bverts:
        nb[v.index] = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
    for _ in range(iters):
        new = {}
        for v in bverts:
            ns = nb[v.index]
            if len(ns) == 2:
                avg = (ns[0].co + ns[1].co) / 2
                new[v.index] = v.co.lerp(avg, fac)
        for v in bverts:
            if v.index in new:
                loc, nor, fi, d = bvh.find_nearest(new[v.index])
                v.co = loc if loc is not None else new[v.index]
    bm.to_mesh(obj.data); bm.free()

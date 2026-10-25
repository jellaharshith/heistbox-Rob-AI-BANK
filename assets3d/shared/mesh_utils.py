"""
mesh_utils.py - generic bmesh/numpy helpers for building game characters from an MPFB base in headless Blender 5.x.
Public API (stable):
    ensure_object_mode()
    obj_from_bmesh(bm, name, collection=None)         -> Object
    copy_object(obj, name, shape_keys=False)          -> Object   (deep mesh copy, vertex groups kept)
    submesh_by_verts(obj, vert_mask, name, mode='all')-> Object   (faces whose verts are in mask; keeps UV + weights)
    submesh_by_faces(obj, face_mask, name)            -> Object
    offset_along_normals(obj, dist, ref_obj=None)     (dist: float or per-vertex array)
    add_rim(obj, inset=0.0, ref_coords=None)          close open boundary loops with a wall back to ref coords
    decimate_to_tris(obj, target_tris, delimit=('UV',), keep_shape_keys=False)
    tri_count(obj)
    closest_face_data(src_obj, dst_coords_world)      -> (poly_tri_verts, bary, dist) per dst point
    transfer_vertex_groups(src_obj, dst_obj, names=None)
    transfer_shape_keys(src_obj, dst_obj, vert_filter=None, max_dist=None)
    limit_and_normalize_weights(obj, max_influences=4, keep_prefix=None)
    set_group_weight(obj, group_name, weight=1.0)     all verts -> one group
    join(objs, name)                                  -> Object
    uv_scale_about_center(obj, factor)
    set_uv_rect(obj, rect, uv_name=None)              remap whole UV bbox into rect (u0,v0,u1,v1)
All coordinates are object space unless a name ends in _world. Characters should have identity transforms.
"""
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def ensure_object_mode():
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass


def _collection(collection):
    return collection or bpy.context.scene.collection


def obj_from_bmesh(bm, name, collection=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    _collection(collection).objects.link(ob)
    return ob


def _vgroup_copy(src, dst):
    # NOTE: never call dst.vertex_groups.clear() here - it wipes the weights already carried by the mesh.
    for vg in src.vertex_groups:
        if dst.vertex_groups.get(vg.name) is None:
            dst.vertex_groups.new(name=vg.name)


def copy_object(obj, name, shape_keys=False):
    """Copy mesh + vertex groups (no modifiers, no parent). Shape keys dropped unless shape_keys=True."""
    if shape_keys:
        me = obj.data.copy()
    else:
        bm = bmesh.new()
        bm.from_mesh(obj.data, use_shape_key=False)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
    me.name = name
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = obj.matrix_world
    _vgroup_copy(obj, ob)
    for c in obj.users_collection:
        c.objects.link(ob)
        break
    else:
        bpy.context.scene.collection.objects.link(ob)
    return ob


def _build_sub(obj, keep_faces_pred, name):
    bm = bmesh.new()
    bm.from_mesh(obj.data, use_shape_key=False)
    bm.faces.ensure_lookup_table()
    kill = [f for f in bm.faces if not keep_faces_pred(f)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.matrix_world = obj.matrix_world
    _vgroup_copy(obj, ob)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _remap_groups(src_obj, src_me_verts_idx_map, ob, bm_kept):
    pass


def submesh_by_verts(obj, vert_mask, name, mode='all'):
    """New object with the faces whose vertices are inside vert_mask (bool array). mode 'all'|'any'|'most'.
    Vertex-group weights are carried (bmesh deform layer)."""
    mask = np.asarray(vert_mask, dtype=bool)

    def pred(f):
        n = sum(1 for v in f.verts if mask[v.index])
        if mode == 'all':
            return n == len(f.verts)
        if mode == 'any':
            return n > 0
        return n >= len(f.verts) - 1
    return _build_sub(obj, pred, name)


def submesh_by_faces(obj, face_mask, name):
    fm = np.asarray(face_mask, dtype=bool)
    return _build_sub(obj, lambda f: fm[f.index], name)


def offset_along_normals(obj, dist, ref_obj=None):
    """Displace verts along smooth vertex normals. If ref_obj is given its normals are used via closest point."""
    me = obj.data
    me.calc_normals() if hasattr(me, "calc_normals") else None
    n = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertex_normals.foreach_get("vector", n)
    n = n.reshape(-1, 3)
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    d = np.asarray(dist, dtype=np.float32)
    if d.ndim == 0:
        d = np.full(len(co), float(d), dtype=np.float32)
    co = co + n * d[:, None]
    me.vertices.foreach_set("co", co.ravel())
    me.update()


def add_rim(obj, inset=0.0, ref_coords=None):
    """Close the gap at every boundary loop with a wall of quads going back to `ref_coords`
    (array of the pre-offset positions per vertex index, e.g. saved before offset_along_normals).
    New rim verts copy the deform weights and UV of the boundary vertex."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    deform = bm.verts.layers.deform.active
    uv = bm.loops.layers.uv.active
    bedges = [e for e in bm.edges if e.is_boundary]
    vmap = {}
    vmap_orig = {v.index: v for v in bm.verts}
    for e in bedges:
        for v in e.verts:
            if v.index in vmap:
                continue
            nv = bm.verts.new(v.co if ref_coords is None else Vector(ref_coords[v.index]))
            if inset:
                nv.co = nv.co - v.normal * inset
            if deform is not None:
                nv[deform] = v[deform]
            vmap[v.index] = nv
    for e in bedges:
        f = e.link_faces[0]
        a = b = None
        for l in f.loops:
            if l.edge == e:
                a, b = l.vert, l.link_loop_next.vert
                break
        try:
            nf = bm.faces.new((b, a, vmap[a.index], vmap[b.index]))
        except ValueError:
            continue
        if uv is not None:
            # wall is a thin sliver: every wall loop takes the uv of its boundary vertex
            uvs = {l.vert: l[uv].uv.copy() for l in f.loops}
            rev = {id(nv): ov for ov, nv in ((vmap_orig[k], vmap[k]) for k in vmap)}
            for l in nf.loops:
                ov = l.vert if l.vert in uvs else rev.get(id(l.vert))
                if ov is not None and ov in uvs:
                    l[uv].uv = uvs[ov]
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()


def tri_count(obj):
    me = obj.data
    return sum(len(p.vertices) - 2 for p in me.polygons)


def decimate_to_tris(obj, target_tris, delimit=('UV',), keep_shape_keys=False, triangulate=True, iterations=3):
    """Collapse-decimate obj (modifier applied) until <= target_tris. Shape keys must be removed first."""
    ensure_object_mode()
    if obj.data.shape_keys is not None:
        raise RuntimeError("remove shape keys before decimating")
    cur = tri_count(obj)
    if cur <= target_tris:
        return obj
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    ratio = target_tris / cur
    for it in range(iterations):
        m = obj.modifiers.new("dec", 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = max(0.02, min(1.0, ratio))
        m.use_collapse_triangulate = triangulate
        if delimit:
            try:
                m.delimit = set(delimit)
            except Exception as e:
                print("delimit", e)
        bpy.ops.object.modifier_apply(modifier=m.name)
        cur = tri_count(obj)
        if cur <= target_tris:
            break
        ratio = (target_tris / cur) * 0.98
    return obj


def _world_coords(obj):
    me = obj.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    M = np.array(obj.matrix_world, dtype=np.float32)
    return co @ M[:3, :3].T + M[:3, 3]


def closest_face_data(src_obj, dst_points):
    """For each point find the closest point on src_obj's (basis) surface.
    Returns tri vertex indices (N,3), barycentric weights (N,3), distance (N,). Uses the mesh basis coords."""
    me = src_obj.data
    bm = bmesh.new()
    bm.from_mesh(me, use_shape_key=False)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    tris = []
    bary = []
    dist = []
    for p in dst_points:
        loc, nor, idx, d = bvh.find_nearest(Vector(p))
        f = bm.faces[idx]
        vs = [v.index for v in f.verts]
        a, b, c = [bm.verts[i].co for i in vs]
        # barycentric of loc
        v0, v1, v2 = b - a, c - a, loc - a
        d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
        d20, d21 = v2.dot(v0), v2.dot(v1)
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-18:
            w = (1.0, 0.0, 0.0)
        else:
            v = (d11 * d20 - d01 * d21) / den
            wv = (d00 * d21 - d01 * d20) / den
            w = (1.0 - v - wv, v, wv)
        tris.append(vs)
        bary.append(w)
        dist.append(d)
    bm.free()
    return np.array(tris, dtype=np.int64), np.array(bary, dtype=np.float32), np.array(dist, dtype=np.float32)


def _coords_normals(obj):
    me = obj.data
    n = len(me.vertices)
    c = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", c)
    nn = np.empty(n * 3, dtype=np.float32); me.vertex_normals.foreach_get("vector", nn)
    return c.reshape(-1, 3), nn.reshape(-1, 3)


def closest_points(src_obj, pts):
    """closest surface point and interpolated normal on src (basis). Returns (pos, normal, dist)."""
    tris, bary, dist = closest_face_data(src_obj, pts)
    c, nn = _coords_normals(src_obj)
    pos = (c[tris] * bary[:, :, None]).sum(axis=1)
    nor = (nn[tris] * bary[:, :, None]).sum(axis=1)
    nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
    return pos, nor, dist


def smooth_shell(obj, iterations=8, factor=0.5, pin_boundary=True):
    """Laplacian smooth (numpy) with boundary verts pinned."""
    me = obj.data
    n = len(me.vertices)
    c = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", c); c = c.reshape(-1, 3)
    e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get("vertices", e); e = e.reshape(-1, 2)
    # boundary verts
    bm = bmesh.new(); bm.from_mesh(me); bm.edges.ensure_lookup_table()
    bnd = np.zeros(n, dtype=bool)
    for ed in bm.edges:
        if ed.is_boundary:
            bnd[ed.verts[0].index] = True; bnd[ed.verts[1].index] = True
    bm.free()
    deg = np.bincount(e.ravel(), minlength=n).astype(np.float32)
    for _ in range(iterations):
        acc = np.zeros_like(c)
        np.add.at(acc, e[:, 0], c[e[:, 1]])
        np.add.at(acc, e[:, 1], c[e[:, 0]])
        avg = acc / np.maximum(deg, 1)[:, None]
        new = c + (avg - c) * factor
        if pin_boundary:
            new[bnd] = c[bnd]
        c = new
    me.vertices.foreach_set("co", c.ravel())
    me.update()


def push_outside(obj, body_obj, min_dist):
    """Make sure every vertex is at least min_dist outside body_obj surface (along the body normal)."""
    me = obj.data
    n = len(me.vertices)
    c = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", c); c = c.reshape(-1, 3)
    pos, nor, dist = closest_points(body_obj, c)
    sd = ((c - pos) * nor).sum(axis=1)
    short = sd < min_dist
    c[short] = pos[short] + nor[short] * min_dist
    me.vertices.foreach_set("co", c.ravel())
    me.update()


def transfer_vertex_groups(src_obj, dst_obj, names=None):
    """Interpolate src vertex-group weights onto dst by closest surface point (both object-space aligned)."""
    me_s = src_obj.data
    dst_co = np.empty(len(dst_obj.data.vertices) * 3, dtype=np.float32)
    dst_obj.data.vertices.foreach_get("co", dst_co)
    dst_co = dst_co.reshape(-1, 3)
    tris, bary, dist = closest_face_data(src_obj, dst_co)
    gnames = names or [g.name for g in src_obj.vertex_groups]
    # dense weight matrix for src
    idx = {g.name: g.index for g in src_obj.vertex_groups}
    W = np.zeros((len(me_s.vertices), len(gnames)), dtype=np.float32)
    col = {n: i for i, n in enumerate(gnames)}
    for v in me_s.vertices:
        for g in v.groups:
            nm = src_obj.vertex_groups[g.group].name
            if nm in col:
                W[v.index, col[nm]] = g.weight
    Wd = (W[tris] * bary[:, :, None]).sum(axis=1)
    for n in gnames:
        if dst_obj.vertex_groups.get(n) is None:
            dst_obj.vertex_groups.new(name=n)
    for j, n in enumerate(gnames):
        vg = dst_obj.vertex_groups[n]
        col_w = Wd[:, j]
        for i in np.nonzero(col_w > 1e-4)[0]:
            vg.add([int(i)], float(col_w[i]), 'REPLACE')


def transfer_shape_keys(src_obj, dst_obj, vert_filter=None, max_dist=None, falloff=None):
    """Create on dst the same shape keys as src, deltas interpolated from the closest src face.
    vert_filter: bool array over dst verts that receive deltas (others 0). max_dist: zero beyond this distance
    (optionally smoothly with falloff=(d0,d1) -> weight 1 below d0, 0 above d1)."""
    sk = src_obj.data.shape_keys
    if sk is None:
        return
    n_dst = len(dst_obj.data.vertices)
    dst_co = np.empty(n_dst * 3, dtype=np.float32)
    dst_obj.data.vertices.foreach_get("co", dst_co)
    dst_co = dst_co.reshape(-1, 3)
    tris, bary, dist = closest_face_data(src_obj, dst_co)
    gate = np.ones(n_dst, dtype=np.float32)
    if vert_filter is not None:
        gate *= np.asarray(vert_filter, dtype=np.float32)
    if falloff is not None:
        d0, d1 = falloff
        gate *= np.clip((d1 - dist) / max(1e-9, d1 - d0), 0.0, 1.0)
    elif max_dist is not None:
        gate *= (dist <= max_dist)
    basis = sk.key_blocks[0]
    nv = len(src_obj.data.vertices)
    bco = np.empty(nv * 3, dtype=np.float32)
    basis.data.foreach_get("co", bco)
    bco = bco.reshape(-1, 3)
    if dst_obj.data.shape_keys is None:
        dst_obj.shape_key_add(name="Basis", from_mix=False)
    for kb in sk.key_blocks[1:]:
        kco = np.empty(nv * 3, dtype=np.float32)
        kb.data.foreach_get("co", kco)
        delta = kco.reshape(-1, 3) - bco
        dd = (delta[tris] * bary[:, :, None]).sum(axis=1) * gate[:, None]
        nk = dst_obj.shape_key_add(name=kb.name, from_mix=False)
        nk.data.foreach_set("co", (dst_co + dd).ravel())
        nk.slider_min, nk.slider_max = kb.slider_min, kb.slider_max
        nk.value = 0.0


def limit_and_normalize_weights(obj, max_influences=4, keep_prefix=None):
    """Keep the strongest `max_influences` groups per vertex and normalise. Optionally drop groups not starting with keep_prefix."""
    me = obj.data
    if keep_prefix:
        for vg in list(obj.vertex_groups):
            if not vg.name.startswith(keep_prefix):
                obj.vertex_groups.remove(vg)
    bm = bmesh.new()
    bm.from_mesh(me)
    deform = bm.verts.layers.deform.verify()
    for v in bm.verts:
        d = v[deform]
        items = sorted(d.items(), key=lambda kv: -kv[1])[:max_influences]
        tot = sum(w for _, w in items)
        d.clear()
        if tot <= 1e-8:
            continue
        for g, w in items:
            d[g] = w / tot
    bm.to_mesh(me)
    bm.free()
    me.update()


def set_group_weight(obj, group_name, weight=1.0):
    obj.vertex_groups.clear()
    vg = obj.vertex_groups.new(name=group_name)
    vg.add(list(range(len(obj.data.vertices))), weight, 'REPLACE')


def join(objs, name):
    ensure_object_mode()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    res = bpy.context.view_layer.objects.active
    res.name = name
    res.data.name = name
    return res


def uv_scale_about_center(obj, factor, uv_name=None):
    me = obj.data
    uvl = me.uv_layers[uv_name] if uv_name else me.uv_layers.active
    n = len(uvl.data)
    a = np.empty(n * 2, dtype=np.float32)
    uvl.data.foreach_get("uv", a)
    a = a.reshape(-1, 2)
    c = (a.min(0) + a.max(0)) * 0.5
    a = (a - c) * factor + c
    uvl.data.foreach_set("uv", a.ravel())


def set_uv_rect(obj, rect, uv_name=None, keep_aspect=False):
    """Remap the object's whole UV bounding box into rect=(u0,v0,u1,v1)."""
    me = obj.data
    uvl = me.uv_layers[uv_name] if uv_name else me.uv_layers.active
    n = len(uvl.data)
    a = np.empty(n * 2, dtype=np.float32)
    uvl.data.foreach_get("uv", a)
    a = a.reshape(-1, 2)
    lo, hi = a.min(0), a.max(0)
    span = np.maximum(hi - lo, 1e-9)
    u0, v0, u1, v1 = rect
    a = (a - lo) / span
    a[:, 0] = u0 + a[:, 0] * (u1 - u0)
    a[:, 1] = v0 + a[:, 1] * (v1 - v0)
    uvl.data.foreach_set("uv", a.ravel())

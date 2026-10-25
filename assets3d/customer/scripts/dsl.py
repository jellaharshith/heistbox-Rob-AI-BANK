# Node-expression DSL + procedural materials for baking
import bpy, math

REG = {}
class NB:
    cur = None
    def __init__(s, mat):
        mat.use_nodes = True
        s.mat = mat; s.nt = mat.node_tree; s.nt.nodes.clear()
        NB.cur = s
        s.out = None
    def set_in(s, sock, v):
        if isinstance(v, V): s.nt.links.new(v.s, sock)
        elif isinstance(v, (tuple, list)): sock.default_value = tuple(v) + (1.0,) * (len(sock.default_value) - len(v))
        else: sock.default_value = v

class V:
    def __init__(s, sock): s.s = sock
    def _bin(s, op, o, rev=False):
        nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeMath'); n.operation = op
        a, b = (o, s) if rev else (s, o)
        nb.set_in(n.inputs[0], a); nb.set_in(n.inputs[1], b)
        return V(n.outputs[0])
    def __add__(s, o): return s._bin('ADD', o)
    def __radd__(s, o): return s._bin('ADD', o, True)
    def __sub__(s, o): return s._bin('SUBTRACT', o)
    def __rsub__(s, o): return s._bin('SUBTRACT', o, True)
    def __mul__(s, o): return s._bin('MULTIPLY', o)
    def __rmul__(s, o): return s._bin('MULTIPLY', o, True)
    def __truediv__(s, o): return s._bin('DIVIDE', o)
    def __rtruediv__(s, o): return s._bin('DIVIDE', o, True)
    def __pow__(s, o): return s._bin('POWER', o)
    def __neg__(s): return s._bin('MULTIPLY', -1.0)

def fn1(op, a, b=None):
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeMath'); n.operation = op
    nb.set_in(n.inputs[0], a)
    if b is not None: nb.set_in(n.inputs[1], b)
    return V(n.outputs[0])
def absv(a): return fn1('ABSOLUTE', a)
def sqrtv(a): return fn1('SQRT', a)
def sinv(a): return fn1('SINE', a)
def fract(a): return fn1('FRACT', a)
def lt(a, b): return fn1('LESS_THAN', a, b)
def gt(a, b): return fn1('GREATER_THAN', a, b)
def vmin(a, b): return fn1('MINIMUM', a, b)
def vmax(a, b): return fn1('MAXIMUM', a, b)
def atan2(a, b): return fn1('ARCTAN2', a, b)
def clamp01(a):
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeMath'); n.operation = 'ADD'; n.use_clamp = True
    nb.set_in(n.inputs[0], a); n.inputs[1].default_value = 0.0
    return V(n.outputs[0])
def step(e0, e1, x):
    """smoothstep from e0 to e1 (e0>e1 allowed)"""
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeMapRange'); n.data_type = 'FLOAT'
    n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
    nb.set_in(n.inputs['Value'], x); nb.set_in(n.inputs['From Min'], e0); nb.set_in(n.inputs['From Max'], e1)
    n.inputs['To Min'].default_value = 0.0; n.inputs['To Max'].default_value = 1.0
    return V(n.outputs['Result'])
def pos():
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeNewGeometry')
    sp = nb.nt.nodes.new('ShaderNodeSeparateXYZ'); nb.nt.links.new(n.outputs['Position'], sp.inputs[0])
    return V(sp.outputs[0]), V(sp.outputs[1]), V(sp.outputs[2]), n.outputs['Position']
def attr(name):
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeAttribute'); n.attribute_name = name
    return V(n.outputs['Fac'])
def uvmap(name):
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeUVMap'); n.uv_map = name
    sp = nb.nt.nodes.new('ShaderNodeSeparateXYZ'); nb.nt.links.new(n.outputs['UV'], sp.inputs[0])
    return V(sp.outputs[0]), V(sp.outputs[1])
def combine(x, y, z):
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeCombineXYZ')
    nb.set_in(n.inputs[0], x); nb.set_in(n.inputs[1], y); nb.set_in(n.inputs[2], z)
    return n.outputs[0]
def noise(vec_sock, scale, detail=3.0, rough=0.5):
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeTexNoise'); n.noise_dimensions = '3D'
    nb.nt.links.new(vec_sock, n.inputs['Vector']); nb.set_in(n.inputs['Scale'], scale)
    n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    return V(n.outputs['Fac'])
def mixc(f, a, b):
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MIX'
    nb.set_in(n.inputs[0], f); nb.set_in(n.inputs[6], a); nb.set_in(n.inputs[7], b)
    return V(n.outputs[2])
def mulc(a, f):   # color * scalar
    nb = NB.cur; n = nb.nt.nodes.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MULTIPLY'
    nb.set_in(n.inputs[0], 1.0); nb.set_in(n.inputs[6], a)
    if isinstance(f, V):
        c = nb.nt.nodes.new('ShaderNodeCombineColor'); 
        for i in range(3): nb.nt.links.new(f.s, c.inputs[i])
        nb.nt.links.new(c.outputs[0], n.inputs[7])
    else: nb.set_in(n.inputs[7], (f, f, f))
    return V(n.outputs[2])
def pv(pos_sock, ox=0.0, oy=0.0, oz=0.0, sx=1.0, sy=1.0, sz=1.0):
    """position scaled/offset vector"""
    nb = NB.cur
    a = nb.nt.nodes.new('ShaderNodeVectorMath'); a.operation = 'ADD'
    nb.nt.links.new(pos_sock, a.inputs[0]); a.inputs[1].default_value = (ox, oy, oz)
    m = nb.nt.nodes.new('ShaderNodeVectorMath'); m.operation = 'MULTIPLY'
    nb.nt.links.new(a.outputs[0], m.inputs[0]); m.inputs[1].default_value = (sx, sy, sz)
    return m.outputs[0]

def finish(nb, color, rough, metal=0.0, alpha=1.0):
    """attach Emission->Output; returns pass setter"""
    nt = nb.nt
    em = nt.nodes.new('ShaderNodeEmission'); outn = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], outn.inputs[0])
    nb.em = em; nb.sockets = {}
    def asc(x):
        if isinstance(x, V): return x
        return x
    nb.pass_vals = dict(COLOR=color, ROUGH=rough, METAL=metal, ALPHA=alpha)
    REG[nb.mat.name] = nb
    return nb

def set_pass(mat, which):
    nb = REG[mat.name]
    em = [n for n in mat.node_tree.nodes if n.type == 'EMISSION'][0]
    val = nb.pass_vals[which]
    for l in list(em.inputs['Color'].links): mat.node_tree.links.remove(l)
    if isinstance(val, V): mat.node_tree.links.new(val.s, em.inputs['Color'])
    elif isinstance(val, (tuple, list)): em.inputs['Color'].default_value = tuple(val) + (1.0,)
    else: em.inputs['Color'].default_value = (val, val, val, 1.0)


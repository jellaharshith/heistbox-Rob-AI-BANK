import bpy

def _principled(m):
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL' and n.type != 'BSDF_PRINCIPLED':
            nt.nodes.remove(n)
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    o = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    if not o.inputs['Surface'].links:
        nt.links.new(b.outputs['BSDF'], o.inputs['Surface'])
    b.location = (400, 0); o.location = (700, 0)
    return nt, b

def tex_node(nt, img, loc, nonc=False, uvname=None):
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img
    t.location = loc
    t.interpolation = 'Linear'
    if uvname:
        u = nt.nodes.new('ShaderNodeUVMap')
        u.uv_map = uvname
        u.location = (loc[0] - 220, loc[1])
        nt.links.new(u.outputs['UV'], t.inputs['Vector'])
    return t

def get_gltf_group():
    name = "glTF Material Output"
    g = bpy.data.node_groups.get(name)
    if g: return g
    g = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    g.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
    return g

def pbr_mat(name, bc, orm=None, nrm=None, ao=None, ao_uv="UV_AO", emissive_tex=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, b = _principled(m)
    nt.links.clear() if False else None
    nt.links.new(b.outputs['BSDF'], next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    t = tex_node(nt, bc, (-300, 300))
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if orm:
        o = tex_node(nt, orm, (-600, 0))
        s = nt.nodes.new('ShaderNodeSeparateColor'); s.location = (-300, 0)
        nt.links.new(o.outputs['Color'], s.inputs['Color'])
        nt.links.new(s.outputs['Green'], b.inputs['Roughness'])
        nt.links.new(s.outputs['Blue'], b.inputs['Metallic'])
        if not ao:
            g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = get_gltf_group(); g.location = (100, -300)
            nt.links.new(s.outputs['Red'], g.inputs['Occlusion'])
    if nrm:
        n = tex_node(nt, nrm, (-600, -300))
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.location = (0, -300)
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if ao:
        a = tex_node(nt, ao, (-600, -600), uvname=ao_uv)
        sa = nt.nodes.new('ShaderNodeSeparateColor'); sa.location = (-300, -600)
        nt.links.new(a.outputs['Color'], sa.inputs['Color'])
        g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = get_gltf_group(); g.location = (100, -600)
        nt.links.new(sa.outputs['Red'], g.inputs['Occlusion'])
        nt.nodes.active = a
    return m

def runtime_mat(name, img):
    """Plain emissive image texture, UVs 0-1, no other inputs."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, b = _principled(m)
    b.inputs['Base Color'].default_value = (0, 0, 0, 1)
    b.inputs['Roughness'].default_value = 0.5
    t = tex_node(nt, img, (-300, 0))
    nt.links.new(t.outputs['Color'], b.inputs['Emission Color'])
    b.inputs['Emission Strength'].default_value = 1.0
    return m

def flat_mat(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, alpha=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, b = _principled(m)
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    if alpha is not None:
        b.inputs['Alpha'].default_value = alpha
        try: m.surface_render_method = 'BLENDED'
        except Exception: pass
        m.use_backface_culling = False
    return m

"""Export user-supplied production Blender characters as lightweight static web GLBs.

Usage: blender -b --factory-startup --python scripts/export_web_characters.py -- rain
The source files are only read. Complex Cycles shaders receive portable PBR materials.
"""
import bpy, json, sys, zipfile
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'rain': ROOT / 'assets3d/imported/Rain_v3.3/Rain v3.3/rain_v3.2.blend',
    'einar': ROOT / 'assets3d/imported/einar_v1/einar_release_v1.blend',
    'ellie': ROOT / 'ellie.blend',
    'security-bot': ROOT / 'assets3d/imported/security_bot_v1/security_bot_v1/security_bot_release_v1.blend',
}
name = sys.argv[sys.argv.index('--') + 1]
if name not in SOURCES:
    raise SystemExit('Choose rain, einar, ellie, or security-bot')
if not SOURCES[name].exists() and name != 'ellie':
    archives={'rain':'Rain v3.3.zip','einar':'einar_v1.zip','security-bot':'security_bot_v1.zip'}
    archive=ROOT/archives[name]
    destination=ROOT/'assets3d/imported'/archive.stem.replace(' ','_')
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            resolved=(destination/member.filename).resolve()
            if not resolved.is_relative_to(destination.resolve()):
                raise ValueError('Archive contains a path outside the extraction folder')
        zipped.extractall(destination)
bpy.ops.wm.open_mainfile(filepath=str(SOURCES[name]), load_ui=False)
print('EXPORT_START', name, flush=True)

# Ellie ships both a viewport hairstyle and a strand groom. Use the authored
# viewport mesh because strand particle hair is unsupported by glTF.
if name == 'ellie':
    hair=bpy.data.objects.get('GEO-ellie_hair')
    if hair:
        hair.hide_render=False
        hair.hide_set(False)

# Einar's legacy native strand curves fail Blender 5.2 geometry evaluation.
# Export the supported surface meshes; the untouched source retains its groom.

def nodes_recursive(tree):
    if not tree: return []
    result = list(tree.nodes)
    for n in tree.nodes:
        if n.type == 'GROUP' and n.node_tree:
            result += nodes_recursive(n.node_tree)
    return result

def color_for(label):
    n=label.lower()
    if name=='security-bot':
        if 'emit' in n: return (0.04,0.8,0.65,1)
        if 'black' in n or 'hose' in n: return (0.018,0.024,0.028,1)
        if 'white' in n: return (0.74,0.76,0.68,1)
        if 'letter' in n: return (0.018,0.024,0.028,1)
        return (0.24,0.28,0.3,1)
    if any(s in n for s in ['skin','body','head','hand','face','ear']): return (0.53,0.31,0.20,1)
    if any(s in n for s in ['hair','beard','brow','lash']): return (0.055,0.025,0.016,1)
    if any(s in n for s in ['teeth','sclera','eye_white']): return (0.8,0.8,0.72,1)
    if 'eye' in n or 'iris' in n: return (0.055,0.15,0.18,1)
    if any(s in n for s in ['gum','tongue']): return (0.38,0.08,0.075,1)
    if 'scarf' in n: return (0.36,0.05,0.035,1)
    if 'jean' in n: return (0.028,0.08,0.13,1)
    if any(s in n for s in ['shoe','sole','rubber']): return (0.04,0.035,0.03,1)
    if name=='security-bot': return (0.3,0.35,0.33,1)
    if any(s in n for s in ['metal','robot','arm','finger']): return (0.24,0.28,0.27,1)
    return (0.12,0.22,0.20,1)

material_cache = {}
def portable_material(old):
    if old.name in material_cache: return material_cache[old.name]
    nodes=nodes_recursive(old.node_tree)
    ps=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
    base=color_for(old.name)
    if ps:
        inp=ps.inputs.get('Base Color')
        if inp and not inp.is_linked: base=tuple(inp.default_value)
    m=bpy.data.materials.new(old.name+'_web')
    m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=base
    p.inputs['Roughness'].default_value=0.65
    p.inputs['Metallic'].default_value=0.5 if any(s in old.name.lower() for s in ['metal','robot','steel']) else 0
    if name=='security-bot' and 'emit' in old.name.lower():
        p.inputs['Emission Color'].default_value=(0.04,0.8,0.65,1)
        p.inputs['Emission Strength'].default_value=2
    images=[n.image for n in nodes if n.type=='TEX_IMAGE' and n.image]
    diffuse=next((i for i in images if any(s in i.name.lower() for s in ['diffuse','albedo','color_base','base_color','clothing.color','hair.color','eyes']) and not any(s in i.name.lower() for s in ['dirt','bruise','distress','direction']) and 'cornea' not in old.name.lower()),None)
    if diffuse and diffuse.source != 'TILED':
        try:
            if max(diffuse.size)>1024:
                factor=1024/max(diffuse.size)
                diffuse.scale(max(1,int(diffuse.size[0]*factor)),max(1,int(diffuse.size[1]*factor)))
            tex=m.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image=diffuse
            m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
        except Exception as e: print('TEXTURE_SKIP',old.name,str(e),flush=True)
    if 'cornea' in old.name.lower():
        p.inputs['Alpha'].default_value=0.12
        p.inputs['Roughness'].default_value=0.05
        m.surface_render_method='DITHERED'
    material_cache[old.name]=m
    print('MATERIAL',old.name, 'base',list(base),'image', diffuse.name if diffuse else None,flush=True)
    return m

source_objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.visible_get() and not o.hide_render and len(o.data.polygons)>0 and not any(s in o.name.lower() for s in ['wgt','widget','control','ground','floor','backdrop'])]
print('VISIBLE_MESHES',[(o.name,len(o.data.vertices)) for o in source_objects],flush=True)
for o in source_objects:
    for mod in o.modifiers:
        if mod.type in {'SUBSURF','MULTIRES','PARTICLE_SYSTEM'}:
            mod.show_viewport=False
            mod.show_render=False
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
exports=[]
for o in source_objects:
    mesh=bpy.data.meshes.new_from_object(o.evaluated_get(deps),depsgraph=deps,preserve_all_data_layers=True)
    obj=bpy.data.objects.new(o.name+'_web',mesh)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world=o.matrix_world.copy()
    for i,mat in enumerate(list(mesh.materials)):
        if mat: mesh.materials[i]=portable_material(mat)
    exports.append(obj)
    print('MESH',obj.name,len(mesh.vertices),len(mesh.polygons),flush=True)

for o in list(bpy.context.scene.objects):
    if o not in exports: bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
for o in exports:
    o.hide_set(False)
    o.hide_render=False
    o.select_set(True)
    bpy.context.view_layer.objects.active=o
    if len(o.data.polygons)>45000:
        mod=o.modifiers.new('Web reduction','DECIMATE')
        mod.ratio=45000/len(o.data.polygons)
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for poly in o.data.polygons: poly.use_smooth=True
bpy.context.view_layer.update()
coords=[o.matrix_world@Vector(c) for o in exports for c in o.bound_box]
lo=Vector([min(v[i] for v in coords) for i in range(3)])
hi=Vector([max(v[i] for v in coords) for i in range(3)])
scale=2/max(hi.z-lo.z,0.01)
offset=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
for o in exports:
    o.location=(o.location-offset)*scale
    o.scale*=scale
bpy.context.view_layer.update()
for o in exports:
    # Bake a relaxed arm stance into this static web copy. The production rigs
    # remain untouched; all meshes share the same smooth shoulder rotation.
    # Ellie and Einar have accessory meshes that cross the shoulder region;
    # preserve their authored poses to keep straps, hair, and sleeves intact.
    if name == 'rain':
        world=o.matrix_world.copy()
        inv=world.inverted()
        for vert in o.data.vertices:
            pos=world@vert.co
            side=1 if pos.x>0 else -1
            shoulder=0.15 if name!='einar' else 0.21
            blend=min(1,max(0,(abs(pos.x)-shoulder)/0.12))
            # Smoothly fade the deformation at both vertical boundaries. Hard
            # cutoffs split adjacent shoulder vertices into different poses.
            def smoothstep(a,b,value):
                t=min(1,max(0,(value-a)/(b-a)))
                return t*t*(3-2*t)
            blend*=smoothstep(0.95,1.20,pos.z)
            blend*=1-smoothstep(1.70,1.94,pos.z)
            if blend<=0: continue
            pivot=Vector((side*shoulder,0,1.50 if name!='ellie' else 1.40))
            rotated=pivot+Matrix.Rotation(side*0.75*blend,3,'Y')@(pos-pivot)
            vert.co=inv@rotated
out=ROOT/'web/public/characters'/f'{name}.glb'
out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_animations=False,export_apply=True,export_image_format='JPEG',export_jpeg_quality=82,export_texcoords=True,export_normals=True,export_materials='EXPORT')
report={'name':name,'file':str(out),'bytes':out.stat().st_size,'meshes':len(exports),'vertices':sum(len(o.data.vertices) for o in exports),'polygons':sum(len(o.data.polygons) for o in exports),'source':str(SOURCES[name]),'bounds':{'min':list(lo),'max':list(hi)}}
reports=ROOT/'assets3d/export/reports'; reports.mkdir(parents=True,exist_ok=True)
(reports/f'{name}.json').write_text(json.dumps(report,indent=2))
print('EXPORT_DONE',json.dumps(report),flush=True)

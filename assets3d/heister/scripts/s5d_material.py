"""Stage 5d: clean asset blend (no hi-res), one material MAT_Heister (BaseColor/ORM/Normal) on all meshes. s5a -> heister_s5d.blend"""
import bpy, os, sys, json
H = r"C:\Users\Shaik\Downloads\heistbox\assets3d\heister"
bpy.ops.wm.open_mainfile(filepath=os.path.join(H, "heister_s5a.blend"))
O = bpy.data.objects
for n in ("HI_all", "HI_duffel", "Body_hi"):
    if n in O:
        bpy.data.objects.remove(O[n], do_unlink=True)
for c in list(bpy.data.collections):
    if c.name == "HI_src":
        bpy.data.collections.remove(c)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)

def load(name, cs):
    im = bpy.data.images.load(os.path.join(H, "textures", name + ".png"))
    im.colorspace_settings.name = cs
    im.pack()
    return im
bc = load("Heister_BaseColor", "sRGB"); orm = load("Heister_ORM", "Non-Color"); nm = load("Heister_Normal", "Non-Color")
mat = bpy.data.materials.new("MAT_Heister"); mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (900, 0)
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (600, 0)
nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
t1 = nt.nodes.new("ShaderNodeTexImage"); t1.image = bc; t1.location = (-400, 300)
t2 = nt.nodes.new("ShaderNodeTexImage"); t2.image = orm; t2.location = (-400, 0)
t3 = nt.nodes.new("ShaderNodeTexImage"); t3.image = nm; t3.location = (-400, -300)
nt.links.new(t1.outputs["Color"], bsdf.inputs["Base Color"])
sep = nt.nodes.new("ShaderNodeSeparateColor"); sep.location = (-100, 0)
nt.links.new(t2.outputs["Color"], sep.inputs["Color"])
nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.location = (200, -300)
nt.links.new(t3.outputs["Color"], nmap.inputs["Color"])
nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
# glTF occlusion via the official custom group
grp = bpy.data.node_groups.new("glTF Material Output", 'ShaderNodeTree')
grp.interface.new_socket("Occlusion", in_out='INPUT', socket_type='NodeSocketFloat')
g = nt.nodes.new("ShaderNodeGroup"); g.node_tree = grp; g.location = (300, 200)
nt.links.new(sep.outputs["Red"], g.inputs["Occlusion"])
for o in O:
    if o.type == 'MESH':
        o.data.materials.clear()
        o.data.materials.append(mat)
print("material users", mat.users)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(H, "heister_s5d.blend"))

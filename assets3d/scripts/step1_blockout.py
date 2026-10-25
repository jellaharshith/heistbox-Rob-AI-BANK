import bpy, bmesh, math
from mathutils import Vector

ROOT = r"C:\Users\Shaik\Downloads\heistbox\assets3d"

# ---- clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)

def coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c

def mat(name, color, rough=0.5, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m

M = {
    "MAT_Marble": mat("MAT_Marble", (0.02, 0.022, 0.028), 0.12),
    "MAT_Wall": mat("MAT_Wall", (0.07, 0.075, 0.09), 0.8),
    "MAT_Brass": mat("MAT_Brass", (0.75, 0.55, 0.2), 0.3, 1.0),
    "MAT_Wood": mat("MAT_Wood", (0.12, 0.06, 0.03), 0.5),
    "MAT_Steel": mat("MAT_Steel", (0.35, 0.37, 0.4), 0.35, 1.0),
    "MAT_Ice": mat("MAT_Ice", (0.55, 0.8, 1.0), 0.3, 0.2),
    "MAT_Gunmetal": mat("MAT_Gunmetal", (0.12, 0.13, 0.15), 0.4, 1.0),
}

def box(name, size, loc, material, col):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]; v.co.y *= size[1]; v.co.z *= size[2]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = loc
    o.data.materials.append(M[material])
    col.objects.link(o)
    return o

env = coll("ENV_BankHall")
vaults = coll("VAULTS")
empties = coll("EMPTIES")

W, D, H = 16.0, 12.0, 4.6          # hall: x in [-8,8], y in [-6,6]
# floor / ceiling / walls
box("ENV_Floor", (W, D, 0.1), (0, 0, -0.05), "MAT_Marble", env)
box("ENV_Ceiling", (W, D, 0.1), (0, 0, H + 0.05), "MAT_Wall", env)
box("ENV_WallFront", (W, 0.2, H), (0, -D/2, H/2), "MAT_Wall", env)
box("ENV_WallLeft", (0.2, D, H), (-W/2, 0, H/2), "MAT_Wall", env)
box("ENV_WallRight", (0.2, D, H), (W/2, 0, H/2), "MAT_Wall", env)

# back wall with three alcoves (alcove width 3.6, pitch 4.6) recessed 1.8 m
yb = D/2           # 6.0 back face of the hall
rec = 1.8
xs = [-4.6, 0.0, 4.6]
aw = 3.6
box("ENV_BackWall_Rear", (W, 0.2, H), (0, yb + rec, H/2), "MAT_Wall", env)
# front back-wall segments between/outside alcoves
edges = [-W/2, xs[0]-aw/2, xs[0]+aw/2, xs[1]-aw/2, xs[1]+aw/2, xs[2]-aw/2, xs[2]+aw/2, W/2]
for i in range(0, len(edges), 2):
    x0, x1 = edges[i], edges[i+1]
    if x1 - x0 > 0.01:
        box(f"ENV_Pillar{i//2}", (x1 - x0, 0.2, H), ((x0+x1)/2, yb, H/2), "MAT_Wall", env)
for i, x in enumerate(xs):
    for s in (-1, 1):
        box(f"ENV_AlcoveSide{i}{'L' if s<0 else 'R'}", (0.15, rec, H), (x + s*aw/2, yb + rec/2, H/2), "MAT_Wall", env)
    box(f"ENV_AlcoveTrim{i}", (aw + 0.3, 0.1, 0.12), (x, yb - 0.05, 3.4), "MAT_Brass", env)

# teller counter (long, between player and Tina) at y=0
box("ENV_Counter_Top", (6.0, 1.0, 0.08), (0, 0, 1.1), "MAT_Wood", env)
box("ENV_Counter_Body", (5.9, 0.9, 1.06), (0, 0, 0.53), "MAT_Wood", env)
box("ENV_Counter_Trim", (6.1, 0.05, 0.1), (0, -0.52, 1.0), "MAT_Brass", env)
box("ENV_Counter_Glass", (6.0, 0.04, 0.7), (0, 0.25, 1.49), "MAT_Ice", env)

# vault placeholders: round door r=1.1, origin at hinge (left edge), facing -Y
def vault_door(name, x, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.1, depth=0.4,
                                        rotation=(math.radians(90), 0, 0))
    o = bpy.context.active_object
    o.name = name
    o.data.name = name
    bpy.ops.object.transform_apply(rotation=True)
    # shift mesh so hinge is the origin
    for v in o.data.vertices:
        v.co.x += 1.1
    o.location = (x - 1.1, yb + 0.5, 1.6)
    o.data.materials.append(M[material])
    for c in o.users_collection:
        c.objects.unlink(o)
    vaults.objects.link(o)
    return o

vault_door("VAULT_L_Door", xs[0], "MAT_Brass")
vault_door("VAULT_M_Door", xs[1], "MAT_Ice")
vault_door("VAULT_R_Door", xs[2], "MAT_Gunmetal")

# vault floor plates for visual separation
for n, x, m in (("L", xs[0], "MAT_Brass"), ("M", xs[1], "MAT_Ice"), ("R", xs[2], "MAT_Gunmetal")):
    box(f"ENV_VaultPlate_{n}", (aw - 0.3, 1.4, 0.03), (x, yb + 0.9, 0.015), m, env)

# empties
def empty(name, loc, target=None, disp="ARROWS", size=0.4):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = disp
    e.empty_display_size = size
    e.location = loc
    if target is not None:
        d = Vector(target) - Vector(loc)
        e.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    empties.objects.link(e)
    return e

empty("SPAWN_Player", (0, -4.5, 0), target=(0, 0, 0), disp="SINGLE_ARROW")
empty("SPAWN_Customer", (-2.6, -2.2, 0), target=(0, 0, 0), disp="SINGLE_ARROW")
empty("CAM_Overview", (0, -5.6, 3.2), target=(0, 3.5, 1.3))
empty("CAM_VaultL", (xs[0], yb - 2.8, 1.7), target=(xs[0], yb + 0.5, 1.6))
empty("CAM_VaultM", (xs[1], yb - 2.8, 1.7), target=(xs[1], yb + 0.5, 1.6))
empty("CAM_VaultR", (xs[2], yb - 2.8, 1.7), target=(xs[2], yb + 0.5, 1.6))
empty("ANCHOR_LaserTarget", (0, 0.5, 1.5), disp="SPHERE", size=0.15)

# preview-only light + camera
ld = bpy.data.lights.new("PreviewLight", 'AREA'); ld.energy = 600; ld.size = 6
lo = bpy.data.objects.new("PreviewLight", ld); lo.location = (0, 0, 4.3)
bpy.context.scene.collection.objects.link(lo)
cd = bpy.data.cameras.new("PreviewCam"); cd.lens = 28
co = bpy.data.objects.new("PreviewCam", cd); co.location = (0, -5.8, 3.0)
co.rotation_euler = (Vector((0, 3.5, 1.3)) - co.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.collection.objects.link(co)
bpy.context.scene.camera = co

sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
sc.render.fps = 30
bpy.ops.wm.save_as_mainfile(filepath=ROOT + r"\heistbox_assets.blend")
print("saved", len(bpy.data.objects), "objects")

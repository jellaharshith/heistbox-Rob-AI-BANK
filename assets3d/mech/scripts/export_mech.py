import bpy, os
ROOT = r"C:\Users\Shaik\Downloads\heistbox\assets3d\mech"
OUT = os.environ.get("MECH_OUT", ROOT + r"\export")
# OPT=0 keeps constant (static) animation channels, needed for the VAULT_L_Door_Ajar clip
OPT = os.environ.get("OPT", "1") == "1"
bpy.ops.wm.open_mainfile(filepath=ROOT + r"\MECH.blend")
props = bpy.ops.export_scene.gltf.get_rna_type().properties
names = set(props.keys())


def export(coll_name, path):
    for o in bpy.data.objects:
        o.select_set(False)
    for o in bpy.data.collections[coll_name].objects:
        o.select_set(True)
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_animation_mode='NLA_TRACKS',
              export_yup=True, export_apply=True, export_cameras=False, export_lights=False,
              export_image_format='AUTO', export_skins=False, export_morph=False,
              export_optimize_animation_size=OPT, export_optimize_animation_keep_anim_object=True)
    kw = {k: v for k, v in kw.items() if k in names}
    r = bpy.ops.export_scene.gltf(**kw)
    print("EXPORT", path, r)


export("MECH_VaultProps", OUT + r"\VAULT_PROPS.glb")
export("CHAR_Sentinel", OUT + r"\CHAR_Sentinel.glb")



# ---- patch node rest rotations in the raw GLB: L door ajar (-12 deg about hinge/Z -> glTF Y), M/R closed (identity)
import json, struct, math
def patch_rest(path):
    b = open(path, 'rb').read()
    jl = struct.unpack('<I', b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    a = math.radians(-12) / 2
    for n in j['nodes']:
        if n.get('name') == 'VAULT_L_Door':
            n['rotation'] = [0.0, math.sin(a), 0.0, math.cos(a)]
        elif n.get('name') in ('VAULT_M_Door', 'VAULT_R_Door'):
            n.pop('rotation', None)
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    rest = b[20 + jl:]
    out = b[:12] + struct.pack('<I', len(js)) + b'JSON' + js + rest
    out = out[:8] + struct.pack('<I', len(out)) + out[12:]
    open(path, 'wb').write(out)
    print("PATCHED rest rotations", path)
patch_rest(OUT + r"\VAULT_PROPS.glb")


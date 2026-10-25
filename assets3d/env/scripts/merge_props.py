"""Headless merge: PROPS_own.glb + mech VAULT_PROPS.glb (+ customer PROP_Phone.glb) -> env/export/PROPS.glb
usage: blender -b -P merge_props.py -- out.glb in1.glb in2.glb ..."""
import bpy, sys
args = sys.argv[sys.argv.index("--") + 1:]
out, ins = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30   # BEFORE import: the importer converts seconds->frames at scene fps (24 default shrank every clip by 0.8)
for f in ins:
    bpy.ops.import_scene.gltf(filepath=f)
    print("IMPORTED", f)
objs = [o for o in bpy.data.objects if o.type in ('MESH', 'EMPTY', 'ARMATURE')]
# strip duplicate suffix on materials if a name collided and the original is unused
for o in objs:
    if o.animation_data:
        print("ANIM", o.name, o.animation_data.action.name if o.animation_data.action else None,
              [t.name for t in o.animation_data.nla_tracks])
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.context.scene.render.fps = 30
for o in objs:   # make sure only NLA tracks drive export (no active action left over)
    ad = o.animation_data
    if ad and ad.action and ad.nla_tracks:
        ad.action = None
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_cameras=False, export_lights=False,
    export_yup=True, export_apply=False, export_animations=True, export_animation_mode='NLA_TRACKS',
    export_image_format='AUTO', export_skins=True, export_morph=True)
print("MERGED", out)
# post-process: Blender cannot write EXT_mesh_gpu_instancing -> collapse the 12 PROP_CashHeist_Bundle.NN nodes (shared mesh CASH_Bundle)
# into one instanced node (needs node + env/scripts/node/node_modules)
import subprocess, os
_nd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "node")
_r = subprocess.run(["node", os.path.join(_nd, "instance_cash.mjs"), out, out], cwd=_nd, capture_output=True, text=True, shell=(os.name == "nt"))
print("INSTANCE_CASH rc", _r.returncode, _r.stdout.strip(), _r.stderr.strip()[:500])
if _r.returncode != 0: raise SystemExit("instance_cash.mjs failed")

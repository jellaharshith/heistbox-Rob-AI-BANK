"""Stage 7: save final blend + export CHAR_Tina.glb"""
import sys
sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")
import bpy
import export_utils as eu

ROOT = r"C:/Users/Shaik/Downloads/heistbox/assets3d/tina"
bpy.ops.wm.open_mainfile(filepath=ROOT + "/scripts/_stage6.blend")
arm = bpy.data.objects["CHAR_Tina"]
lods = [bpy.data.objects["CHAR_Tina_LOD%d" % i] for i in range(3)]
# clean up leftovers
for m in list(bpy.data.materials):
    if m.users == 0:
        bpy.data.materials.remove(m)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=ROOT + "/CHAR_Tina.blend")
eyes = [bpy.data.objects[n] for n in ("CHAR_Tina_Eyes", "CHAR_Tina_EyeL", "CHAR_Tina_EyeR")]
r = eu.export_glb([arm] + lods + eyes, ROOT + "/export/CHAR_Tina.glb")
print("export", r)

# assets3d/shared - reusable headless Blender 5.2 helpers (written by the Tina agent)

Use: `import sys; sys.path.insert(0, r"C:/Users/Shaik/Downloads/heistbox/assets3d/shared")` inside a script run with
`blender.exe -b -P script.py`. Start scripts with `bpy.ops.wm.read_factory_settings(use_empty=True)`.
Please do not change published function signatures; add new functions instead.

| module | purpose |
|---|---|
| `mpfb_base.py` | enable MPFB2 headless, `build_human(gender, age, ..., rig="mixamo")` -> (body, armature) with Mixamo bone names (`mixamorig:Hips`...), 52 bones, weights, helpers stripped; `load_unit_targets()` loads MakeHuman expression units as shape keys; `dominant_bone_map()` |
| `mesh_utils.py` | bmesh/numpy helpers: `submesh_by_verts`, `offset_along_normals`, `smooth_shell`, `push_outside`, `add_rim`, `decimate_to_tris`, `closest_points`, `transfer_vertex_groups`, `transfer_shape_keys`, `limit_and_normalize_weights`, `set_group_weight`, `join`, `set_uv_rect` |
| `bake_utils.py` | Cycles baking: `setup_cycles`, `new_image`, `make_target_material`, `bake_pass` (selected-to-active hi->lo for DIFFUSE/ROUGHNESS/NORMAL, AO), `image_to_array`, `linear_to_srgb`, `save_png_raw`, `pack_orm` |
| `preview_utils.py` | `shot()` Workbench/Cycles preview PNG, `montage()` |
| `nla_utils.py` | slotted-action aware `make_clip()` -> one Action per NLA track at 30 fps, `push_clip()`, loop helpers |
| `export_utils.py` | `export_glb()` (NLA_TRACKS, deform bones only, no lights/cameras), `optimize()` (gltf-transform meshopt+webp), `reimport_report()` (clips, bones, shape keys, tris) |

## Hard-won notes
* MPFB module: `bl_ext.user_default.mpfb`. gender 0 = female. `rig="mixamo"` already gives `mixamorig:` names, A-pose rest.
  Expression-unit targets (eyes/brows/mouth) exist under `data/targets/expression/units/<race>/`; viseme/ARKit packs are NOT installed, so
  build visemes by mixing unit targets (see `tina/scripts/s1_base.py`).
* Character left = +X, front = -Y (MPFB). Mixamo "Left*" bones are on +X.
* Cycles bake: assign the target material (active Image Texture node) to the low mesh; use float Non-Color images and sRGB-encode albedo
  yourself; `margin_type='EXTEND'`; AO bake with `use_selected_to_active=False`.
* glTF alpha clip is detected from nodes: Image Alpha -> Math GREATER_THAN 0.5 -> Principled Alpha (exports alphaMode MASK).
  Occlusion needs a node group named `glTF Material Output` with a float input `Occlusion`.
* Shape keys: decimate before adding keys (modifier apply fails with keys); use `transfer_shape_keys` from the full-res body.

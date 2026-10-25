# HeistBox asset pack - FIX PASS shared brief (read together with SPEC.md; SPEC.md stays authoritative)

Main agent has already built the verification tools. USE THEM, and do not report an item done until you have verified it with them.

## Hard rules
- NEVER rename anything in the integration contract (SPEC.md: object / material / clip / empty names, mixamorig bone names, shape-key names).
  Adding NEW names is fine. Do not remove existing contract clips/objects.
- Stay inside your own folder `assets3d/<asset>/` (own .blend, scripts/, textures/, shots/, export/). Do not edit other agents' folders,
  `heistbox_assets.blend`, `assets3d/export/`, `assets3d/scripts/`, `assets3d/viewer/`, `assets3d/shared/*` (you may ADD a new file to shared/ if really
  needed, never change existing signatures). Put re-runnable scripts in `<asset>/scripts/`.
- Blender: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b <file.blend> -P script.py` (headless, one process per agent). DO NOT use the
  live-Blender MCP tools. Back up the .blend you start from (copy to e.g. `<name>_prefix.blend`) before changing it.
- Shell is Windows PowerShell 5.1 (no `&&`). cwd may drift: always use absolute paths. Do not use `\n` inside PowerShell strings to make newlines in files; use the Write tool.
- Budgets (SPEC.md) must still hold afterwards: LOD0 <= 15k tris (LOD1 <= 7k, LOD2 <= 3k), <= 65 bones, <= 4 weights/vertex, char GLB <= 4 MB optimized,
  scene <= 150k tris and <= 40 draw calls scene-wide (currently 35 draw calls: every NEW material/primitive costs one; you may add at most ONE extra
  material per character file and only if you cannot fold it into the existing atlas).
- You may be blocked from writing REPORT.md. Try to write `<asset>/NOTES_FIXPASS.md`; if blocked, put everything in your final message. Either way your FINAL MESSAGE
  must contain the notes (see "Final message").

## Tools (all under `assets3d/`, run from any cwd with absolute paths)
- `node C:\Users\Shaik\Downloads\heistbox\assets3d\scripts\shot.mjs --src <glb path> --out <png path> [--clip Name --t 0.5] [--pose rest] [--view front|side|back|3q|head|headside|head3q|upper|top] [--morph viseme_PP:1,jawOpen:0.3] [--size 640x800] [--hide NodeA,NodeB] [--lod 0]`
  Renders the GLB in the three.js viewer (headless Chrome) = what the game will see. `--src` may be an absolute path to ANY .glb (use your raw `<asset>/export/*.glb`).
  `--pose rest` = the glTF rest pose (T/A pose). `--clip X --t 0.5` = clip X sampled at 0.5 s. Batch mode: `--batch jobs.json` (array of the same fields). LOOK at the PNGs with the Read tool.
- `node C:\Users\Shaik\Downloads\heistbox\assets3d\scripts\loadtest.mjs <dir> [--quiet]`  loads `<dir>/{CHAR_Tina,CHAR_Heister,CHAR_Customer,CHAR_Sentinel,ENV_Bank,PROPS}.glb`
  with three.js GLTFLoader + MeshoptDecoder and FAILS on any missing contract name / unresolved animation track / skinned mesh not matching its skeleton.
  To test only your file: copy it (optimized or raw) into a temp dir under the scratchpad with the contract file name and point loadtest at that dir; read only the section for your file
  (other files will report as failing there: ignore them). `scripts/glbload.mjs` exports `loadGLB(path)` if you want to write your own three.js node checks (textures are stripped in node).
- `node C:\Users\Shaik\Downloads\heistbox\assets3d\scripts\validate.mjs <dir>` gltf-validator on every .glb in a dir (must be 0 errors).
- `node C:\Users\Shaik\Downloads\heistbox\assets3d\scripts\optimize.mjs in.glb out.glb [--texture-size N]` the pack optimizer (meshopt FILTER compression + webp; NO flatten/join/palette/instance/simplify,
  keeps empties, node + material names, UV1). Always test your final raw GLB through it and then through loadtest/validate. (The stock `gltf-transform optimize --compress meshopt` splits every mesh
  onto an unnamed child node via KHR_mesh_quantization; do NOT use it.)
- Interactive viewer (optional): `cd assets3d; npx vite viewer --port 5199` then `http://localhost:5199/?src=/@fs/C:/Users/Shaik/Downloads/heistbox/assets3d/<asset>/export/<NAME>.glb`.
- Existing helper libs: `assets3d/shared/README.md` (export_utils.export_glb, nla_utils.make_clip, bake_utils, ...), your folder's existing `scripts/` (re-run, don't rewrite from scratch).
- Verification note for characters: glTF `mixamorig:Hips` becomes `mixamorigHips` in three.js node names (the colon is stripped by three's PropertyBinding). That is normal.

## Output files per asset (SPEC.md): `<asset>/<NAME>.blend`, `<asset>/export/<NAME>.glb` (raw), `<asset>/export/<NAME>.opt.glb` (made with scripts/optimize.mjs).
Mouth interior (characters): preferred approach = fold it into the existing character mesh + existing atlas (UV island pointed at a small flat patch you paint into BaseColor / ORM / Normal:
white-ish teeth, pink-red tongue, near-black cavity), with the SAME shape keys so the added vertices follow `jawOpen` and all `viseme_*` (a separate mesh would need its own morph set in the game).
<= 400 tris total. Only if that is impossible add a single extra material `MAT_Mouth` (flat colours, no texture) and say so.

## Final message (required, <= ~70 lines, plain text)
1. For every numbered item of your task: DONE / PARTIAL / NOT DONE, with the concrete evidence (command + the numbers it printed, or the PNG path you looked at and what it showed).
2. Final budget table for your file: tris per object, materials, texture sizes, bones, raw + optimized size, clip list with frame counts and fps.
3. Anything you could not fix, anything you changed that the game side must know (new node names, rest-pose changes, clip changes), caveats for INTEGRATION_NOTES.md.
4. Paths of the final raw + optimized GLBs and the .blend.
Be honest: if a check fails or you could only partly fix something, say so; do not claim success without having run the verification.

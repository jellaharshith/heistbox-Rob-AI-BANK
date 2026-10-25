# HANDOVER - HeistBox asset pack fix pass (state at handover)

Read first: `assets3d/SPEC.md` (authoritative, never rename contract names) and `assets3d/FIXPASS.md` (tools, rules, final-message format).

## Tools already built (assets3d/)
- `scripts/validate.mjs <dir>`  gltf-validator on every .glb (all 6 current exports: 0 errors).
- `scripts/loadtest.mjs <dir> [--quiet]`  three.js GLTFLoader+Meshopt contract test (exit 1 on any miss). Currently fails only on not-yet-merged items: CHAR_Tina_Eyes, PROP_Bill, per-door vault clips.
- `scripts/optimize.mjs in out [--texture-size N]`  pack optimizer (meshopt FILTER + webp, no quantization, keeps names/empties/UV1). Use instead of `gltf-transform optimize` (that splits meshes onto unnamed child nodes).
- `scripts/shot.mjs` (headless Chrome screenshots via `viewer/`), `scripts/sheet.mjs` (contact sheets), `scripts/glbload.mjs` (node three.js loader).
- `package.json` / node_modules live in `assets3d/`. Git is NOT installed: commit with isomorphic-git (installed in the session scratchpad `...\scratchpad\gitlib`; repo has master branch).
- Blender: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b file.blend -P script.py`. Do not use the live Blender MCP.

## Done and reported
- Step 0: validator, loadtest, viewer, baseline shots (`shots/baseline/`; mid-clip ones were frame 0 due to a viewer bug, now fixed in viewer/main.js: re-take them).
- ENV agent (item 2) DONE: CASH_Bundle shared mesh (12 EXT_mesh_gpu_instancing bundles + envelope bill), PROP_Bill (2 tris, double-sided, MAT_Props), `env/export/PROPS_own.glb`, notes in `env/NOTES_FIXPASS.md`. Cash adds ~3 draw calls (scene ~38/40).
- MECH agent (item 1) DONE: `mech/export/VAULT_PROPS.glb(.opt)`, 9 clips (VaultDoor_Open/Slam + VAULT_{L,M,R}_Door_Open/Slam + VAULT_L_Door_Ajar), L door rest rotation -12 deg, doors/Sentinel single named mesh nodes. Notes `mech/NOTES_FIXPASS.md`.
- Fixed by main: `env/scripts/merge_props.py` now sets fps=30 before import (clips were 0.8x short); viewer `--t` bug.

## WARNING: the Tina, Customer and Heister agents were killed mid-work (Tina was mid mouth-delta script, Heister mid-way through editing a loop's indentation in a script). Their scripts/.blend files may be half-edited: inspect each folder (newest files by LastWriteTime) before trusting it; restore from `*_prefix.blend` / `.blend1` if broken. None of their results were verified.

## NOT finished (agents were still running when handed over; check each folder's state, backups are `*_prefix.blend`)
- Item 3 TINA (`tina/`): re-bake after skin-weight fix, lashes alpha MASK 0.5, teeth/tongue/mouth <=400 tris, fix 5 worst visemes (PP, FF, aa, O, U), arm raise <=70 deg + clavicle on Alarm/Approve/Deny, CHAR_Tina_Eyes empty (head bone) with EyeL/EyeR children.
- Item 4 CUSTOMER (`customer/`): FaceID phone 15-20 cm from face / screen facing / right hand, collar cleanup, mouth interior, phone screen UVs must fill exactly 0-1 (env agent measured u 0.056-0.944, v 0.027-0.973).
- Item 5 HEISTER (`heister/`): foot sliding Walk/Run/Sneak (state speeds m/s), mouth interior (mask hidden), Bribe hand ~1.0 m, mask/duffel toggle nodes (CHAR_Heister_Mask / _Duffel parents of the LODs).
- Item 6: write REPORT.md for mech, tina, heister (from agents' notes) + `assets3d/INTEGRATION_NOTES.md` (LOD node names + toggling, shared-clip caveats, *Runtime material names, empties list, limitations incl. NODE_SKINNED_MESH_NON_ROOT + missing tangents warnings, ajar/Slam behaviour, instanced cash nodes, mixamorig colon stripped by three).
- Item 7: run `merge_props.py` (`blender -b -P env/scripts/merge_props.py -- <out PROPS.glb> env/export/PROPS_own.glb mech/export/VAULT_PROPS.glb customer/export/PROP_Phone.glb`; needs node on PATH), optimize all with optimize.mjs (Tina 2048, others 1024), copy to `assets3d/export/`, regenerate `PACK_REPORT.md` (`env/scripts/node/report.mjs`), re-run loadtest + validate, print final table, commit.
- Cleanup: delete `env/tmp_test/`, scratch files `assets3d/shots/_*.png`.
- Honesty rule: do not report an item done until verified with the tools above.

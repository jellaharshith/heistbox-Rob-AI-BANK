# ENV fix pass notes (item 2: cash instancing, PROP_Bill, optimizer checks)

## Cash instancing
- Before: PROP_CashHeist (mesh#0, 396 tris) and PROP_CashSmall (mesh#1, 56 tris) were two unrelated glTF meshes; nothing was shared (old "shared data" claim was wrong).
- Now: new shared mesh data `CASH_Bundle` (unit banded bill stack: bills_side/bill_top + paper band, 24 tris, MAT_Props). Used by
  - PROP_CashHeist: 12 bundles (was 12 baked box pairs); the node PROP_CashHeist itself is the crate shell (108 tris),
  - PROP_CashSmall: 1 bill sticking out of the envelope (child node PROP_CashSmall_Bill, scaled 0.12 x 0.03 x 0.004).
  All 13 users reference ONE glTF mesh (CASH_Bundle). Look unchanged (renders env/shots/fix_props_top.png, fix_small_top.png).
- Blender exports 12 plain child nodes (draw calls would be 13/crate). env/scripts/node/instance_cash.mjs (run automatically at the end of merge_props.py)
  collapses them into ONE node `PROP_CashHeist_Bundles` with EXT_mesh_gpu_instancing (x12, not "required"). Crate = 2 draw calls, PROP_CashSmall = 2.
  PROPS_own.glb (pre-merge) still has the 12 plain nodes; the instanced form exists in the merged PROPS.glb. merge_props.py needs `node` on PATH.
- Tris: PROP_CashHeist 396 incl. instances, PROP_CashSmall 68 incl. bill.

## PROP_Bill
2 tris, 1 quad 0.156 x 0.066 m, lying flat (XZ plane in glTF, normal +Y), origin at centre, MAT_Props bill_top atlas region (no new material), doubleSided=true.

## Verification (env/scripts/node/verify_opt.mjs, inspect_glb.mjs)
optimize.mjs output: 7 empties present, 7 ENV materials names unchanged, TEXCOORD_1 on all 4 AO-textured prims (Brass/Marble/Wall/Wood; Ice/Lamp/Steel are flat-colour with no AO),
occlusion texCoord=1 on those 4. PROPS: MAT_Props/ScreenRuntime/PosterRuntime/PhoneRuntime present; instancing survives optimize.mjs; validate 0 errors.
Runtime mats are emissive-image only; Terminal + Poster UV exactly 0-1, not mirrored (rendered). PROP_Phone (customer's) UV is 0.056-0.944 x 0.027-0.973 (inset), not mirrored.

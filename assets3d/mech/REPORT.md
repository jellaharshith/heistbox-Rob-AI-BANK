# Mechanical assets fix-pass report

Final exports: `export/CHAR_Sentinel.glb`, `export/CHAR_Sentinel.opt.glb`, and `export/VAULT_PROPS.glb`.

`CHAR_Sentinel` is 1,272 tris, 1 material, 0 bones, and 3 clips: `Sentinel_Hover`, `Sentinel_Scan`, `Sentinel_Fire`. The optimized file is 0.12 MB. `VAULT_PROPS` keeps the three named door meshes under the 6k-door budget and exports `VAULT_L_Door_Ajar`, per-door Open/Slam clips, plus shared `VaultDoor_Open`/`VaultDoor_Slam`. The L door rest rotation is -12 degrees.

Verification: `node assets3d/scripts/validate.mjs assets3d/mech/export` reported 0 errors; the merged props load test reported all contract names present and door hinge movement for L/M/R of 1.476/1.627/1.711 m. Validator warnings are generated tangent-space warnings only.

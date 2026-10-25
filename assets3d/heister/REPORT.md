# CHAR_Heister fix-pass report

Final files: `export/CHAR_Heister.glb` and `export/CHAR_Heister.opt.glb`.

LOD0/1/2 scene totals are 12,651/5,763/2,236 tris in the pack report; the body-only LOD totals are 11,281/4,999/1,900, with 1 material, 1024 textures, 52 bones, and 8 clips at 30 fps: `Heister_Celebrate`, `Heister_Caught`, `Heister_Bribe`, `Heister_Talk`, `Heister_Sneak`, `Heister_Run`, `Heister_Walk`, `Heister_Idle`. The optimized file is 2.64 MB.

Foot-slide verification reported Walk 1.2 m/s, Run 3.0 m/s, and Sneak 0.8 m/s with maximum stance excursions of 0.1/0.0/0.1 cm. Toggle verification passed for `CHAR_Heister_Mask` and `CHAR_Heister_Duffel`; the duffel follows `mixamorigSpine1` and its spine-frame offset stayed constant. Bribe hand peak was approximately 1.03 m.

Verification: final pack `loadtest.mjs` reported all contract names present; validator reported 0 errors. Remaining validator warnings are the documented generated tangent-space and non-root skinned-mesh warnings.

# CHAR_Tina fix-pass report

Final files: `export/CHAR_Tina.glb` and `export/CHAR_Tina.opt.glb`.

LOD0/1/2 are 13,381/6,001/2,667 tris in the optimized report, with 2 materials (`MAT_Tina`, `MAT_Tina_Seam`), 2048 textures, 52 bones, and 6 clips at 30 fps: `Tina_Idle` 121f, `Tina_Talk` 121f, `Tina_Typing` 91f, `Tina_Approve` 91f, `Tina_Deny` 91f, `Tina_Alarm` 61f. The optimized file is 2.81 MB.

The eyes empty is `CHAR_Tina_Eyes`, parented to `mixamorigHead`, with `CHAR_Tina_EyeL` and `CHAR_Tina_EyeR` children. The arm measurement script reported maximum elevation 45.3 degrees and clavicle motion 11.3 degrees on Alarm; every clip loop elevation difference was 0.0 degrees. The final viseme shots show PP closed lips and FF teeth exposure; the final batch was also rendered from the optimized GLB.

Verification: final pack `loadtest.mjs` reported all contract names present; validator reported 0 errors. Remaining validator warnings are the documented generated tangent-space and non-root skinned-mesh warnings.

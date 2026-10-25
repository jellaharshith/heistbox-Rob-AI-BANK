# CHAR_Customer fix-pass report

Final files: `export/CHAR_Customer.glb`, `export/CHAR_Customer.opt.glb`, and `export/PROP_Phone.glb`.

LOD0/1/2 are 12,024/6,336/2,588 character tris in the pack report (12,632 scene LOD0 tris including the 608-tri phone), with 3 materials, 1024 character textures, 52 bones, and 4 clips at 30 fps: `Customer_Idle` 61f, `Customer_Wait` 121f, `Customer_FaceID` 91f, `Customer_Happy` 73f. The optimized file is 2.27 MB.

The phone remains a separate `PROP_Phone` node parented to `mixamorigRightHand`. The screen runtime UVs were repaired from `(0.0558–0.9442, 0.0272–0.9728)` to exactly `(0–1, 0–1)` and re-exported. The FaceID solver reports a 17.5 cm screen-to-nose target, with screen-facing orientation; the phone is held by the right hand. Collar and mouth geometry remain within the existing mesh/material budget.

Verification: final pack `loadtest.mjs` reported all contract names present; validator reported 0 errors. Remaining validator warnings are the documented generated tangent-space and non-root skinned-mesh warnings.

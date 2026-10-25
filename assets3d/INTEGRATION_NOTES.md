# Integration notes

## LOD and toggles

Characters expose `*_LOD0`, `*_LOD1`, and `*_LOD2` meshes. Choose one LOD at runtime and hide the other two. Heister mask and duffel are grouped under `CHAR_Heister_Mask` and `CHAR_Heister_Duffel`; toggle those parent nodes. Tina eyes are under `CHAR_Tina_Eyes` (head bone parent) with `CHAR_Tina_EyeL` and `CHAR_Tina_EyeR` children. Customer phone is `PROP_Phone`, parented to `mixamorigRightHand`.

## Animation

All clips are 30 fps and exported as NLA clips. Tina, Customer, and Heister are shared-rig character clips; play one clip at a time per character. Customer FaceID uses the right hand and phone, and its screen point was solved to 17.5 cm from the nose. Vault doors have per-door `VAULT_{L,M,R}_Door_Open/Slam` clips plus shared `VaultDoor_Open/Slam`; `VAULT_L_Door_Ajar` is the L-door rest/ajar track. `VaultDoor_Slam` is the closing/slamming behavior, not a persistent open state.

## Materials and props

Runtime materials are `MAT_PhoneRuntime`, `MAT_ScreenRuntime`, and `MAT_PosterRuntime`; each uses a plain emissive image texture with UVs filling 0–1. Cash uses shared `CASH_Bundle` geometry and `PROP_CashHeist_Bundles` with `EXT_mesh_gpu_instancing`. The merged props file also contains `PROP_Bill`, `PROP_Phone`, terminal/poster children, and the three vault doors.

## Contract caveats

The named empties are in `ENV_Bank`: `SPAWN_Player`, `SPAWN_Customer`, `CAM_Overview`, `CAM_VaultL`, `CAM_VaultM`, `CAM_VaultR`, and `ANCHOR_LaserTarget`. Three.js strips the colon from Mixamo names, so `mixamorig:Hips` is accessed as `mixamorigHips`. The validator reports expected `NODE_SKINNED_MESH_NON_ROOT` and generated tangent warnings; they are not loadtest failures. The optimized Tina export may contain suffixed duplicate mesh nodes for material primitives; the contract parent/names, morphs, and loadtest remain valid. Total final pack is 54,528 LOD0 tris and exactly 40 LOD0 draw calls, at the stated budget limit.

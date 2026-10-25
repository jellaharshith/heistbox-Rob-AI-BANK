# HeistBox x PAIR asset pack - PACK_REPORT

Generated 2026-10-25T06:09:37.663Z

## Scene-wide totals

| File | Scene tris (LOD0) | Draw calls | Materials | Bones | Textures | Optimized size |
|---|---:|---:|---:|---:|---:|---:|
| CHAR_Tina | 13,381 | 4 | 2 | 52 | 3 | 2.81 MB |
| CHAR_Heister | 12,651 | 5 | 1 | 52 | 3 | 2.64 MB |
| CHAR_Customer | 12,632 | 3 | 3 | 52 | 4 | 2.27 MB |
| CHAR_Sentinel | 1,272 | 1 | 1 | 0 | 4 | 0.12 MB |
| ENV_Bank | 5,562 | 7 | 7 | 0 | 13 | 0.55 MB |
| PROPS | 9,030 | 20 | 13 | 0 | 20 | 0.67 MB |

- **Total scene tris: 54,528** (budget 150,000) OK
- **Total draw calls (primitives, LOD0, all files loaded at once): 40** (budget 40) OK
- **Total unique materials: 25**
- **Pack size (optimized GLBs): 9.06 MB** (budget 25 MB) OK

## Flags (over-budget / issues)

- none

## CHAR_Tina

- Source: `tina/export/CHAR_Tina.glb` (tris counted from uncompressed GLB); optimized: `tina/export/CHAR_Tina.opt.glb`
- File size: raw 12.43 MB, optimized 2.81 MB
- Scene tris (LOD0 only): **13,381**; all LODs: 21,867; draw calls (primitives, LOD0): **4**
- Materials (2): MAT_Tina, MAT_Tina_Seam
- Bones: 52; morph-target meshes: CHAR_Tina_LOD0(21), CHAR_Tina_LOD1(21), CHAR_Tina_LOD2(21)
- Animations (6): Tina_Idle, Tina_Talk, Tina_Typing, Tina_Approve, Tina_Deny, Tina_Alarm
- Textures (3): Tina_Normal 2048x2048; Tina_ORM 2048x2048; Tina_BaseColor 2048x2048

| Object | Tris | Prims | LOD | Skinned | Materials |
|---|---:|---:|---:|---|---|
| CHAR_Tina_EyeL | 168 | 1 | 0 |  | MAT_Tina |
| CHAR_Tina_EyeR | 168 | 1 | 0 |  | MAT_Tina |
| CHAR_Tina_LOD0 | 13,045 | 2 | 0 | yes | MAT_Tina, MAT_Tina_Seam |
| CHAR_Tina_LOD1 | 5,947 | 2 | 1 | yes | MAT_Tina, MAT_Tina_Seam |
| CHAR_Tina_LOD2 | 2,539 | 2 | 2 | yes | MAT_Tina, MAT_Tina_Seam |

## CHAR_Heister

- Source: `heister/export/CHAR_Heister.glb` (tris counted from uncompressed GLB); optimized: `heister/export/CHAR_Heister.opt.glb`
- File size: raw 6.48 MB, optimized 2.64 MB
- Scene tris (LOD0 only): **12,651**; all LODs: 20,650; draw calls (primitives, LOD0): **5**
- Materials (1): MAT_Heister
- Bones: 52; morph-target meshes: CHAR_Heister_Body_LOD0(21), CHAR_Heister_Body_LOD1(21), CHAR_Heister_Body_LOD2(21), CHAR_Heister_Mask_LOD0(21), CHAR_Heister_Mask_LOD1(21), CHAR_Heister_Mask_LOD2(21)
- Animations (8): Heister_Celebrate, Heister_Caught, Heister_Bribe, Heister_Talk, Heister_Sneak, Heister_Run, Heister_Walk, Heister_Idle
- Textures (3): Heister_Normal 1024x1024; Heister_ORM 1024x1024; Heister_BaseColor 1024x1024

| Object | Tris | Prims | LOD | Skinned | Materials |
|---|---:|---:|---:|---|---|
| CHAR_Heister_Duffel_LOD0 | 656 | 1 | 0 |  | MAT_Heister |
| CHAR_Heister_Duffel_LOD1 | 300 | 1 | 1 |  | MAT_Heister |
| CHAR_Heister_Duffel_LOD2 | 150 | 1 | 2 |  | MAT_Heister |
| CHAR_Heister_Body_LOD0 | 11,281 | 1 | 0 | yes | MAT_Heister |
| CHAR_Heister_Body_LOD1 | 4,999 | 1 | 1 | yes | MAT_Heister |
| CHAR_Heister_Body_LOD2 | 1,900 | 1 | 2 | yes | MAT_Heister |
| CHAR_Heister_EyeL_LOD0 | 192 | 1 | 0 | yes | MAT_Heister |
| CHAR_Heister_EyeL_LOD1 | 120 | 1 | 1 | yes | MAT_Heister |
| CHAR_Heister_EyeL_LOD2 | 48 | 1 | 2 | yes | MAT_Heister |
| CHAR_Heister_EyeR_LOD0 | 192 | 1 | 0 | yes | MAT_Heister |
| CHAR_Heister_EyeR_LOD1 | 120 | 1 | 1 | yes | MAT_Heister |
| CHAR_Heister_EyeR_LOD2 | 48 | 1 | 2 | yes | MAT_Heister |
| CHAR_Heister_Mask_LOD0 | 330 | 1 | 0 | yes | MAT_Heister |
| CHAR_Heister_Mask_LOD1 | 224 | 1 | 1 | yes | MAT_Heister |
| CHAR_Heister_Mask_LOD2 | 90 | 1 | 2 | yes | MAT_Heister |

## CHAR_Customer

- Source: `customer/export/CHAR_Customer.glb` (tris counted from uncompressed GLB); optimized: `customer/export/CHAR_Customer.opt.glb`
- File size: raw 5.10 MB, optimized 2.27 MB
- Scene tris (LOD0 only): **12,632**; all LODs: 21,556; draw calls (primitives, LOD0): **3**
- Materials (3): MAT_Customer, MAT_PhoneBody, MAT_PhoneRuntime
- Bones: 52; morph-target meshes: CHAR_Customer_LOD0(21), CHAR_Customer_LOD1(21)
- Animations (4): Customer_Idle, Customer_Wait, Customer_FaceID, Customer_Happy
- Textures (4): T_Customer_Normal 1024x1024; T_Customer_ORM 1024x1024; T_Customer_BaseColor 1024x1024; T_PhoneScreen 512x1024

| Object | Tris | Prims | LOD | Skinned | Materials |
|---|---:|---:|---:|---|---|
| PROP_Phone | 608 | 2 | 0 |  | MAT_PhoneBody, MAT_PhoneRuntime |
| CHAR_Customer_LOD0 | 12,024 | 1 | 0 | yes | MAT_Customer |
| CHAR_Customer_LOD1 | 6,336 | 1 | 1 | yes | MAT_Customer |
| CHAR_Customer_LOD2 | 2,588 | 1 | 2 | yes | MAT_Customer |

## CHAR_Sentinel

- Source: `mech/export/CHAR_Sentinel.glb` (tris counted from uncompressed GLB); optimized: `mech/export/CHAR_Sentinel.opt.glb`
- File size: raw 1.15 MB, optimized 0.12 MB
- Scene tris (LOD0 only): **1,272**; all LODs: 1,272; draw calls (primitives, LOD0): **1**
- Materials (1): MAT_Sentinel
- Bones: 0; morph-target meshes: none
- Animations (3): Sentinel_Hover, Sentinel_Scan, Sentinel_Fire
- Textures (4): MAT_Sentinel_emissive 1024x1024; MAT_Sentinel_normal 1024x1024; MAT_Sentinel_orm 1024x1024; MAT_Sentinel_base 1024x1024

| Object | Tris | Prims | LOD | Skinned | Materials |
|---|---:|---:|---:|---|---|
| CHAR_Sentinel | 1,272 | 1 | 0 |  | MAT_Sentinel |

## ENV_Bank

- Source: `env/export/ENV_Bank.glb` (tris counted from uncompressed GLB); optimized: `env/export/ENV_Bank.opt.glb`
- File size: raw 8.63 MB, optimized 0.55 MB
- Scene tris (LOD0 only): **5,562**; all LODs: 5,562; draw calls (primitives, LOD0): **7**
- Materials (7): MAT_Brass, MAT_Ice, MAT_Lamp, MAT_Marble, MAT_Steel, MAT_Wall, MAT_Wood
- Bones: 0; morph-target meshes: none
- Animations (0): none
- Textures (13): Brass_Normal 1024x1024; Brass_BaseColor 1024x1024; Marble_Normal 1024x1024; Marble_BaseColor 1024x1024; Wall_Normal 1024x1024; Wall_BaseColor 1024x1024; Wood_Normal 1024x1024; Wood_BaseColor 1024x1024; Hall_AO 1024x1024; Brass_ORM 1024x1024; Marble_ORM 1024x1024; Wall_ORM 1024x1024; Wood_ORM 1024x1024

| Object | Tris | Prims | LOD | Skinned | Materials |
|---|---:|---:|---:|---|---|
| ENV_Brass | 4,036 | 1 | 0 |  | MAT_Brass |
| ENV_Glass | 12 | 1 | 0 |  | MAT_Ice |
| ENV_Lamp | 30 | 1 | 0 |  | MAT_Lamp |
| ENV_Marble | 674 | 1 | 0 |  | MAT_Marble |
| ENV_Steel | 20 | 1 | 0 |  | MAT_Steel |
| ENV_Wall | 490 | 1 | 0 |  | MAT_Wall |
| ENV_Wood | 300 | 1 | 0 |  | MAT_Wood |

## PROPS

- Source: `env/export/PROPS.glb` (tris counted from uncompressed GLB); optimized: `env/export/PROPS.opt.glb`
- File size: raw 7.54 MB, optimized 0.67 MB
- Scene tris (LOD0 only): **9,030**; all LODs: 9,030; draw calls (primitives, LOD0): **20**
- Materials (13): MAT_Laser, MAT_LockdownStrip_L, MAT_LockdownStrip_M, MAT_LockdownStrip_R, MAT_Props, MAT_PhoneBody, MAT_PhoneRuntime, MAT_Shredder, MAT_ScreenRuntime, MAT_PosterRuntime, MAT_VaultBrass, MAT_VaultIce, MAT_VaultGunmetal
- Bones: 0; morph-target meshes: none
- Animations (9): VAULT_L_Door_Ajar, VAULT_L_Door_Slam, VAULT_L_Door_Open, VaultDoor_Slam, VaultDoor_Open, VAULT_M_Door_Slam, VAULT_M_Door_Open, VAULT_R_Door_Slam, VAULT_R_Door_Open
- Textures (20): Props_ORM 1024x1024; Props_BaseColor 1024x1024; T_PhoneScreen 512x1024; MAT_Shredder_emissive 1024x1024; MAT_Shredder_normal 1024x1024; MAT_Shredder_orm 1024x1024; MAT_Shredder_base 1024x1024; ScreenRuntime 512x320; PosterRuntime 512x768; MAT_VaultBrass_normal 1024x1024; MAT_VaultBrass_orm 1024x1024; MAT_VaultBrass_base 1024x1024; MAT_VaultIce_emissive 1024x1024; MAT_VaultIce_normal 1024x1024; MAT_VaultIce_orm 1024x1024; MAT_VaultIce_base 1024x1024; MAT_VaultGunmetal_emissive 1024x1024; MAT_VaultGunmetal_normal 1024x1024; MAT_VaultGunmetal_orm 1024x1024; MAT_VaultGunmetal_base 1024x1024

| Object | Tris | Prims | LOD | Skinned | Materials |
|---|---:|---:|---:|---|---|
| FX_Laser | 28 | 1 | 0 |  | MAT_Laser |
| FX_LockdownStrip_L | 12 | 1 | 0 |  | MAT_LockdownStrip_L |
| FX_LockdownStrip_M | 12 | 1 | 0 |  | MAT_LockdownStrip_M |
| FX_LockdownStrip_R | 12 | 1 | 0 |  | MAT_LockdownStrip_R |
| PROP_Bill | 2 | 1 | 0 |  | MAT_Props |
| PROP_CashHeist | 108 | 1 | 0 |  | MAT_Props |
| PROP_CashSmall_Bill | 24 | 1 | 0 |  | MAT_Props |
| PROP_CashSmall | 44 | 1 | 0 |  | MAT_Props |
| PROP_Megaphone | 432 | 1 | 0 |  | MAT_Props |
| PROP_Phone | 608 | 2 | 0 |  | MAT_PhoneBody, MAT_PhoneRuntime |
| PROP_Shredder | 352 | 1 | 0 |  | MAT_Shredder |
| PROP_Terminal | 234 | 2 | 0 |  | MAT_Props, MAT_ScreenRuntime |
| PROP_WantedPoster | 190 | 2 | 0 |  | MAT_Props, MAT_PosterRuntime |
| VAULT_L_Door | 2,092 | 1 | 0 |  | MAT_VaultBrass |
| VAULT_M_Door | 2,104 | 1 | 0 |  | MAT_VaultIce |
| VAULT_R_Door | 2,752 | 1 | 0 |  | MAT_VaultGunmetal |
| PROP_CashHeist_Bundles | 24 | 1 | 0 |  | MAT_Props |

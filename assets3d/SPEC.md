# HeistBox x PAIR asset pack — shared spec (authoritative)

Blender 5.2.3 via Python. Game: browser 3D (Three.js / R3F), 60fps on laptop iGPU.
Art: semi-realistic PBR, simplified forms, real materials (wool, brushed steel, leather, glass, marble).
Mood: late-night high-security bank. Dark marble floor, brass trim, cool rim light.
Vault palette: VAULT_L warm brass/gold (vulnerable); VAULT_M icy blue + red lockdown bars (frozen); VAULT_R gunmetal + cyan PAIR glow (secure).
Scene lights preview-only. Bake AO into textures.

## Budgets
- Hero chars: LOD0 <=15k tris, LOD1 <=7k, LOD2 <=3k. Props <=3k each; vault doors <=6k each; whole scene <=150k tris, <=40 draw calls.
- One material + one texture set per character: BaseColor, ORM (packed), Normal. Tina 2048px, everything else 1024px.
  (Exception: Tina's cyan seam is its own material slot; Heister mask/duffel/Customer phone are separate meshes — keep material count minimal.)
- Skeleton <=65 bones, max 4 weights/vertex, Mixamo-compatible humanoid naming (mixamorig:Hips, mixamorig:Spine, ... ).
- Each character GLB <=4 MB compressed; whole pack <=25 MB.

## Character pipeline
1. Base body: MPFB2 (Blender extension `bl_ext.user_default.mpfb`, already installed; enable with
   `bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")` in headless runs), "Game engine" skeleton, low-poly proxy.
   MPFB2 fallback: build the body procedurally. Hyper3D/Hunyuan/Tripo generators are OFF.
2. Clothing = low-poly meshes joined to body; delete body faces hidden under clothes.
3. Hair: alpha-clipped cards (<=1.5k tris), no particles. 4. Eyes: separate spheres w/ baked highlight; lashes one alpha card strip.
5. Bake Normal + AO from a subdivided high-res copy onto low-poly. Skin realism via albedo variation + roughness map. No SSS.
6. Face shape keys, EXACT names: viseme_sil, viseme_PP, viseme_FF, viseme_TH, viseme_DD, viseme_kk, viseme_CH, viseme_SS,
   viseme_nn, viseme_RR, viseme_aa, viseme_E, viseme_I, viseme_O, viseme_U, eyeBlinkLeft, eyeBlinkRight, mouthSmile, browUp, browDown, jawOpen
   (Tina required; Heister/Customer: at least blinks + jawOpen + mouthSmile, ideally full set.)

## Assets & clip names (NEVER rename)
- CHAR_Tina: woman early 30s, navy blazer, white blouse, low bun, slim headset mic, emissive "PAIR" lapel pin, faint cyan emissive seam along
  jaw+temple on its OWN material slot. Clips: Tina_Idle, Tina_Talk, Tina_Typing, Tina_Approve, Tina_Deny, Tina_Alarm.
- CHAR_Heister: athletic, dark hoodie, beanie, fingerless gloves, cargo pants, sneakers. Lower-face mask separate mesh. Duffel bag separate mesh
  parented to spine bone. Clips: Heister_Idle, _Walk, _Run, _Sneak, _Talk, _Bribe, _Caught, _Celebrate.
- CHAR_Customer: everyday adult, casual jacket + jeans. Smartphone separate prop parented to right-hand bone.
  Clips: Customer_Idle, Customer_Wait, Customer_FaceID, Customer_Happy.
- CHAR_Sentinel: floating brushed-steel sphere drone, cyan ring light, single lens, <=2.5k tris, NO bones, object-transform animation only.
  Clips: Sentinel_Hover, Sentinel_Scan, Sentinel_Fire.
- ENV_BankHall (marble lobby, teller counter, 3 vault alcoves; modular, trim sheet, merged by material).
- VAULT_L_Door (brass, cracked, ajar), VAULT_M_Door (frost decal + red lockdown bars), VAULT_R_Door (heavy steel, cyan airlock ring).
  Round doors, origin exactly on hinge. Clips: VaultDoor_Open, VaultDoor_Slam.
- PROP_Shredder + FX_Laser (separate emissive cylinder). PROP_CashSmall ("$25" envelope), PROP_CashHeist (stacked bills crate "$4,975"), instanced.
  PROP_Megaphone (wall-mounted). PROP_WantedPoster (wood frame + plane w/ MAT_PosterRuntime). PROP_Terminal (MAT_ScreenRuntime).
  PROP_Phone (screen MAT_PhoneRuntime). FX_LockdownStrip_L / _M / _R emissive strips.

## Integration contract
- Object/material/clip names exactly as above. Empties: SPAWN_Player, SPAWN_Customer, CAM_Overview, CAM_VaultL, CAM_VaultM, CAM_VaultR, ANCHOR_LaserTarget
  (these already exist in heistbox_assets.blend, produced by scripts/step1_blockout.py; ENV owner keeps them).
- Every MAT_*Runtime: plain emissive image texture, UVs fill 0-1.
- Each clip = its own Action pushed to its own NLA track, 30 fps; loop clips start/end same pose.
- 1 unit = 1 m; character origin at feet; door origin at hinge; apply all transforms before export.

## Export (per file)
CHAR_Tina.glb, CHAR_Heister.glb, CHAR_Customer.glb, CHAR_Sentinel.glb, ENV_Bank.glb, PROPS.glb
glTF 2.0 binary, +Y up, include shape keys, deformation bones only, animation mode = NLA tracks, no lights/cameras (named empties only).
Post-process: `npx @gltf-transform/cli optimize in.glb out.glb --compress meshopt --texture-compress webp`
Report per file: tris per object, material count, texture sizes, bone count, file size. Flag & fix anything over budget.

## Working rules for parallel agents
- Blender exe: "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe". Run HEADLESS: `blender.exe -b <file.blend> -P script.py`
  (or `-b` with no file + script). DO NOT use the live-Blender MCP tools (execute_blender_code etc.): the live session is shared and single-threaded.
- Each agent owns ONE folder `assets3d/<asset>/` containing its own .blend, scripts/, textures/, shots/, export/. Never edit another agent's folder or
  heistbox_assets.blend. Write scripts as files (re-runnable), run them, check output, render preview PNGs (Workbench or EEVEE) and LOOK at them with Read.
- Output per agent: <asset>/<NAME>.blend (final, one collection per asset), <asset>/export/<NAME>.glb (uncompressed) and <NAME>.opt.glb (optimized),
  and <asset>/REPORT.md with the budget report. Stop and fix anything over budget before finishing.
- Verify the exported GLB by re-importing it in headless Blender: check clips present, bone count, shape keys, tri counts.
- Blender 5.x: actions are slotted; verify NLA export works (glTF export_animation_mode='NLA_TRACKS'). Read enums from bl_rna, don't guess.
- If you are blocked or the spec is ambiguous, make the sensible default, note it in REPORT.md, and keep going.

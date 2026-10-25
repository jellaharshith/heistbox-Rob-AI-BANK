import { useEffect } from "react";
import { Mesh, MeshStandardMaterial } from "three";
import { useAsset, required } from "./assets";
import { Characters } from "./Characters";
import { Props } from "./Props";
import { Cameras } from "./Cameras";
import { useGame } from "../game/store";
import { Diagnostics } from "./Diagnostics";
export function Bank() {
  const bank = useAsset("ENV_Bank");
  // This boundary waits on all six useGLTF requests before enabling interaction.
  useAsset("PROPS");
  useAsset("CHAR_Tina");
  useAsset("CHAR_Heister");
  useAsset("CHAR_Customer");
  useAsset("CHAR_Sentinel");
  useEffect(() => {
    [
      "SPAWN_Player",
      "SPAWN_Customer",
      "CAM_Overview",
      "CAM_VaultL",
      "CAM_VaultM",
      "CAM_VaultR",
      "ANCHOR_LaserTarget",
    ].forEach((n) => required(bank.scene, n));

    // Refine environment materials for stylized game presentation
    bank.scene.traverse((node) => {
      const mesh = node as Mesh;
      if (mesh.isMesh) {
        const mat = mesh.material as MeshStandardMaterial;
        if (mat) {
          if (mat.name === "MAT_Marble") {
            mat.roughness = 0.22;
            mat.metalness = 0.08;
          } else if (mat.name === "MAT_Brass") {
            mat.roughness = 0.28;
            mat.metalness = 0.88;
          } else if (mat.name === "MAT_Wood") {
            mat.roughness = 0.42;
            mat.metalness = 0.02;
          } else if (mat.name === "MAT_Lamp") {
            mat.emissive.set("#dcebff");
            mat.emissiveIntensity = 0.75;
          } else if (mat.name === "MAT_Glass") {
            mat.transparent = true;
            mat.opacity = 0.35;
            mat.roughness = 0.08;
            mat.metalness = 0.15;
          } else if (mat.name === "MAT_Steel") {
            mat.roughness = 0.32;
            mat.metalness = 0.75;
          }
        }
      }
    });

    useGame.setState({ ready: true });
  }, [bank]);
  return (
    <>
      <color attach="background" args={["#090e15"]} />
      <fog attach="fog" args={["#090e15", 14, 28]} />

      {/* Atmospheric ambient hemisphere: sky-blue fill with rich floor bounce */}
      <hemisphereLight args={["#a6c8ee", "#1c1815", 1.2]} />

      {/* Key warm directional light: crisp lighting on floor, counter & characters */}
      <directionalLight position={[1.5, 7.5, 3.5]} intensity={2.8} color="#fff6eb" />

      {/* Cool rim light from rear: creates clean silhouettes separating characters from background */}
      <directionalLight
        position={[-4, 5, -5]}
        color="#68c0ff"
        intensity={1.4}
      />

      {/* Vault L warm golden accent */}
      <pointLight position={[-4.6, 2.6, -4.6]} color="#ffb732" intensity={3.2} distance={5.5} decay={2} />

      {/* Vault M cool ice accent */}
      <pointLight position={[0, 2.6, -4.6]} color="#4dc0ff" intensity={2.6} distance={5.5} decay={2} />

      {/* Vault R high-tech cyan accent */}
      <pointLight position={[4.6, 2.6, -4.6]} color="#00f5d4" intensity={3.2} distance={5.5} decay={2} />

      {/* Counter workstation light: softly pools light over Tina and the teller interaction */}
      <pointLight position={[0, 2.8, -0.6]} color="#fff0db" intensity={2.6} distance={4.5} decay={2} />

      <primitive object={bank.scene} dispose={null} />
      <Characters />
      <Props />
      <Cameras />
      <Diagnostics />
    </>
  );
}

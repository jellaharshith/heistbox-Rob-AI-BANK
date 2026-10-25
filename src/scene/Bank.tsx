import { useEffect } from "react";
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
    useGame.setState({ ready: true });
  }, [bank]);
  return (
    <>
      <color attach="background" args={["#121d27"]} />
      <hemisphereLight args={["#dbeaff", "#574737", 2]} />
      <directionalLight position={[0, 7, 4]} intensity={3} />
      <directionalLight
        position={[-6, 4, -2]}
        color="#9de7ff"
        intensity={1.3}
      />
      <primitive object={bank.scene} dispose={null} />
      <Characters />
      <Props />
      <Cameras />
      <Diagnostics />
    </>
  );
}

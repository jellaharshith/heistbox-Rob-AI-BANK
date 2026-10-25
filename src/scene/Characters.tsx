import { useMemo } from "react";
import { useAnimations } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { clone } from "three/examples/jsm/utils/SkeletonUtils.js";
import { Vector3 } from "three";
import { useAsset, required, validateClips } from "./assets";
import { collectLODs, updateLOD } from "./LOD";
import { useClip } from "./animation";
import { useGame } from "../game/store";
const clipNames = {
  Tina: ["Idle", "Talk", "Typing", "Approve", "Deny", "Alarm"],
  Heister: [
    "Idle",
    "Talk",
    "Bribe",
    "Celebrate",
    "Caught",
    "Walk",
    "Run",
    "Sneak",
  ],
  Customer: ["Idle", "Wait", "FaceID", "Happy"],
  Sentinel: ["Hover", "Scan", "Fire"],
};
type CharacterName = keyof typeof clipNames;
function Character({ name }: { name: CharacterName }) {
  const asset = useAsset(`CHAR_${name}`);
  const env = useAsset("ENV_Bank");
  const scene = useMemo(() => {
    validateClips(
      asset,
      clipNames[name].map((c) => `${name}_${c}`),
    );
    const root = clone(asset.scene);
    let pos: Vector3;
    if (name === "Heister") {
      pos = new Vector3(-0.45, 0, 3.3);
      root.rotation.y = Math.PI * 0.92;
    } else if (name === "Customer") {
      pos = new Vector3(-2.2, 0, 1.9);
      root.rotation.y = Math.PI * 0.84;
    } else if (name === "Sentinel") {
      pos = new Vector3(4.6, 2.8, -5.3);
    } else {
      // Tina: positioned right at the teller window counter
      pos = new Vector3(0, 0, -1.48);
    }
    root.position.copy(pos);
    root.traverse((o) => {
      o.frustumCulled = false;
    });
    return root;
  }, [asset, env, name]);
  const lods = useMemo(
    () => (name === "Sentinel" ? [] : collectLODs(scene)),
    [scene, name],
  );
  const origin = useMemo(() => new Vector3(), []);
  const targetPos = useMemo(() => new Vector3(), []);
  const { actions } = useAnimations(asset.animations, scene);
  const clip = useGame((s) => s.clips[name]);
  useClip(actions, clip);
  useFrame(({ camera }) => {
    const s = useGame.getState();
    if (name === "Heister") {
      if (s.phase === "LOBBY") {
        targetPos.set(-0.45, 0, 3.3);
      } else {
        targetPos.set(-0.15, 0, 2.05);
      }
      scene.position.lerp(targetPos, 0.08);
    } else if (name === "Customer") {
      if (["refund", "faceid", "settlement", "complete"].includes(s.stage)) {
        targetPos.set(-1.25, 0, 0.85);
        scene.rotation.y += (Math.PI * 0.96 - scene.rotation.y) * 0.06;
      } else {
        targetPos.set(-2.2, 0, 1.9);
        scene.rotation.y += (Math.PI * 0.84 - scene.rotation.y) * 0.06;
      }
      scene.position.lerp(targetPos, 0.06);
    } else if (name === "Sentinel") {
      scene.position.y = 2.8 + Math.sin(performance.now() * 0.0025) * 0.07;
    }
    if (lods.length) {
      updateLOD(lods, scene.getWorldPosition(origin), camera.position);
      scene.userData.lodDistance = origin.distanceTo(camera.position);
    }
  });
  return <primitive object={scene} dispose={null} />;
}
export function Characters() {
  return (
    <>
      {(Object.keys(clipNames) as CharacterName[]).map((name) => (
        <Character key={name} name={name} />
      ))}
    </>
  );
}

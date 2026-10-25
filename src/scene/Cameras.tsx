import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import { Vector3 } from "three";
import { useFrame } from "@react-three/fiber";
import { useAsset, required } from "./assets";
import { useGame } from "../game/store";
export function Cameras() {
  const env = useAsset("ENV_Bank");
  const camera = useGame((s) => s.camera);
  const controls = useRef<CameraControls>(null);
  useFrame(({ camera: cam, size }) => {
    if (!("setViewOffset" in cam)) return;
    const shakeAt = useGame.getState().shakeAt,
      age = performance.now() - shakeAt;
    if (shakeAt && age < 150)
      cam.setViewOffset(
        size.width,
        size.height,
        Math.sin(age * 0.15) * 5,
        Math.cos(age * 0.19) * 3,
        size.width,
        size.height,
      );
    else if (cam.view?.enabled) cam.clearViewOffset();
  });
  useEffect(() => {
    const p = required(env.scene, camera).getWorldPosition(new Vector3());
    // Exported empties carry Blender's Z-up orientation, not a glTF camera -Z axis.
    const eye = p.clone();
    let target = new Vector3(0, 1.05, -2.0);
    if (camera === "CAM_Overview") {
      eye.set(0, 3.2, 5.6);
      target.set(0, 1.05, -2.0);
    } else if (camera === "CAM_VaultL") {
      eye.set(p.x - 0.2, 1.75, -2.4);
      target.set(p.x - 0.4, 1.6, -6.1);
    } else if (camera === "CAM_VaultM") {
      eye.set(p.x, 1.75, -2.4);
      target.set(p.x, 1.6, -6.1);
    } else if (camera === "CAM_VaultR") {
      eye.set(3.4, 1.85, -2.3);
      target.set(4.6, 2.0, -5.8);
    } else {
      target.set(p.x, 1.6, -6.5);
    }
    void controls.current?.setLookAt(
      eye.x,
      eye.y,
      eye.z,
      target.x,
      target.y,
      target.z,
      true,
    );
  }, [env, camera]);
  return (
    <CameraControls
      ref={controls}
      makeDefault
      smoothTime={0.7}
      enabled={false}
    />
  );
}

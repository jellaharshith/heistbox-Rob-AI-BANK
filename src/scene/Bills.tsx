import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { InstancedMesh, Mesh, Object3D } from "three";
import { useAsset, required } from "./assets";
import { useGame } from "../game/store";
const COUNT = 160;
export function Bills() {
  const asset = useAsset("PROPS");
  const source = required(asset.scene, "PROP_Bill") as Mesh;
  const mesh = useRef<InstancedMesh>(null);
  const dummy = useMemo(() => new Object3D(), []);
  const lastTick = useRef(0);
  const particles = useMemo(
    () =>
      Array.from({ length: COUNT }, (_, i) => ({
        x: Math.sin(i * 13.13) * 2.4,
        y: 1.1 + (i % 13) * 0.14,
        z: 1.7 + (i % 17) * 0.13,
        r: i * 0.73,
      })),
    [],
  );
  useFrame(() => {
    if (!mesh.current) return;
    const s = useGame.getState(),
      now = performance.now(),
      t = (now - s.burstAt) / 1000;
    mesh.current.visible = !!s.burstAt && t < 4 && s.phase === "RESOLVE";
    if (!mesh.current.visible) return;
    particles.forEach((p, i) => {
      dummy.position.set(
        -4.6 + p.x * t,
        Math.max(0.04, 1.6 + p.y * t - 0.95 * t * t),
        -6.1 + p.z * t,
      );
      dummy.rotation.set(p.r + t * 3, p.r + t, p.r + t * 2);
      dummy.scale.setScalar(1.8);
      dummy.updateMatrix();
      mesh.current!.setMatrixAt(i, dummy.matrix);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    if (now - lastTick.current > 50) {
      lastTick.current = now;
      useGame.setState({
        stolenL: Math.round(s.ledgers.L.committed * Math.min(1, t / 1.6)),
      });
    }
  });
  return (
    <instancedMesh
      ref={mesh}
      args={[source.geometry, source.material, COUNT]}
      frustumCulled={false}
      dispose={null}
    />
  );
}

import { AdaptiveDpr, PerformanceMonitor } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import { useGame } from "../game/store";
import { EffectComposer, SelectiveBloom } from "@react-three/postprocessing";
import { useEffect, useState } from "react";
import { Object3D, Light } from "three";
export function Effects({ selection }: { selection: Object3D[] }) {
  const setDpr = useThree((s) => s.setDpr);
  const scene = useThree((s) => s.scene);
  const low = useGame((s) => s.lowQuality);
  const [lights, setLights] = useState<Light[]>([]);
  useEffect(() => {
    const found: Light[] = [];
    scene.traverse((o) => {
      if (o instanceof Light) found.push(o);
    });
    setLights(found);
  }, [scene]);
  return (
    <>
      <AdaptiveDpr pixelated />
      <PerformanceMonitor
        bounds={() => [45, 58]}
        onDecline={() => {
          setDpr(1);
          useGame.setState({ lowQuality: true });
        }}
      />
      {!low && lights.length > 0 && (
        <EffectComposer multisampling={0}>
          <SelectiveBloom
            selection={selection}
            lights={lights}
            ignoreBackground
            luminanceThreshold={0.5}
            intensity={0.55}
            mipmapBlur={false}
            resolutionScale={0.5}
          />
        </EffectComposer>
      )}
    </>
  );
}

import { useFrame, useThree } from '@react-three/fiber';
import { useEffect } from 'react';
import { useGame } from '../game/store';
export function Diagnostics() {
  const context = useThree();
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    Object.assign(window, { __heist: { scene:context.scene, camera:context.camera, renderer:context.gl, store:useGame } });
    return () => { delete (window as unknown as Record<string,unknown>).__heist; };
  }, [context.scene,context.camera,context.gl]);
  useFrame(() => {});
  return null;
}

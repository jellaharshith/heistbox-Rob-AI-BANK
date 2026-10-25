import { useEffect, useRef } from 'react';
import { CameraControls } from '@react-three/drei';
import { Vector3 } from 'three';
import { useAsset, required } from './assets';
import { useGame } from '../game/store';
export function Cameras() {
  const env = useAsset('ENV_Bank');
  const camera = useGame(s => s.camera);
  const controls = useRef<CameraControls>(null);
  useEffect(() => {
    const p = required(env.scene,camera).getWorldPosition(new Vector3());
    // Exported empties carry Blender's Z-up orientation, not a glTF camera -Z axis.
    const target = camera === 'CAM_Overview' ? new Vector3(0,1,-3.2) : new Vector3(p.x,1.6,-6.5);
    void controls.current?.setLookAt(p.x,p.y,p.z,target.x,target.y,target.z,true);
  }, [env,camera]);
  return <CameraControls ref={controls} makeDefault smoothTime={.55} enabled={false}/>;
}

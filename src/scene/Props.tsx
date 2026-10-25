import { useMemo } from 'react';
import { useAnimations } from '@react-three/drei';
import { useAsset, required, validateClips } from './assets';
import { useClip } from './animation';
import { useGame } from '../game/store';
export function Props() {
  const asset = useAsset('PROPS');
  const scene = useMemo(() => {
    const root = asset.scene.clone(true);
    ['VAULT_L_Door','VAULT_M_Door','VAULT_R_Door','PROP_Shredder','FX_Laser','PROP_CashSmall','PROP_CashHeist','PROP_Bill','PROP_Megaphone','PROP_WantedPoster','PROP_Terminal','PROP_Phone','FX_LockdownStrip_L','FX_LockdownStrip_M','FX_LockdownStrip_R'].forEach(n => required(root,n));
    validateClips(asset, ['VAULT_L_Door_Ajar', ...['L','M','R'].flatMap(v => [`VAULT_${v}_Door_Open`,`VAULT_${v}_Door_Slam`])]);
    required(root,'FX_Laser').visible = false;
    required(root,'PROP_Bill').visible = false;
    return root;
  }, [asset]);
  const { actions } = useAnimations(asset.animations, scene);
  useClip(actions, useGame(s => s.clips.L));
  useClip(actions, useGame(s => s.clips.M));
  useClip(actions, useGame(s => s.clips.R));
  return <primitive object={scene} dispose={null}/>;
}

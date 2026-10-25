import { useMemo } from 'react';
import { useAnimations } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js';
import { Vector3 } from 'three';
import { useAsset, required, validateClips } from './assets';
import { collectLODs, updateLOD } from './LOD';
import { useClip } from './animation';
import { useGame } from '../game/store';
const clipNames = { Tina:['Idle','Talk','Typing','Approve','Deny','Alarm'], Heister:['Idle','Talk','Bribe','Celebrate','Caught','Walk','Run','Sneak'], Customer:['Idle','Wait','FaceID','Happy'], Sentinel:['Hover','Scan','Fire'] };
type CharacterName = keyof typeof clipNames;
function Character({ name }: { name: CharacterName }) {
  const asset = useAsset(`CHAR_${name}`);
  const env = useAsset('ENV_Bank');
  const scene = useMemo(() => {
    validateClips(asset, clipNames[name].map(c => `${name}_${c}`));
    const root = clone(asset.scene);
    const pos = name === 'Heister' ? required(env.scene,'SPAWN_Player').position : name === 'Customer' ? required(env.scene,'SPAWN_Customer').position : new Vector3(name === 'Sentinel' ? 4.6 : 0, name === 'Sentinel' ? 2.8 : 0, name === 'Sentinel' ? -5.3 : -1.6);
    root.position.copy(pos);
    if (name === 'Heister' || name === 'Customer') root.rotation.y = Math.PI;
    root.traverse(o => { o.frustumCulled = false; });
    return root;
  }, [asset,env,name]);
  const lods = useMemo(() => name === 'Sentinel' ? [] : collectLODs(scene), [scene,name]);
  const origin = useMemo(() => new Vector3(), []);
  const { actions } = useAnimations(asset.animations, scene);
  const clip = useGame(s => s.clips[name]);
  useClip(actions, clip);
  useFrame(({camera}) => { if (lods.length) { updateLOD(lods, scene.getWorldPosition(origin), camera.position); scene.userData.lodDistance = origin.distanceTo(camera.position); } });
  return <primitive object={scene} dispose={null}/>;
}
export function Characters() { return <>{(Object.keys(clipNames) as CharacterName[]).map(name => <Character key={name} name={name}/>)}</>; }

import { useGLTF } from "@react-three/drei";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { Object3D, type AnimationClip } from "three";
export const files = [
  "CHAR_Tina",
  "CHAR_Heister",
  "CHAR_Customer",
  "CHAR_Sentinel",
  "ENV_Bank",
  "PROPS",
] as const;
const configure: NonNullable<Parameters<typeof useGLTF>[3]> = (loader) => {
  loader.setMeshoptDecoder(MeshoptDecoder);
};
export function useAsset(name: (typeof files)[number]) {
  return useGLTF(`/models/${name}.glb`, false, true, configure);
}
files.forEach((name) =>
  useGLTF.preload(`/models/${name}.glb`, false, true, configure),
);
export function required(root: Object3D, name: string): Object3D {
  const node = root.getObjectByName(name);
  if (!node) {
    console.error(`[GLB CONTRACT] Missing node: ${name}`);
    throw new Error(`Missing asset node ${name}`);
  }
  return node;
}
export function validateClips(
  asset: { animations: AnimationClip[] },
  names: string[],
) {
  for (const name of names)
    if (!asset.animations.some((a) => a.name === name)) {
      console.error(`[GLB CONTRACT] Missing clip: ${name}`);
      throw new Error(`Missing clip ${name}`);
    }
}

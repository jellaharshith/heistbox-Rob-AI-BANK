import { Object3D, Vector3 } from 'three';
export function collectLODs(root: Object3D) {
  const nodes: { node: Object3D; level: number }[] = [];
  root.traverse(node => { const match = /_LOD([012])(?:_|$)/.exec(node.name); if (match) nodes.push({ node, level: Number(match[1]) }); });
  if (!nodes.length) { console.error(`[GLB CONTRACT] No LODs in ${root.name}`); throw new Error('Missing character LODs'); }
  for (const level of [0,1,2]) if (!nodes.some(n => n.level === level)) throw new Error(`Missing LOD${level}`);
  nodes.forEach(({node,level}) => { node.visible = level === 0; });
  return nodes;
}
export const lodAtDistance = (distance: number) => distance < 6 ? 0 : distance < 14 ? 1 : 2;
export function updateLOD(nodes: ReturnType<typeof collectLODs>, origin: Vector3, camera: Vector3) {
  const level = lodAtDistance(origin.distanceTo(camera));
  nodes.forEach(entry => { entry.node.visible = entry.level === level; });
}

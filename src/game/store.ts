import { create } from 'zustand';
export type Vault = 'L' | 'M' | 'R';
export type CameraName = 'CAM_Overview' | 'CAM_VaultL' | 'CAM_VaultM' | 'CAM_VaultR';
type State = {
  ready: boolean; phase: 'LOBBY' | 'ATTACK' | 'RESOLVE' | 'RESULTS'; camera: CameraName;
  clips: Record<string,string>; lowQuality: boolean;
};
export const idleClips = { Tina: 'Tina_Idle', Heister: 'Heister_Idle', Customer: 'Customer_Wait', Sentinel: 'Sentinel_Hover', L: 'VAULT_L_Door_Ajar', M: 'VAULT_M_Door_Slam', R: 'VAULT_R_Door_Slam' };
export const useGame = create<State>(() => ({ ready:false, phase:'LOBBY', camera:'CAM_Overview', clips:idleClips, lowQuality:false }));

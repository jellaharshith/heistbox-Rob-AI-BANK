import { useEffect, useRef } from "react";
import { AnimationAction, LoopOnce, LoopRepeat } from "three";
import { useGame } from "../game/store";
export function useClip(
  actions: Record<string, AnimationAction | null>,
  name: string,
) {
  const previous = useRef<AnimationAction | null>(null);
  const epoch = useGame((s) => s.epoch);
  const lastEpoch = useRef(epoch);
  if (lastEpoch.current !== epoch) {
    lastEpoch.current = epoch;
    previous.current = null;
  }
  useEffect(() => {
    const action = actions[name];
    if (!action) {
      console.error(`[GLB CONTRACT] Missing action: ${name}`);
      throw new Error(`Missing action ${name}`);
    }
    const looping = /Idle|Wait|Hover|Talk|Typing|Bribe|Celebrate|Scan/.test(name);
    action.enabled = true;
    action.setEffectiveTimeScale(1);
    action.setEffectiveWeight(1);
    action
      .reset()
      .setLoop(looping ? LoopRepeat : LoopOnce, looping ? Infinity : 1);
    action.clampWhenFinished = true;
    action.play();
    if (previous.current && previous.current !== action) {
      action.crossFadeFrom(previous.current, 0.35, true);
    } else {
      action.fadeIn(0.35);
    }
    previous.current = action;
    return () => {
      action.fadeOut(0.3);
    };
  }, [actions, name, epoch]);
}

import { useEffect, useRef } from "react";
import { AnimationAction, LoopOnce, LoopRepeat } from "three";
import { useGame } from "../game/store";
export function useClip(
  actions: Record<string, AnimationAction | null>,
  name: string,
) {
  const previous = useRef<AnimationAction | null>(null);
  const epoch = useGame((s) => s.epoch);
  useEffect(() => {
    const action = actions[name];
    if (!action) {
      console.error(`[GLB CONTRACT] Missing action: ${name}`);
      throw new Error(`Missing action ${name}`);
    }
    const looping = /Idle|Wait|Hover|Talk|Typing/.test(name);
    action
      .reset()
      .setLoop(looping ? LoopRepeat : LoopOnce, looping ? Infinity : 1);
    action.clampWhenFinished = true;
    action.play();
    if (previous.current && previous.current !== action)
      action.crossFadeFrom(previous.current, 0.25, false);
    else action.fadeIn(0.25);
    previous.current = action;
    return () => {
      action.fadeOut(0.25);
    };
  }, [actions, name, epoch]);
}

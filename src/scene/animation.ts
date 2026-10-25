import { useEffect, useRef } from 'react';
import { AnimationAction, LoopOnce, LoopRepeat } from 'three';
export function useClip(actions: Record<string, AnimationAction | null>, name: string) {
  const previous = useRef<AnimationAction | null>(null);
  useEffect(() => {
    const action = actions[name];
    if (!action) { console.error(`[GLB CONTRACT] Missing action: ${name}`); throw new Error(`Missing action ${name}`); }
    const looping = /Idle|Wait|Hover|Talk|Typing/.test(name);
    action.reset().setLoop(looping ? LoopRepeat : LoopOnce, looping ? Infinity : 1);
    action.clampWhenFinished = true;
    action.play();
    if (previous.current && previous.current !== action) action.crossFadeFrom(previous.current, .25, false);
    else action.fadeIn(.25);
    previous.current = action;
    return () => { action.fadeOut(.25); };
  }, [actions,name]);
}

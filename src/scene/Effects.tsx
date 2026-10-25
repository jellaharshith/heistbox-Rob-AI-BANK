import { AdaptiveDpr, PerformanceMonitor } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import { useGame } from '../game/store';
export function Effects() {
  const setDpr = useThree(s => s.setDpr);
  return <><AdaptiveDpr pixelated/><PerformanceMonitor bounds={() => [45,58]} onDecline={() => {setDpr(1); useGame.setState({lowQuality:true});}}/></>;
}

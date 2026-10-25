import React, { Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import { Canvas } from '@react-three/fiber';
import { useProgress } from '@react-three/drei';
import { Bank } from './scene/Bank';
import { useGame } from './game/store';
import './style.css';
class Boundary extends React.Component<React.PropsWithChildren, {error:string}> {
  state = {error:''};
  static getDerivedStateFromError(error: Error) { return {error:error.message}; }
  render() { return this.state.error ? <div className="fatal">Asset contract failure: {this.state.error}<p>Check the console and assets3d load test.</p></div> : this.props.children; }
}
function App() {
  const ready = useGame(s => s.ready);
  const { progress } = useProgress();
  return <Boundary><main><header><a className="brand" href="/">H<span>×</span>P</a><div><b>HEISTBOX <span>× PAIR</span></b><small>THE ADVERSARIAL BANKING EXPERIMENT</small></div><div className="status">● ASSET PREVIEW</div></header><section className="intro"><p className="eyebrow">ONE PROMPT. THREE LINES OF DEFENSE.</p><h1>Rob our AI bank.</h1><p>Talk your way past Tina. See which vault holds.</p></section><div className="arena"><Canvas dpr={[1,1.5]} camera={{position:[0,3.2,5.6],fov:65,near:.05,far:100}}><Suspense fallback={null}><Bank/></Suspense></Canvas><div className="scene-label">LIVE BANK FLOOR <span>01 / OVERVIEW</span></div></div><div className="vaults">{['LLM Judge','Firewall','PAIR'].map((name,i) => <article key={name}><small>VAULT {['L','M','R'][i]} / {['SEMANTIC TRUST','ZERO TOLERANCE','VERIFIED ENTITLEMENTS'][i]}</small><h2>{name}</h2><p>{['Trusts the story.','Freezes the entire request.','Checks what you are owed.'][i]}</p><strong>$0 <small>STOLEN</small></strong></article>)}</div><footer>SCENE CHECKPOINT · Models loaded once. Camera-distance LODs active.</footer>{!ready && <div className="loading"><b>Opening the bank</b><progress value={progress} max={100}/><span>{Math.round(progress)}% · decoding six GLBs</span></div>}</main></Boundary>;
}
createRoot(document.getElementById('root')!).render(<App/>);

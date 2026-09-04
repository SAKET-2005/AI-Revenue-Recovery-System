import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Line, PerspectiveCamera } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { cn } from "@/lib/utils";

const cyan = "#6DE7F2";
const green = "#81E6A8";
const amber = "#F0B36B";
const blue = "#8295FF";

type NodeData = { id: string; label: string; position: [number, number, number]; color: string; value: string; sub: string };
const nodes: NodeData[] = [
  { id: "transactions", label: "TRANSACTIONS", position: [-4.3, 1.5, 0], color: blue, value: "18.4L", sub: "processed" },
  { id: "infra", label: "PAYMENT INFRA", position: [-2.2, 0, .35], color: cyan, value: "98.2%", sub: "healthy" },
  { id: "risk", label: "REVENUE AT RISK", position: [.25, 1.7, -.15], color: amber, value: "₹3.2L", sub: "exposed" },
  { id: "engine", label: "AI RECOVERY", position: [.5, -.6, .4], color: cyan, value: "91%", sub: "confidence" },
  { id: "recovered", label: "RECOVERED REVENUE", position: [3.45, .25, .15], color: green, value: "₹2.1L", sub: "recovered" },
];

function ParticleField({ reduced = false }: { reduced?: boolean }) {
  const ref = useRef<THREE.Points>(null);
  const count = reduced ? 34 : 115;
  const positions = useMemo(() => { const p = new Float32Array(count * 3); for (let i = 0; i < count; i++) { const t = i / count; p[i * 3] = -5 + t * 9.2; p[i * 3 + 1] = Math.sin(t * 8.4) * .6 + (Math.random() - .5) * 2.1; p[i * 3 + 2] = (Math.random() - .5) * 2.4; } return p; }, [count]);
  useFrame((_, delta) => { if (ref.current) { ref.current.rotation.y += delta * .018; ref.current.rotation.z += delta * .006; } });
  return <points ref={ref}><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} count={count} array={positions} itemSize={3} /></bufferGeometry><pointsMaterial color={cyan} size={reduced ? .045 : .035} transparent opacity={.62} sizeAttenuation /></points>;
}

function FlowParticles({ color, start, end, reduced = false }: { color: string; start: [number, number, number]; end: [number, number, number]; reduced?: boolean }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const count = reduced ? 3 : 8;
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const seeds = useMemo(() => Array.from({ length: count }, (_, i) => i / count), [count]);
  useFrame(({ clock }) => { if (!ref.current) return; const time = clock.getElapsedTime() * (reduced ? .12 : .22); seeds.forEach((seed, i) => { const t = (seed + time) % 1; const curve = Math.sin(t * Math.PI) * .42; dummy.position.set(THREE.MathUtils.lerp(start[0], end[0], t), THREE.MathUtils.lerp(start[1], end[1], t) + curve, THREE.MathUtils.lerp(start[2], end[2], t)); dummy.scale.setScalar(.45 + Math.sin(t * Math.PI) * .35); dummy.updateMatrix(); ref.current?.setMatrixAt(i, dummy.matrix); }); ref.current.instanceMatrix.needsUpdate = true; });
  return <instancedMesh ref={ref} args={[undefined, undefined, count]}><sphereGeometry args={[.055, 8, 8]} /><meshBasicMaterial color={color} transparent opacity={.85} /></instancedMesh>;
}

function FlowLine({ points, color, opacity = .46 }: { points: [number, number, number][]; color: string; opacity?: number }) { return <Line points={points} color={color} transparent opacity={opacity} lineWidth={1.2} />; }

function NetworkScene({ onSelect, reduced }: { onSelect?: (node: NodeData) => void; reduced: boolean }) {
  const group = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  useFrame(({ pointer }) => { if (!group.current || reduced) return; group.current.rotation.y = THREE.MathUtils.lerp(group.current.rotation.y, pointer.x * .07, .04); group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, -pointer.y * .04, .04); });
  return <group ref={group}>
    <ParticleField reduced={reduced} />
    <FlowLine points={[[-4.3, 1.5, 0], [-2.2, 0, .35], [.5, -.6, .4], [3.45, .25, .15]]} color={cyan} opacity={.5} />
    <FlowLine points={[[-2.2, 0, .35], [.25, 1.7, -.15]]} color={amber} opacity={.52} />
    <FlowLine points={[[.25, 1.7, -.15], [.5, -.6, .4]]} color={cyan} opacity={.42} />
    <FlowLine points={[[.5, -.6, .4], [3.45, .25, .15]]} color={green} opacity={.62} />
    <FlowParticles color={cyan} start={[-4.3, 1.5, 0]} end={[-2.2, 0, .35]} reduced={reduced} />
    <FlowParticles color={amber} start={[-2.2, 0, .35]} end={[.25, 1.7, -.15]} reduced={reduced} />
    <FlowParticles color={cyan} start={[.25, 1.7, -.15]} end={[.5, -.6, .4]} reduced={reduced} />
    <FlowParticles color={green} start={[.5, -.6, .4]} end={[3.45, .25, .15]} reduced={reduced} />
    {nodes.map((node, index) => <Float key={node.id} speed={reduced ? 0 : 1.15 + index * .06} rotationIntensity={reduced ? 0 : .12} floatIntensity={reduced ? 0 : .16}><group position={node.position} onPointerOver={(event) => { event.stopPropagation(); setHovered(node.id); }} onPointerOut={() => setHovered(null)} onClick={(event) => { event.stopPropagation(); onSelect?.(node); }}><mesh><sphereGeometry args={[node.id === "engine" ? .22 : .14, 20, 20]} /><meshStandardMaterial color={node.color} emissive={node.color} emissiveIntensity={node.id === "engine" ? 2.8 : 1.5} roughness={.35} metalness={.25} /></mesh><mesh scale={node.id === "engine" ? 1.8 : 1.45}><sphereGeometry args={[.14, 16, 16]} /><meshBasicMaterial color={node.color} transparent opacity={.07} /></mesh>{hovered === node.id && <group position={[0, .42, 0]}><mesh><planeGeometry args={[1.6, .48]} /><meshBasicMaterial color="#0B1A24" transparent opacity={.96} /></mesh><sprite><spriteMaterial color="#DDECEF" transparent opacity={.9} /></sprite></group>}</group></Float>)}
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.6, 0]}><planeGeometry args={[12, 7]} /><meshBasicMaterial color="#0A151D" transparent opacity={.42} /></mesh>
  </group>;
}

export function RevenueNetwork({ className, compact = false, onSelect }: { className?: string; compact?: boolean; onSelect?: (node: NodeData) => void }) {
  const [reduced, setReduced] = useState(false);
  return <div className={cn("relative overflow-hidden rounded-[18px] border border-white/[0.1] bg-[#09151e]", className)} onDoubleClick={() => setReduced((value) => !value)}>
    <div className="absolute inset-0 signal-grid opacity-40" /><img src="/images/reviveai-network-reference.png" alt="" aria-hidden="true" className="absolute inset-0 h-full w-full object-cover opacity-[.14] mix-blend-screen" />
    <Canvas dpr={[1, 1.6]} gl={{ antialias: true, powerPreference: "high-performance", alpha: true }} camera={{ position: [0, 0, 9], fov: 36 }} style={{ position: "absolute", inset: 0 }}><PerspectiveCamera makeDefault position={[0, 0, 9]} fov={compact ? 40 : 36} /><ambientLight intensity={.34} /><pointLight position={[0, 2, 4]} color={cyan} intensity={5} distance={7} /><pointLight position={[2, -1, 2]} color={green} intensity={3} distance={5} /><NetworkScene onSelect={onSelect} reduced={reduced} /></Canvas>
    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#09151e] to-transparent" />
    {compact && <div className="pointer-events-none absolute bottom-3 left-4 font-mono text-[8px] uppercase tracking-[.18em] text-[#6A8790]">Double click to {reduced ? "resume" : "reduce"} motion</div>}
  </div>;
}

export function NetworkLegend() { return <div className="flex flex-wrap gap-3 font-mono text-[9px] uppercase tracking-[.12em] text-[#6E8791]"><span className="flex items-center gap-2"><i className="h-1.5 w-1.5 rounded-full bg-[#8295FF]" />processed</span><span className="flex items-center gap-2"><i className="h-1.5 w-1.5 rounded-full bg-[#F0B36B]" />at risk</span><span className="flex items-center gap-2"><i className="h-1.5 w-1.5 rounded-full bg-[#6DE7F2]" />AI flow</span><span className="flex items-center gap-2"><i className="h-1.5 w-1.5 rounded-full bg-[#81E6A8]" />recovered</span></div>; }

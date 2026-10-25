export type Point = { x: number; y: number };
export type SimAgent = Point & { id: string; waiting?: boolean };

const neighbors = (p: Point) => [{ x: p.x + 1, y: p.y }, { x: p.x - 1, y: p.y }, { x: p.x, y: p.y + 1 }, { x: p.x, y: p.y - 1 }];
const key = (p: Point) => `${p.x}:${p.y}`;

export function aStar(start: Point, goal: Point, blocked: Set<string>, width = 12, height = 10): Point[] {
  const open = [start]; const came = new Map<string, Point>(); const g = new Map([[key(start), 0]]);
  const score = (p: Point) => Math.abs(p.x - goal.x) + Math.abs(p.y - goal.y);
  while (open.length) {
    open.sort((a, b) => score(a) + (g.get(key(a)) ?? 0) - score(b) - (g.get(key(b)) ?? 0));
    const current = open.shift()!;
    if (key(current) === key(goal)) { const path = [current]; while (came.has(key(path[0]))) path.unshift(came.get(key(path[0]))!); return path; }
    for (const next of neighbors(current)) {
      if (next.x < 0 || next.y < 0 || next.x >= width || next.y >= height || blocked.has(key(next))) continue;
      const nextG = (g.get(key(current)) ?? 0) + 1;
      if (nextG < (g.get(key(next)) ?? Infinity)) { came.set(key(next), current); g.set(key(next), nextG); if (!open.some((p) => key(p) === key(next))) open.push(next); }
    }
  }
  return [start];
}

export function giveWay(agent: SimAgent, occupied: Set<string>): SimAgent { return { ...agent, waiting: occupied.has(key(agent)) }; }

/* Copyright 2026 Aaron John Schlosser, PhD. */
/** Orthogonal visibility-grid routing. Cards are obstacles; occupied parallel segments
 * are unavailable. Perpendicular crossings are rendered with a visible bridge casing. */
export type RoutePoint = { x: number; y: number };
export type RouteBox = RoutePoint & { id: string; width: number; height: number };
export type RouteEdge = { id: string; from: string; to: string };
type Segment = [RoutePoint, RoutePoint];

function overlaps([a, b]: Segment, [c, d]: Segment) {
  if (a.x === b.x && c.x === d.x && a.x === c.x)
    return (
      Math.min(Math.max(a.y, b.y), Math.max(c.y, d.y)) >
      Math.max(Math.min(a.y, b.y), Math.min(c.y, d.y))
    );
  if (a.y === b.y && c.y === d.y && a.y === c.y)
    return (
      Math.min(Math.max(a.x, b.x), Math.max(c.x, d.x)) >
      Math.max(Math.min(a.x, b.x), Math.min(c.x, d.x))
    );
  return false;
}
function crosses([a, b]: Segment, [c, d]: Segment) {
  if (overlaps([a, b], [c, d])) return true;
  if ((a.x === b.x) === (c.x === d.x)) return false;
  const [v1, v2, h1, h2] = a.x === b.x ? [a, b, c, d] : [c, d, a, b];
  return (
    v1.x >= Math.min(h1.x, h2.x) &&
    v1.x <= Math.max(h1.x, h2.x) &&
    h1.y >= Math.min(v1.y, v2.y) &&
    h1.y <= Math.max(v1.y, v2.y)
  );
}
function blocked([a, b]: Segment, boxes: RouteBox[]) {
  return boxes.some((n) =>
    a.x === b.x
      ? a.x > n.x - 6 &&
        a.x < n.x + n.width + 6 &&
        Math.max(a.y, b.y) > n.y - 6 &&
        Math.min(a.y, b.y) < n.y + n.height + 6
      : a.y > n.y - 6 &&
        a.y < n.y + n.height + 6 &&
        Math.max(a.x, b.x) > n.x - 6 &&
        Math.min(a.x, b.x) < n.x + n.width + 6,
  );
}
class Queue {
  private heap: Array<{ id: number; cost: number }> = [];
  push(value: { id: number; cost: number }) {
    const h = this.heap;
    h.push(value);
    let i = h.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (h[p].cost <= value.cost) break;
      h[i] = h[p];
      i = p;
    }
    h[i] = value;
  }
  pop() {
    const h = this.heap,
      first = h[0],
      last = h.pop();
    if (h.length && last) {
      let i = 0;
      while (i * 2 + 1 < h.length) {
        let c = i * 2 + 1;
        if (c + 1 < h.length && h[c + 1].cost < h[c].cost) c++;
        if (last.cost <= h[c].cost) break;
        h[i] = h[c];
        i = c;
      }
      h[i] = last;
    }
    return first;
  }
}
function findRoute(
  start: RoutePoint,
  end: RoutePoint,
  boxes: RouteBox[],
  occupied: Segment[],
  lane: number,
  reserved: Segment[],
) {
  const clearance = 16 + lane * 10;
  const xs = [
    ...new Set([
      ...occupied.flatMap(([a, b]) => [a.x - 10, a.x + 10, b.x - 10, b.x + 10]),
      start.x,
      end.x,
      ...boxes.flatMap((n) => [
        n.x - clearance,
        n.x + n.width + clearance,
        n.x - 8,
        n.x + n.width + 8,
      ]),
    ]),
  ].sort((a, b) => a - b);
  const ys = [
    ...new Set([
      ...occupied.flatMap(([a, b]) => [a.y - 10, a.y + 10, b.y - 10, b.y + 10]),
      start.y,
      end.y,
      ...boxes.flatMap((n) => [
        n.y - clearance,
        n.y + n.height + clearance,
        n.y - 8,
        n.y + n.height + 8,
      ]),
    ]),
  ].sort((a, b) => a - b);
  const width = xs.length;
  const id = (p: RoutePoint) => ys.indexOf(p.y) * width + xs.indexOf(p.x);
  const point = (i: number) => ({ x: xs[i % width], y: ys[Math.floor(i / width)] });
  const begin = id(start),
    target = id(end),
    queue = new Queue();
  const distance = new Map<number, number>([[begin, 0]]),
    parent = new Map<number, number>();
  queue.push({ id: begin, cost: 0 });
  const visited = new Set<number>();
  for (let current = queue.pop(); current; current = queue.pop()) {
    const index = current.id;
    if (visited.has(index)) continue;
    if (index === target) {
      const result: RoutePoint[] = [end];
      let at = target;
      while (at !== begin) {
        at = parent.get(at)!;
        result.push(point(at));
      }
      return result.reverse();
    }
    visited.add(index);
    const x = index % width,
      y = Math.floor(index / width),
      a = point(index);
    const adjacent = [
      x > 0 ? index - 1 : -1,
      x + 1 < width ? index + 1 : -1,
      y > 0 ? index - width : -1,
      y + 1 < ys.length ? index + width : -1,
    ];
    for (const next of adjacent) {
      if (next < 0 || visited.has(next)) continue;
      const b = point(next),
        segment: Segment = [a, b];
      if (
        blocked(segment, boxes) ||
        occupied.some((other) => overlaps(segment, other)) ||
        reserved.some((other) => crosses(segment, other))
      )
        continue;
      const previous = parent.get(index);
      const before = previous === undefined ? null : point(previous);
      const turn = before && (before.x === a.x) !== (a.x === b.x) ? 24 : 0;
      const cost = distance.get(index)! + Math.abs(b.x - a.x) + Math.abs(b.y - a.y) + turn;
      if (cost >= (distance.get(next) ?? Infinity)) continue;
      distance.set(next, cost);
      parent.set(next, index);
      queue.push({ id: next, cost: cost + Math.abs(b.x - end.x) + Math.abs(b.y - end.y) });
    }
  }
  throw new Error(
    `No unobstructed pipeline connection route: lane ${lane}, start ${JSON.stringify(start)}, end ${JSON.stringify(end)}`,
  );
}
export function routePipelineEdges<T extends RouteEdge>(
  nodes: RouteBox[],
  edges: T[],
  orientation: "horizontal" | "vertical",
) {
  const occupied: Segment[] = [];
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const ports = edges.map((edge) => {
    const from = byId.get(edge.from)!,
      to = byId.get(edge.to)!;
    const out = edges.filter((e) => e.from === edge.from).findIndex((e) => e.id === edge.id);
    const into = edges.filter((e) => e.to === edge.to).findIndex((e) => e.id === edge.id);
    const vertical = orientation === "vertical";
    const start = vertical
      ? { x: from.x + 24 + out * 18, y: from.y + from.height }
      : { x: from.x + from.width, y: from.y + 24 + out * 18 };
    const end = vertical
      ? { x: to.x + 24 + into * 18, y: to.y }
      : { x: to.x, y: to.y + 24 + into * 18 };
    const exit = { x: start.x + (vertical ? 0 : 12), y: start.y + (vertical ? 12 : 0) };
    const entry = { x: end.x - (vertical ? 0 : 12), y: end.y - (vertical ? 12 : 0) };
    return { start, end, exit, entry };
  });
  return edges.map((edge, lane) => {
    const { start, end, exit, entry } = ports[lane];
    // Reserve even future arrowheads and exits so earlier routes cannot occupy them.
    const reserved: Segment[] = ports.flatMap((p, i) =>
      i === lane
        ? []
        : ([
            [p.start, p.exit],
            [p.entry, p.end],
          ] as Segment[]),
    );
    const points = [
      start,
      ...findRoute(exit, entry, nodes, [...occupied, ...reserved], lane, reserved),
      end,
    ];
    const compact: RoutePoint[] = [];
    for (const p of points) {
      while (compact.length > 1) {
        const a = compact[compact.length - 2],
          b = compact[compact.length - 1];
        if (!((a.x === b.x && b.x === p.x) || (a.y === b.y && b.y === p.y))) break;
        compact.pop();
      }
      compact.push(p);
    }
    for (let i = 1; i < compact.length; i++) occupied.push([compact[i - 1], compact[i]]);
    return {
      ...edge,
      points: compact,
      path: compact.map((p, i) => (i ? "L " : "M ") + p.x + " " + p.y).join(" "),
    };
  });
}

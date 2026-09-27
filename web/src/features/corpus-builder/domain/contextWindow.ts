// Copyright 2026 Aaron John Schlosser, PhD.

/** Text-bearing neighbour of the record under review. */
export interface ContextNeighbour {
  text: string;
}

export interface ContextFit<T extends ContextNeighbour> {
  before: T[];
  after: T[];
}

/**
 * Choose how many neighbouring records fit around the record under review.
 *
 * The reading window has a fixed capacity, measured in characters. The record under review always comes first: what
 * it leaves over is shared between the records before and after it, nearest first, and a neighbour is shown whole
 * or not at all. A large record therefore has few (or no) neighbours and a small one has many, so the record lands in
 * the reader's line of sight instead of being pushed down by the text above it.
 *
 * Records before it only push it down, so they get the smaller share (`beforeShare`); whatever they leave unused
 * goes to the records after it. `overhead` is the fixed cost of a neighbour (its heading and spacing) in characters.
 */
export function fitContext<T extends ContextNeighbour>(
  before: T[],
  after: T[],
  focusChars: number,
  capacityChars: number,
  { beforeShare = 0.4, overhead = 0 }: { beforeShare?: number; overhead?: number } = {},
): ContextFit<T> {
  const remaining = capacityChars - focusChars;
  if (!(remaining > 0)) return { before: [], after: [] };
  const take = (items: T[], budget: number, nearestLast: boolean) => {
    const ordered = nearestLast ? [...items].reverse() : items;
    const kept: T[] = [];
    let used = 0;
    for (const item of ordered) {
      const cost = item.text.length + overhead;
      if (used + cost > budget) break;
      kept.push(item);
      used += cost;
    }
    return { kept: nearestLast ? kept.reverse() : kept, used };
  };
  const earlier = take(before, remaining * beforeShare, true);
  const later = take(after, remaining - earlier.used, false);
  return { before: earlier.kept, after: later.kept };
}

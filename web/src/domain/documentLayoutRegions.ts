/* Copyright 2026 Aaron John Schlosser, PhD. */

/** A rectangle the reviewer applies to many pages, not a box around one passage. */
export type LayoutRole =
  "main" | "margin_parallel" | "margin_apparatus" | "infobox" | "block_quote" | "running_matter";

export type LayoutThread = "thread_a" | "thread_b" | "thread_c" | "thread_d";

export type LayoutScope = "all" | "odd" | "even" | "range" | "page";

export type LayoutFlow = "with_main" | "separate";

export interface LayoutRegion {
  id: string;
  role: LayoutRole;
  thread: LayoutThread;
  language?: string | null;
  flow: LayoutFlow;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  applies_to: LayoutScope;
  page_start?: number | null;
  page_end?: number | null;
  page?: number | null;
  label?: string | null;
}

export const MAX_LAYOUT_REGIONS = 24;
export const LAYOUT_ROLES: LayoutRole[] = [
  "main",
  "margin_parallel",
  "margin_apparatus",
  "infobox",
  "block_quote",
  "running_matter",
];
export const LAYOUT_THREADS: LayoutThread[] = ["thread_a", "thread_b", "thread_c", "thread_d"];

const DEFAULT_FLOW: Record<LayoutRole, LayoutFlow> = {
  main: "with_main",
  block_quote: "with_main",
  margin_parallel: "separate",
  margin_apparatus: "separate",
  infobox: "separate",
  running_matter: "separate",
};

export function defaultFlow(role: LayoutRole): LayoutFlow {
  return role === "main" ? "with_main" : DEFAULT_FLOW[role];
}

function round4(value: number) {
  return Math.round(value * 10000) / 10000;
}

export function clamp01(value: number) {
  return Math.min(1, Math.max(0, value));
}

export function canonicalRegion(region: LayoutRegion): LayoutRegion {
  let x0 = round4(Number(region.x0) || 0);
  let y0 = round4(Number(region.y0) || 0);
  let x1 = round4(Number(region.x1) || 0);
  let y1 = round4(Number(region.y1) || 0);
  if (x1 < x0) [x0, x1] = [x1, x0];
  if (y1 < y0) [y0, y1] = [y1, y0];
  const role = region.role;
  return {
    id: region.id,
    role,
    thread: region.thread || "thread_a",
    language: String(region.language || "").trim(),
    flow: role === "main" ? "with_main" : region.flow || defaultFlow(role),
    x0,
    y0,
    x1,
    y1,
    applies_to: region.applies_to || "all",
    page_start: region.applies_to === "range" ? region.page_start || null : null,
    page_end: region.applies_to === "range" ? region.page_end || null : null,
    page: region.applies_to === "page" ? region.page || null : null,
    label: String(region.label || "").trim(),
  };
}

export function regionApplies(region: LayoutRegion, page: number) {
  if (region.applies_to === "odd") return page % 2 === 1;
  if (region.applies_to === "even") return page % 2 === 0;
  if (region.applies_to === "page") return Number(region.page) === page;
  if (region.applies_to === "range") {
    const start = Number(region.page_start || 0);
    const end = Number(region.page_end || 0);
    return start <= page && page <= end;
  }
  return true;
}

function area(region: LayoutRegion) {
  return Math.max(0, region.x1 - region.x0) * Math.max(0, region.y1 - region.y0);
}

function specificity(region: LayoutRegion) {
  if (region.applies_to === "page") return 3;
  if (region.applies_to === "range") return 2;
  if (region.applies_to === "odd" || region.applies_to === "even") return 1;
  return 0;
}

export function matchRegion(
  regions: LayoutRegion[],
  page: number,
  bbox: number[] | undefined,
  width: number,
  height: number,
) {
  if (!regions.length || !bbox || bbox.length < 4 || width <= 0 || height <= 0) return null;
  const x = ((Number(bbox[0]) || 0) + (Number(bbox[2]) || 0)) / 2 / width;
  const y = ((Number(bbox[1]) || 0) + (Number(bbox[3]) || 0)) / 2 / height;
  const hits = regions
    .map((region, index) => ({ region, index }))
    .filter(
      ({ region }) =>
        regionApplies(region, page) &&
        region.x0 <= x &&
        x <= region.x1 &&
        region.y0 <= y &&
        y <= region.y1,
    );
  if (!hits.length) return null;
  hits.sort(
    (left, right) =>
      specificity(right.region) - specificity(left.region) ||
      area(left.region) - area(right.region) ||
      right.index - left.index,
  );
  return hits[0].region;
}

export function newRegionId(existing: string[]) {
  const used = new Set(existing);
  let id = "";
  do {
    id = `r${Math.random().toString(36).slice(2, 8)}`;
  } while (used.has(id) || !/^[a-z][a-z0-9_-]{0,39}$/.test(id));
  return id;
}

export function fullPageMain(): LayoutRegion {
  return {
    id: "main",
    role: "main",
    thread: "thread_a",
    language: "",
    flow: "with_main",
    x0: 0,
    y0: 0,
    x1: 1,
    y1: 1,
    applies_to: "all",
    page_start: null,
    page_end: null,
    page: null,
    label: "",
  };
}

export function marginBand(side: "left" | "right"): LayoutRegion {
  const width = 0.2;
  return {
    id: "margin",
    role: "margin_apparatus",
    thread: "thread_b",
    language: "",
    flow: "separate",
    x0: side === "left" ? 0 : round4(1 - width),
    y0: 0.04,
    x1: side === "left" ? width : 1,
    y1: 0.96,
    applies_to: "all",
    page_start: null,
    page_end: null,
    page: null,
    label: "",
  };
}

export function placeMargin(region: LayoutRegion, side: "left" | "right"): LayoutRegion {
  const width = Math.min(0.45, Math.max(0.08, region.x1 - region.x0));
  return canonicalRegion({
    ...region,
    x0: side === "left" ? 0 : round4(1 - width),
    x1: side === "left" ? round4(width) : 1,
  });
}

export function marginSide(region: LayoutRegion): "left" | "right" {
  return (region.x0 + region.x1) / 2 < 0.5 ? "left" : "right";
}

export type LayoutRecipe = "single" | "two_up" | "margin" | "infobox" | "quote" | "custom";

export function presetRegions(
  recipe: LayoutRecipe,
  side: "left" | "right" = "left",
): LayoutRegion[] {
  if (recipe === "margin") return [fullPageMain(), marginBand(side)];
  if (recipe === "infobox") {
    return [
      fullPageMain(),
      {
        id: "infobox",
        role: "infobox",
        thread: "thread_b",
        language: "",
        flow: "separate",
        x0: 0.52,
        y0: 0.08,
        x1: 0.94,
        y1: 0.36,
        applies_to: "all",
        page_start: null,
        page_end: null,
        page: null,
        label: "",
      },
    ];
  }
  if (recipe === "quote") {
    return [
      fullPageMain(),
      {
        id: "quote",
        role: "block_quote",
        thread: "thread_a",
        language: "",
        flow: "with_main",
        x0: 0.14,
        y0: 0.28,
        x1: 0.86,
        y1: 0.48,
        applies_to: "all",
        page_start: null,
        page_end: null,
        page: null,
        label: "",
      },
    ];
  }
  return [];
}

export function detectRecipe(pageLayout: string, regions: LayoutRegion[]): LayoutRecipe {
  if (pageLayout === "two_up") return regions.length ? "custom" : "two_up";
  if (!regions.length) return "single";
  const roles = new Set(regions.map((region) => region.role));
  if ([...roles].some((role) => role === "margin_parallel" || role === "margin_apparatus"))
    return "margin";
  if (roles.has("infobox")) return "infobox";
  if (roles.has("block_quote") && !roles.has("running_matter")) return "quote";
  if (roles.size === 1 && roles.has("main")) return "single";
  return "custom";
}

export function regionFromRect(
  rect: { x0: number; y0: number; x1: number; y1: number },
  page: number,
  existing: LayoutRegion[],
): LayoutRegion {
  const x0 = clamp01(Math.min(rect.x0, rect.x1));
  const y0 = clamp01(Math.min(rect.y0, rect.y1));
  const x1 = clamp01(Math.max(rect.x0, rect.x1));
  const y1 = clamp01(Math.max(rect.y0, rect.y1));
  const width = x1 - x0;
  const height = y1 - y0;
  let role: LayoutRole = "infobox";
  if (height < 0.12 && (y0 < 0.08 || y1 > 0.92)) role = "running_matter";
  else if (width < 0.28 && (x0 < 0.08 || x1 > 0.92)) role = "margin_apparatus";
  const separate = defaultFlow(role) === "separate";
  return canonicalRegion({
    id: newRegionId(existing.map((region) => region.id)),
    role,
    thread: separate ? "thread_b" : "thread_a",
    language: "",
    flow: defaultFlow(role),
    x0,
    y0,
    x1,
    y1,
    applies_to: "all",
    page_start: null,
    page_end: null,
    page,
    label: "",
  });
}

export function moveRegion(region: LayoutRegion, dx: number, dy: number): LayoutRegion {
  const width = region.x1 - region.x0;
  const height = region.y1 - region.y0;
  let x0 = region.x0 + dx;
  let y0 = region.y0 + dy;
  x0 = Math.min(Math.max(0, x0), 1 - width);
  y0 = Math.min(Math.max(0, y0), 1 - height);
  return canonicalRegion({ ...region, x0, y0, x1: x0 + width, y1: y0 + height });
}

export type RegionEdge = "n" | "s" | "e" | "w";

export function resizeRegion(
  region: LayoutRegion,
  edge: RegionEdge,
  x: number,
  y: number,
): LayoutRegion {
  const next = { ...region };
  const min = 0.03;
  if (edge === "w") next.x0 = Math.min(clamp01(x), region.x1 - min);
  if (edge === "e") next.x1 = Math.max(clamp01(x), region.x0 + min);
  if (edge === "n") next.y0 = Math.min(clamp01(y), region.y1 - min);
  if (edge === "s") next.y1 = Math.max(clamp01(y), region.y0 + min);
  return canonicalRegion(next);
}

export function edgeAt(x: number, y: number, width: number, height: number): RegionEdge | null {
  if (width < 28 || height < 28) return null;
  const margin = 10;
  if (x <= margin) return "w";
  if (x >= width - margin) return "e";
  if (y <= margin) return "n";
  if (y >= height - margin) return "s";
  return null;
}

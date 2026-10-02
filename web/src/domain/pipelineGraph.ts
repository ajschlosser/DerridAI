/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { PipelineDefinition, PipelineRunTrace, PipelineStage } from "../types/pipelines";

export const PIPELINE_NODE_WIDTH = 280;
export const PIPELINE_NODE_HEIGHT = 160;
const CANVAS_PAD = 64;

export type PipelineEdgeKind = "next" | "on_empty" | "on_unavailable" | "on_timeout" | "on_error";
export type PipelineDiagramOrientation = "horizontal" | "vertical";
export type PipelineDiagramDensity = "compact" | "standard" | "wide";

const DENSITY_SPACING: Record<PipelineDiagramDensity, { columnGap: number; rowGap: number }> = {
  compact: { columnGap: 100, rowGap: 88 },
  standard: { columnGap: 160, rowGap: 112 },
  wide: { columnGap: 220, rowGap: 160 },
};

export type PipelineGraphEdge = {
  id: string;
  from: string;
  to: string;
  kind: PipelineEdgeKind;
  traversed: boolean;
  path: string;
  lane: number;
};

export type PipelineGraphNode = {
  id: string;
  strategy: string;
  enabled: boolean;
  entry: boolean;
  x: number;
  y: number;
  executionStatus: string | null;
  presence: "configured" | "not_reached" | "observed_only";
  elapsedMs: number | null;
  inputCount: number | null;
  outputCount: number | null;
  fallbackReason: string | null;
};

export type PipelineDiagram = {
  nodes: PipelineGraphNode[];
  edges: PipelineGraphEdge[];
  width: number;
  height: number;
};

const FALLBACKS: Array<{ key: keyof PipelineStage; kind: PipelineEdgeKind }> = [
  { key: "on_empty", kind: "on_empty" },
  { key: "on_unavailable", kind: "on_unavailable" },
  { key: "on_timeout", kind: "on_timeout" },
  { key: "on_error", kind: "on_error" },
];

function stageList(value: unknown): PipelineStage[] {
  if (!Array.isArray(value)) return [];
  const stages: PipelineStage[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    const id = String(row.id || row.stage_id || "").trim();
    const strategy = String(row.strategy || row.strategy_id || "").trim();
    if (!id || !strategy) continue;
    stages.push({
      id,
      strategy,
      enabled: row.enabled !== false,
      config: {},
      next: Array.isArray(row.next) ? row.next.map((target) => String(target)) : [],
      on_empty: row.on_empty ? String(row.on_empty) : null,
      on_unavailable: row.on_unavailable ? String(row.on_unavailable) : null,
      on_timeout: row.on_timeout ? String(row.on_timeout) : null,
      on_error: row.on_error ? String(row.on_error) : null,
    });
  }
  return stages;
}

export function configurationForTrace(
  trace: PipelineRunTrace,
  pipelines: PipelineDefinition[],
): { stages: PipelineStage[]; entryStageIds: string[]; catalogKey: string | null } {
  const match = pipelines.find(
    (item) => item.pipeline_id === trace.pipeline_id && item.version === trace.pipeline_version,
  );
  if (match) {
    return {
      stages: match.stages,
      entryStageIds: match.entry_stage_ids,
      catalogKey: `${match.pipeline_id}@${match.version}`,
    };
  }

  const resolved = trace.resolved_pipeline;
  const resolvedStages = stageList(resolved?.stages);
  if (resolvedStages.length) {
    const entries = Array.isArray(resolved.entry_stage_ids)
      ? resolved.entry_stage_ids.map((item) => String(item))
      : resolvedStages.slice(0, 1).map((item) => item.id);
    return { stages: resolvedStages, entryStageIds: entries, catalogKey: null };
  }

  return {
    stages: trace.stages.map((stage, index) => ({
      id: stage.stage_id,
      strategy: stage.strategy_id,
      enabled: true,
      config: {},
      next: trace.stages[index + 1] ? [trace.stages[index + 1].stage_id] : [],
    })),
    entryStageIds: trace.stages[0] ? [trace.stages[0].stage_id] : [],
    catalogKey: null,
  };
}

/** Separate connection ports and route long/backward edges outside the card grid. */
export function pipelineEdgePath(
  from: PipelineGraphNode,
  to: PipelineGraphNode,
  lane = 0,
  nodes: PipelineGraphNode[] = [from, to],
  orientation: PipelineDiagramOrientation = "horizontal",
): string {
  const vertical = orientation === "vertical";
  const primary = (node: PipelineGraphNode) => (vertical ? node.y : node.x);
  const secondary = (node: PipelineGraphNode) => (vertical ? node.x : node.y);
  const length = vertical ? PIPELINE_NODE_HEIGHT : PIPELINE_NODE_WIDTH;
  const breadth = vertical ? PIPELINE_NODE_WIDTH : PIPELINE_NODE_HEIGHT;
  const point = (a: number, b: number) => (vertical ? `${b} ${a}` : `${a} ${b}`);
  // Distinct ports keep parallel next/fallback arrowheads visible.
  const port = 24 + (lane % 5) * 22;
  const a = primary(from) + length;
  const b = primary(to);
  const u = secondary(from) + port;
  const v = secondary(to) + port;
  const blocked = nodes.some(
    (node) =>
      node.id !== from.id &&
      node.id !== to.id &&
      primary(node) > primary(from) &&
      primary(node) < primary(to),
  );
  if (b > a && !blocked) {
    const bend = (a + b) / 2 + ((lane % 5) - 2) * 8;
    return `M ${point(a, u)} C ${point(bend, u)}, ${point(bend, v)}, ${point(b, v)}`;
  }
  const outside = Math.max(...nodes.map((node) => secondary(node) + breadth)) + 32 + lane * 18;
  const exit = a + 16 + (lane % 5) * 6;
  const entry = b - 16 - (lane % 5) * 6;
  return `M ${point(a, u)} L ${point(exit, u)} L ${point(exit, outside)} L ${point(entry, outside)} L ${point(entry, v)} L ${point(b, v)}`;
}

export function layoutPipelineDiagram(
  stages: PipelineStage[],
  entryStageIds: string[],
  execution?: PipelineRunTrace | null,
  orientation: PipelineDiagramOrientation = "horizontal",
  density: PipelineDiagramDensity = "standard",
): PipelineDiagram {
  const { columnGap, rowGap } = DENSITY_SPACING[density];
  const byId = new Map(stages.map((stage) => [stage.id, stage]));
  const edges: Array<{ from: string; to: string; kind: PipelineEdgeKind }> = [];
  for (const stage of stages) {
    for (const target of stage.next || []) {
      if (byId.has(target)) edges.push({ from: stage.id, to: target, kind: "next" });
    }
    for (const fallback of FALLBACKS) {
      const target = stage[fallback.key];
      if (typeof target === "string" && target && byId.has(target)) {
        edges.push({ from: stage.id, to: target, kind: fallback.kind });
      }
    }
  }

  const observed = new Map(
    (execution?.stages || []).map((stage, index) => [stage.stage_id, { stage, index }]),
  );
  for (const stage of execution?.stages || []) {
    if (!byId.has(stage.stage_id)) {
      byId.set(stage.stage_id, {
        id: stage.stage_id,
        strategy: stage.strategy_id,
        enabled: true,
        config: {},
        next: [],
      });
    }
  }

  const ids = [...byId.keys()];
  const layer = new Map<string, number>();
  for (const id of entryStageIds) {
    if (byId.has(id)) layer.set(id, 0);
  }
  for (const id of ids) {
    const incoming = edges.some((edge) => edge.to === id);
    if (!incoming && !layer.has(id)) layer.set(id, 0);
  }
  for (let pass = 0; pass < ids.length + 1; pass += 1) {
    let changed = false;
    for (const edge of edges) {
      const source = layer.get(edge.from) ?? 0;
      const next = Math.min(source + 1, ids.length);
      const current = layer.get(edge.to);
      if (current == null || current < next) {
        layer.set(edge.to, next);
        changed = true;
      }
    }
    if (!changed) break;
  }
  let maxLayer = Math.max(0, ...[...layer.values()]);
  for (const id of ids) {
    if (!layer.has(id)) {
      const mark = observed.get(id);
      if (mark && !stages.some((stage) => stage.id === id)) {
        maxLayer += 1;
        layer.set(id, maxLayer);
      } else {
        layer.set(id, 0);
      }
    }
  }

  const columns = new Map<number, string[]>();
  for (const id of ids) {
    const index = layer.get(id) ?? 0;
    const column = columns.get(index) || [];
    column.push(id);
    columns.set(index, column);
  }
  const columnCount = Math.max(1, ...[...columns.keys()].map((index) => index + 1));
  const tallest = Math.max(1, ...[...columns.values()].map((column) => column.length));
  const height = CANVAS_PAD * 2 + tallest * PIPELINE_NODE_HEIGHT + (tallest - 1) * rowGap;
  const width =
    CANVAS_PAD * 2 + columnCount * PIPELINE_NODE_WIDTH + Math.max(0, columnCount - 1) * columnGap;

  const nodes: PipelineGraphNode[] = [];
  for (const [index, column] of columns) {
    const stack = column.length * PIPELINE_NODE_HEIGHT + Math.max(0, column.length - 1) * rowGap;
    const offsetY = CANVAS_PAD + (height - CANVAS_PAD * 2 - stack) / 2;
    column.forEach((id, row) => {
      const stage = byId.get(id)!;
      const mark = observed.get(id);
      const configured = stages.some((item) => item.id === id);
      nodes.push({
        id,
        strategy: stage.strategy,
        enabled: stage.enabled,
        entry: entryStageIds.includes(id),
        x:
          orientation === "horizontal"
            ? CANVAS_PAD + index * (PIPELINE_NODE_WIDTH + columnGap)
            : CANVAS_PAD + row * (PIPELINE_NODE_WIDTH + columnGap),
        y:
          orientation === "horizontal"
            ? offsetY + row * (PIPELINE_NODE_HEIGHT + rowGap)
            : CANVAS_PAD + index * (PIPELINE_NODE_HEIGHT + rowGap),
        executionStatus: execution
          ? mark?.stage.status || (configured ? "not_reached" : null)
          : null,
        presence: !configured ? "observed_only" : execution && !mark ? "not_reached" : "configured",
        elapsedMs: mark?.stage.elapsed_ms ?? null,
        inputCount: mark?.stage.input_count ?? null,
        outputCount: mark?.stage.output_count ?? null,
        fallbackReason: mark?.stage.fallback_reason ?? null,
      });
    });
  }

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const order = new Map((execution?.stages || []).map((stage, index) => [stage.stage_id, index]));
  const drawn: PipelineGraphEdge[] = [];
  edges.forEach((edge, index) => {
    const from = nodeById.get(edge.from);
    const to = nodeById.get(edge.to);
    if (!from || !to) return;
    const sourceOrder = order.get(edge.from);
    const targetOrder = order.get(edge.to);
    const bothRan = sourceOrder != null && targetOrder != null;
    const traversed = execution
      ? edge.kind === "next"
        ? Boolean(bothRan && targetOrder! >= sourceOrder!)
        : Boolean(bothRan && from.fallbackReason)
      : false;
    drawn.push({
      id: `${edge.kind}:${edge.from}:${edge.to}:${index}`,
      ...edge,
      traversed,
      lane: index,
      path: pipelineEdgePath(from, to, index, nodes, orientation),
    });
  });

  if (orientation === "vertical") {
    return {
      nodes,
      edges: drawn,
      width:
        CANVAS_PAD * 2 +
        tallest * PIPELINE_NODE_WIDTH +
        Math.max(0, tallest - 1) * columnGap +
        64 +
        edges.length * 18,
      height:
        CANVAS_PAD * 2 + columnCount * PIPELINE_NODE_HEIGHT + Math.max(0, columnCount - 1) * rowGap,
    };
  }
  return { nodes, edges: drawn, width, height: height + 64 + edges.length * 18 };
}

/* Copyright 2026 Aaron John Schlosser, PhD. */
import { routePipelineEdges } from "./pipelineRouting";
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
  points: Array<{ x: number; y: number }>;
};

export type PipelineGraphNode = {
  id: string;
  strategy: string;
  enabled: boolean;
  entry: boolean;
  x: number;
  y: number;
  width: number;
  height: number;
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

export function layoutPipelineDiagram(
  stages: PipelineStage[],
  entryStageIds: string[],
  execution?: PipelineRunTrace | null,
  orientation: PipelineDiagramOrientation = "horizontal",
  density: PipelineDiagramDensity = "standard",
  measured: Record<string, { width: number; height: number }> = {},
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
  const sizes = new Map(
    ids.map((id) => {
      const ports = Math.max(
        edges.filter((e) => e.from === id).length,
        edges.filter((e) => e.to === id).length,
      );
      return [
        id,
        {
          width: Math.max(
            PIPELINE_NODE_WIDTH,
            measured[id]?.width || 0,
            orientation === "vertical" ? 48 + ports * 18 : 0,
          ),
          height: Math.max(
            PIPELINE_NODE_HEIGHT,
            measured[id]?.height || 0,
            orientation === "horizontal" ? 48 + ports * 18 : 0,
          ),
        },
      ];
    }),
  );
  const nodes: PipelineGraphNode[] = [];
  let primary = CANVAS_PAD;
  for (const [, column] of [...columns].sort((a, b) => a[0] - b[0])) {
    const primarySize = Math.max(
      ...column.map((id) =>
        orientation === "horizontal" ? sizes.get(id)!.width : sizes.get(id)!.height,
      ),
    );
    let secondary = CANVAS_PAD;
    for (const id of column) {
      const stage = byId.get(id)!,
        mark = observed.get(id),
        configured = stages.some((item) => item.id === id);
      const size = sizes.get(id)!;
      nodes.push({
        id,
        strategy: stage.strategy,
        enabled: stage.enabled,
        entry: entryStageIds.includes(id),
        x: orientation === "horizontal" ? primary : secondary,
        y: orientation === "horizontal" ? secondary : primary,
        ...size,
        executionStatus: execution
          ? mark?.stage.status || (configured ? "not_reached" : null)
          : null,
        presence: !configured ? "observed_only" : execution && !mark ? "not_reached" : "configured",
        elapsedMs: mark?.stage.elapsed_ms ?? null,
        inputCount: mark?.stage.input_count ?? null,
        outputCount: mark?.stage.output_count ?? null,
        fallbackReason: mark?.stage.fallback_reason ?? null,
      });
      secondary +=
        (orientation === "horizontal" ? size.height : size.width) +
        (orientation === "horizontal" ? rowGap : columnGap);
    }
    primary += primarySize + (orientation === "horizontal" ? columnGap : rowGap);
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
      path: "",
      points: [],
    });
  });

  const routed = routePipelineEdges(nodes, drawn, orientation);
  const points = [
    ...nodes.flatMap((n) => [
      { x: n.x, y: n.y },
      { x: n.x + n.width, y: n.y + n.height },
    ]),
    ...routed.flatMap((e) => e.points),
  ];
  const dx = CANVAS_PAD - Math.min(CANVAS_PAD, ...points.map((p) => p.x));
  const dy = CANVAS_PAD - Math.min(CANVAS_PAD, ...points.map((p) => p.y));
  for (const node of nodes) {
    node.x += dx;
    node.y += dy;
  }
  for (const edge of routed) {
    edge.points = edge.points.map((p) => ({ x: p.x + dx, y: p.y + dy }));
    edge.path = edge.points.map((p, i) => (i ? "L " : "M ") + p.x + " " + p.y).join(" ");
  }
  return {
    nodes,
    edges: routed,
    width: Math.max(0, ...points.map((p) => p.x)) + dx + CANVAS_PAD,
    height: Math.max(0, ...points.map((p) => p.y)) + dy + CANVAS_PAD,
  };
}

/* Copyright 2026 Aaron John Schlosser, PhD. */
import type {
  PipelineDataType,
  PipelineDefinition,
  PipelinePort,
  PipelineRunInput,
  PipelineStage,
  PipelineStrategy,
  PipelineWiringOption,
  PipelineWiringSource,
} from "../types/pipelines";

/**
 * Pure edits that keep a pipeline's stage inputs coherent.
 *
 * The server is the authority on whether wiring is valid; these helpers only
 * make the edits the editor offers (re-source an input, insert a stage, rename
 * or remove a stage) without leaving a binding that points at something that
 * no longer exists.
 */

export type BindingChoice =
  | { kind: "stage"; stage: string; output: string }
  | { kind: "run_input"; name: string }
  | { kind: "constant"; value: number };

const FALLBACK_KEYS = ["on_empty", "on_unavailable", "on_timeout", "on_error"] as const;

export function typesCompatible(source: string, target: string): boolean {
  return source === target || source === "any" || target === "any";
}

export function primaryInput(strategy: PipelineStrategy): PipelinePort {
  return (
    strategy.inputs?.[0] ?? {
      name: "input",
      data_type: strategy.input_type as PipelineDataType,
      required: strategy.input_type !== "any",
      multiple: false,
    }
  );
}

export function primaryOutput(strategy: PipelineStrategy): PipelinePort {
  return (
    strategy.outputs?.[0] ?? {
      name: "output",
      data_type: strategy.output_type as PipelineDataType,
      required: true,
      multiple: false,
    }
  );
}

export function optionKey(option: PipelineWiringOption | PipelineWiringSource): string {
  if (option.kind === "constant") return "constant";
  return option.kind === "run_input"
    ? `run:${option.name}`
    : `stage:${option.stage ?? ""}:${option.output ?? ""}`;
}

export function choiceKey(choice: BindingChoice): string {
  if (choice.kind === "constant") return "constant";
  return choice.kind === "run_input"
    ? `run:${choice.name}`
    : `stage:${choice.stage}:${choice.output}`;
}

export function choiceFromKey(
  key: string,
  options: PipelineWiringOption[],
): { choice: BindingChoice; option: PipelineWiringOption } | null {
  const option = options.find((item) => optionKey(item) === key);
  if (!option) return null;
  if (option.kind === "run_input") {
    return { choice: { kind: "run_input", name: option.name ?? "" }, option };
  }
  return {
    choice: { kind: "stage", stage: option.stage ?? "", output: option.output ?? "" },
    option,
  };
}

function clone(pipeline: PipelineDefinition): PipelineDefinition {
  return JSON.parse(JSON.stringify(pipeline)) as PipelineDefinition;
}

function targetsOf(stage: PipelineStage): string[] {
  const values = [stage.next, ...FALLBACK_KEYS.map((key) => stage[key])].flat();
  return values.filter((value): value is string => typeof value === "string" && value !== "");
}

/** True when ``to`` can be reached from ``from`` along any edge. */
export function reaches(pipeline: PipelineDefinition, from: string, to: string): boolean {
  const byId = new Map(pipeline.stages.map((stage) => [stage.id, stage]));
  const seen = new Set<string>();
  const queue = [from];
  while (queue.length) {
    const current = queue.pop() as string;
    if (seen.has(current)) continue;
    seen.add(current);
    const stage = byId.get(current);
    if (!stage) continue;
    for (const target of targetsOf(stage)) {
      if (target === to) return true;
      queue.push(target);
    }
  }
  return false;
}

/**
 * Re-source one stage input. ``null`` returns the port to automatic wiring.
 * Choosing a stage that does not yet run before the consumer adds the `next`
 * edge that makes it so; that is refused (null) when it would form a cycle.
 */
export function setInputBinding(
  pipeline: PipelineDefinition,
  stageId: string,
  port: string,
  choice: BindingChoice | null,
): PipelineDefinition | null {
  return bindInput(pipeline, stageId, port, choice)?.pipeline ?? null;
}

/** An edge added only so a bound producer runs before its consumer. */
export interface OrderingEdge {
  from: string;
  to: string;
}

/** ``setInputBinding`` that also reports the ordering edge it added, if any. */
export function bindInput(
  pipeline: PipelineDefinition,
  stageId: string,
  port: string,
  choice: BindingChoice | null,
): { pipeline: PipelineDefinition; added: OrderingEdge | null } | null {
  let added: OrderingEdge | null = null;
  const next = clone(pipeline);
  const stage = next.stages.find((item) => item.id === stageId);
  if (!stage) return null;
  const inputs = { ...(stage.inputs ?? {}) };

  if (choice === null) {
    delete inputs[port];
  } else if (choice.kind === "constant") {
    if (!Number.isFinite(choice.value)) return null;
    inputs[port] = [{ source: "constant", value: choice.value }];
  } else if (choice.kind === "run_input") {
    inputs[port] = [{ source: "run_input", name: choice.name }];
  } else {
    if (choice.stage === stageId) return null;
    const producer = next.stages.find((item) => item.id === choice.stage);
    if (!producer) return null;
    if (!reaches(next, choice.stage, stageId)) {
      if (reaches(next, stageId, choice.stage)) return null;
      producer.next = [...new Set([...producer.next, stageId])];
      added = { from: choice.stage, to: stageId };
    }
    inputs[port] = [{ source: "stage", stage: choice.stage, output: choice.output }];
  }

  if (Object.keys(inputs).length) stage.inputs = inputs;
  else delete stage.inputs;
  return { pipeline: next, added };
}

/**
 * Remove ordering edges recorded for ``stageId`` once no binding on it still
 * names their producer. Only edges recorded at binding time are touched, so an
 * edge the author drew themselves is never guessed away.
 */
export function releaseOrderingEdges(
  pipeline: PipelineDefinition,
  tracked: OrderingEdge[],
  stageId: string,
): { pipeline: PipelineDefinition; tracked: OrderingEdge[] } {
  const consumer = pipeline.stages.find((item) => item.id === stageId);
  const stillNamed = new Set(
    Object.values(consumer?.inputs ?? {})
      .flat()
      .map((binding) => (binding.source === "stage" ? binding.stage : null)),
  );
  const release = tracked.filter((edge) => edge.to === stageId && !stillNamed.has(edge.from));
  if (!release.length) return { pipeline, tracked };
  const next = clone(pipeline);
  for (const edge of release) {
    const producer = next.stages.find((item) => item.id === edge.from);
    if (producer) producer.next = producer.next.filter((target) => target !== edge.to);
  }
  return { pipeline: next, tracked: tracked.filter((edge) => !release.includes(edge)) };
}

/** Follow a stage rename through every binding that names it. */
export function renameBindingReferences(
  pipeline: PipelineDefinition,
  from: string,
  to: string,
): void {
  for (const stage of pipeline.stages) {
    for (const bindings of Object.values(stage.inputs ?? {})) {
      for (const binding of bindings) {
        if (binding.source === "stage" && binding.stage === from) binding.stage = to;
      }
    }
  }
}

/** Drop every binding that names a removed stage so none points at nothing. */
export function removeBindingReferences(pipeline: PipelineDefinition, removedId: string): void {
  for (const stage of pipeline.stages) {
    if (!stage.inputs) continue;
    for (const [port, bindings] of Object.entries(stage.inputs)) {
      const kept = bindings.filter(
        (binding) => !(binding.source === "stage" && binding.stage === removedId),
      );
      if (kept.length) stage.inputs[port] = kept;
      else delete stage.inputs[port];
    }
    if (!Object.keys(stage.inputs).length) delete stage.inputs;
  }
}

/** Ports belong to a strategy, so switching strategy discards explicit bindings. */
export function clearStageBindings(stage: PipelineStage): void {
  delete stage.inputs;
}

export type StageFit = {
  fits: boolean;
  /** Why not, as a machine reason the UI turns into words. */
  reason: "none" | "primary_type" | "missing_input";
  needs?: string;
  provides?: string;
};

/** Run inputs by name, for deciding whether a strategy's other inputs can be met. */
function runInputTypes(runInputs: PipelineRunInput[]): Map<string, string> {
  return new Map(runInputs.map((item) => [item.name, item.data_type]));
}

/**
 * Whether ``strategy`` can run right after ``producer`` (or first, when there
 * is none): its first input takes what arrives, and each other required input
 * has a run input of the same name to read from.
 */
export function strategyFit(
  strategy: PipelineStrategy,
  producer: PipelineStrategy | null,
  runInputs: PipelineRunInput[],
): StageFit {
  const ports = strategy.inputs?.length ? strategy.inputs : [primaryInput(strategy)];
  const [first, ...rest] = ports;
  const known = runInputTypes(runInputs);
  const provided = producer
    ? primaryOutput(producer).data_type
    : runInputs.find((item) => typesCompatible(item.data_type, first.data_type))?.data_type;
  if (!provided || !typesCompatible(provided, first.data_type)) {
    return { fits: false, reason: "primary_type", needs: first.data_type, provides: provided };
  }
  for (const port of rest) {
    const available = known.get(port.name);
    if (port.required && (!available || !typesCompatible(available, port.data_type))) {
      return { fits: false, reason: "missing_input", needs: port.name };
    }
  }
  return { fits: true, reason: "none", provides: provided, needs: first.data_type };
}

function uniqueStageId(pipeline: PipelineDefinition, strategyId: string): string {
  const stem =
    strategyId
      .split(".")
      .pop()
      ?.replace(/[^a-z0-9_]+/gi, "_") || "stage";
  const used = new Set(pipeline.stages.map((stage) => stage.id));
  let id = stem;
  let suffix = 2;
  while (used.has(id)) id = `${stem}_${suffix++}`;
  return id;
}

export type InsertMode = "after" | "between" | "entry";

/**
 * Add a stage and connect it. ``after`` branches a new next-step off the anchor,
 * ``between`` splices it into the anchor's existing flow, ``entry`` starts a new
 * path from the workflow's own inputs.
 */
export function insertStage(
  pipeline: PipelineDefinition,
  strategyId: string,
  anchorId: string | null,
  mode: InsertMode,
): { pipeline: PipelineDefinition; stageId: string } {
  const next = clone(pipeline);
  const id = uniqueStageId(next, strategyId);
  const stage: PipelineStage = {
    id,
    strategy: strategyId,
    enabled: true,
    config: {},
    next: [],
    on_empty: null,
    on_unavailable: null,
    on_timeout: null,
    on_error: null,
  };
  const anchor = anchorId ? next.stages.find((item) => item.id === anchorId) : undefined;
  if (mode === "entry" || !anchor) {
    next.entry_stage_ids = [...new Set([...next.entry_stage_ids, id])];
  } else if (mode === "between") {
    stage.next = [...anchor.next];
    anchor.next = [id];
  } else {
    anchor.next = [...new Set([...anchor.next, id])];
  }
  next.stages.push(stage);
  return { pipeline: next, stageId: id };
}

/** Number of inputs the server could not wire for a stage. */
export function unsatisfiedInputs(inputs: Array<{ status: string }> | undefined): number {
  return (inputs ?? []).filter((row) => row.status === "unbound" || row.status === "mismatch")
    .length;
}

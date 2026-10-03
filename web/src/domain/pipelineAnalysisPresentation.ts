/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import type {
  PipelineAnalysis,
  PipelineLatencyFigure,
  PipelineStageLatency,
  PipelineWiringSource,
} from "../types/pipelines";
import { pipelineDataTypeLabel, type PipelineTranslator } from "./pipelinePresentation";

/** Short duration for tables and node badges: "—", "42 ms", "1.8 s", "2 min 5 s". */
export function formatMs(value: number | null | undefined, t: PipelineTranslator): string {
  if (value == null) return "—";
  if (value < 1000) return `${Math.round(value)} ${t("pipelines.duration_milliseconds", "ms")}`;
  const seconds = value / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(seconds < 10 ? 2 : 1)} ${t("pipelines.duration_seconds", "s")}`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds - minutes * 60);
  return `${minutes} ${t("pipelines.duration_minutes", "min")} ${rest} ${t("pipelines.duration_seconds", "s")}`;
}

/** A glyph that tells data types apart without relying on colour. */
export function dataTypeGlyph(type: string): string {
  const glyphs: Record<string, string> = {
    query: "?",
    candidate_set: "☰",
    context_packet: "▣",
    model_output: "✎",
    evaluation: "✓",
    number: "#",
    any: "∗",
  };
  return glyphs[type] ?? "∗";
}

export function dataTypeTone(type: string): number {
  const order = ["query", "candidate_set", "context_packet", "model_output", "evaluation", "any"];
  const index = order.indexOf(type);
  return index === -1 ? 6 : index + 1;
}

export function latencyBasisLabel(basis: PipelineStageLatency["basis"], t: PipelineTranslator) {
  const labels: Record<PipelineStageLatency["basis"], string> = {
    this_pipeline: t("pipelines.latency_basis_this_pipeline", "This exact pipeline"),
    same_stage: t("pipelines.latency_basis_same_stage", "Same stage, other versions"),
    strategy: t("pipelines.latency_basis_strategy", "This strategy, any pipeline"),
    none: t("pipelines.latency_basis_none", "No recorded runs"),
  };
  return labels[basis];
}

export function sampleLabel(figure: PipelineLatencyFigure | undefined, t: PipelineTranslator) {
  const count = figure?.samples ?? 0;
  if (!count) return t("pipelines.latency_no_samples", "no samples");
  const text = `n=${count}`;
  return figure?.reliable ? text : `${text} · ${t("pipelines.latency_thin", "thin")}`;
}

export function sourceText(source: PipelineWiringSource, t: PipelineTranslator): string {
  if (source.kind === "constant") {
    return `${t("pipelines.ports_fixed_value", "Fixed value")} ${source.value ?? ""}`;
  }
  if (source.kind === "run_input") {
    return `${t("pipelines.ports_run_input", "Workflow input")} “${source.name}”`;
  }
  if (source.kind === "stage_input") {
    return `${source.stage} ${t("pipelines.ports_fallback_input", "(its input, on fallback)")}`;
  }
  return `${source.stage} → ${source.output}`;
}

export type StageBadge = { text: string; tone: "neutral" | "warn" | "danger" };
export type DiagramLens = "structure" | "latency" | "complexity";

/** One short badge per stage for the diagram lens, or none for the plain structure view. */
export function lensBadges(
  analysis: PipelineAnalysis | null,
  lens: DiagramLens,
  t: PipelineTranslator,
): Record<string, StageBadge> {
  const badges: Record<string, StageBadge> = {};
  if (!analysis) return badges;
  if (lens === "latency") {
    for (const row of analysis.latency.stages) {
      badges[row.stage_id] =
        row.samples > 0
          ? {
              text: `${row.conditional ? "↪ " : "≈ "}${formatMs(row.p50_ms, t)}`,
              tone: row.basis === "strategy" || !row.reliable ? "warn" : "neutral",
            }
          : { text: t("pipelines.latency_unknown_short", "no data"), tone: "warn" };
    }
  } else if (lens === "complexity") {
    for (const row of analysis.complexity.stages) {
      badges[row.stage_id] = { text: row.time, tone: row.scales_with_scope ? "warn" : "neutral" };
    }
  }
  return badges;
}

/** Stage IDs whose inputs the server could not wire, for flagging them in the diagram. */
export function stagesWithWiringProblems(analysis: PipelineAnalysis | null): Set<string> {
  const flagged = new Set<string>();
  for (const [stageId, wiring] of Object.entries(analysis?.wiring.stages ?? {})) {
    if (wiring.inputs.some((row) => row.status === "unbound" || row.status === "mismatch")) {
      flagged.add(stageId);
    }
  }
  return flagged;
}

export function typeLabel(type: string, t: PipelineTranslator) {
  return pipelineDataTypeLabel(type, t);
}

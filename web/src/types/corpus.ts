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

export interface CorpusSegmentationTelemetry {
  candidateCount?: number;
  deterministicSplits?: number;
  deterministicKeeps?: number;
  llmAdjudications?: number;
  llmBatchCalls?: number;
  llmSplits?: number;
  llmKeeps?: number;
  provisionalSplits?: number;
  sizeOptimizedSplits?: number;
  absoluteSafetySplits?: number;
  budgetSkipped?: number;
  classifierFailures?: number;
  reviewCount?: number;
}

export interface RecordSizingPolicy {
  preferred_record_chars: number;
  record_length_tolerance: number;
  long_record_chars: number;
  absolute_record_chars: number;
}

export interface CorpusTopologyPolicy {
  mode: "semantic" | "source_units";
  source_units_per_record: number;
  records_per_page: number | null;
}

export type ReviewQueue =
  | "all"
  | "ready"
  | "issues"
  | "metadata"
  | "topology"
  | "source"
  | "accepted"
  | "rejected";

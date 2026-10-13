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
export type ResearchTurnStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface ResearchThread {
  thread_id: string;
  owner: string;
  title: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  /** Owner-set; pinned threads list first. Optional for payloads from before the migration. */
  pinned_at?: string | null;
  originating_response_record_id: string | null;
}

export interface ResearchThreadSummary extends ResearchThread {
  turn_count: number;
  first_question: string | null;
  last_question: string | null;
  last_status: ResearchTurnStatus | null;
}

export interface ResearchTurn {
  turn_id: string;
  thread_id: string;
  ordinal: number;
  user_question: string;
  user_instructions: string | null;
  status: ResearchTurnStatus;
  job_id: string | null;
  research_run_id: string | null;
  response_record_id: string | null;
  parent_turn_id: string | null;
  contextualized_query: string | null;
  context_selection: unknown;
  error: string | null;
  attempt: number;
  created_at: string;
  updated_at: string;
}

export interface ResearchThreadDetail extends ResearchThread {
  turns: ResearchTurn[];
}

/** One cited EvidenceRef in an export: identity and the run's own citation strings, never passage text. */
export interface ResearchExportReference {
  evidence_id: string | null;
  collection: string | null;
  record_id: string | null;
  record_revision: number | null;
  inline_citation: string | null;
  full_citation: string | null;
  locator: Record<string, string | number>;
}

export interface ResearchExportTurn {
  turn_id: string;
  ordinal: number;
  attempt: number;
  status: ResearchTurnStatus;
  question: string;
  instructions: string | null;
  research_run_id: string | null;
  job_id: string | null;
  answer: string | null;
  answer_available: boolean;
  provider: string | null;
  model: string | null;
  references: ResearchExportReference[];
}

export interface ResearchThreadExport {
  format: string;
  thread: {
    thread_id: string;
    title: string | null;
    created_at: string;
    updated_at: string;
    archived_at: string | null;
  };
  turns: ResearchExportTurn[];
  works_cited: string[];
}

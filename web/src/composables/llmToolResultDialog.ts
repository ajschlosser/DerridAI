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

import { shallowReadonly, shallowRef } from "vue";

export type LlmToolResultBody =
  | { kind: "clean_text"; text: string }
  | { kind: "draft_record"; json: string }
  | { kind: "link_record"; recordId: string; reason: string }
  | {
      kind: "rag_grade";
      question: string;
      cacheError: string;
      /** Escaped by the legacy grade renderer. */
      gradeHtml: string;
    }
  | {
      kind: "rag_grade_batch";
      graded: number;
      failed: number;
      total: number;
      /** Pretty-printed JSON, empty when every response was processed. */
      errorsJson: string;
      errorCount: number;
    }
  | { kind: "raw"; json: string };

export interface LlmToolResultRequest {
  title: string;
  /** "provider · model", already composed. */
  subtitle: string;
  body: LlmToolResultBody;
  /** The one follow-up the task offers, when it offers one. */
  action: { label: string; run: () => void | Promise<void> } | null;
}

const current = shallowRef<LlmToolResultRequest | null>(null);

/** The result of a finished LLM tool job; any follow-up runs after the dialog closes. */
export function openLlmToolResultDialog(request: LlmToolResultRequest) {
  current.value = request;
}

export function closeLlmToolResultDialog() {
  current.value = null;
}

export function useLlmToolResultDialog() {
  return { current: shallowReadonly(current), close: closeLlmToolResultDialog };
}

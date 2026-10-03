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

export interface JobDetailsEvent {
  /** Already formatted. */
  when: string;
  stage: string;
  /** "current/total · detail", already composed. */
  detail: string;
  latest: boolean;
}

export interface JobDetailsRequest {
  title: string;
  subtitle: string;
  facts: { name: string; value: string }[];
  fatalError: string;
  /** Pretty-printed request, API key already removed. */
  requestJson: string;
  events: JobDetailsEvent[];
  resultJson: string;
  /** "cancel" while the job can be cancelled, "cancelling" once it has been asked to stop. */
  cancel: "none" | "cancel" | "cancelling";
  /** Runs after the dialog closes; the forwarder reopens the details when the job was cancelled. */
  onCancel: () => void | Promise<void>;
  openResult: { label: string; run: () => void | Promise<void> } | null;
}

const current = shallowRef<JobDetailsRequest | null>(null);

/** Details of one background job: facts, request, timeline and result summary. */
export function openJobDetailsDialog(request: JobDetailsRequest) {
  current.value = request;
}

export function closeJobDetailsDialog() {
  current.value = null;
}

export function useJobDetailsDialog() {
  return { current: shallowReadonly(current), close: closeJobDetailsDialog };
}

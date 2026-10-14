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

export interface LlmLauncherProfile {
  id: string;
  /** Display name, already resolved by the caller. */
  label: string;
  type: string;
  model: string;
  autoModel: boolean;
  maxConcurrentRequests: number;
  numCtx: number | string;
  think: string;
  numPredict: number | string;
  temperature: number | string;
  topP: number | string;
  seed: number | string;
  extraOptions: string;
  available: boolean;
  statusError: string;
}
export type LlmLauncherRunMode = "background" | "foreground";
/** Raw form values; the caller parses and validates them. */
export interface LlmLauncherSubmission {
  profileId: string;
  runMode: LlmLauncherRunMode;
  model: string;
  numCtx: string;
  think: string;
  numPredict: string;
  temperature: string;
  topP: string;
  seed: string;
  extraOptions: string;
}
export interface LlmTaskLauncherRequest {
  title: string;
  description: string;
  contextText: string;
  /** The model that generated the answer being graded; choosing it again earns a self-grading warning. */
  generationProvider: string | null;
  generationModel: string | null;
  profiles: LlmLauncherProfile[];
  profileId: string;
  runMode: LlmLauncherRunMode;
  /** Offered run modes; one entry fixes the mode (researchers and cache-wide grading). */
  runModes: LlmLauncherRunMode[];
  canManageProviders: boolean;
  /** Warms the model and resolves the message to show. */
  warm: (profileId: string) => Promise<string>;
  manageProviders: () => void;
  /** Validates and starts the task; resolves true when the dialog may close. */
  run: (submission: LlmLauncherSubmission) => Promise<boolean>;
}

const current = shallowRef<LlmTaskLauncherRequest | null>(null);

/** Choose a provider profile and generation settings, then run an LLM task in the foreground or as a job. */
export function openLlmTaskLauncherDialog(request: LlmTaskLauncherRequest) {
  current.value = request;
}

export function closeLlmTaskLauncherDialog() {
  current.value = null;
}

export function useLlmTaskLauncherDialog() {
  return { current: shallowReadonly(current), close: closeLlmTaskLauncherDialog };
}

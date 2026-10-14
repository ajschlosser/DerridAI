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
import type { ProviderProfile } from "../api/system";

export interface WorkMetadataLlmScope {
  work: string;
  sourceTypeLabel: string;
}
export interface WorkMetadataLlmRequest {
  /** Number of work/source-type groups the lookup covers. */
  scopeCount: number;
  /** "2 Book · 1 Article": how many groups of each source type. */
  scopeSummary: string;
  /** The first few groups, shown as a sample; the rest are only counted. */
  sample: WorkMetadataLlmScope[];
  profiles: ProviderProfile[];
  defaultProfileId: string;
  /** Starts the background lookup. A rejection keeps the dialog open and is shown to the user. */
  start: (profileId: string) => Promise<void>;
  /** Confirms leaving for the provider settings. Resolves `true` when the dialog should close. */
  manageProviders: () => Promise<boolean>;
}

const current = shallowRef<WorkMetadataLlmRequest | null>(null);

/** Ask which provider profile should look up metadata for the chosen works. */
export function openWorkMetadataLlmDialog(request: WorkMetadataLlmRequest) {
  current.value = request;
}

export function closeWorkMetadataLlmDialog() {
  current.value = null;
}

export function useWorkMetadataLlmDialog() {
  return { current: shallowReadonly(current), close: closeWorkMetadataLlmDialog };
}

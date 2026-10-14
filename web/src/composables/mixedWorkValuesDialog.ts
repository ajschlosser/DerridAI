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

import { readonly, shallowRef } from "vue";

export interface MixedWorkValue {
  /** Display-ready value; `null` means the value is unset. */
  text: string | null;
  files: string[];
  count: number;
}
export interface MixedWorkValuesRequest {
  work: string;
  fieldLabel: string;
  recordCount: number;
  values: MixedWorkValue[];
}

const current = shallowRef<MixedWorkValuesRequest | null>(null);

/** Show the variants of one metadata field across a work's records. */
export function openMixedWorkValuesDialog(request: MixedWorkValuesRequest) {
  current.value = request;
}

export function closeMixedWorkValuesDialog() {
  current.value = null;
}

export function useMixedWorkValuesDialog() {
  return { current: readonly(current), close: closeMixedWorkValuesDialog };
}

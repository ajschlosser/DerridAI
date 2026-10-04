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

import {
  setTranslationDictionary as setTranslationDictionaryCompat,
  tr as trCompat,
  trf as trfCompat,
} from "./legacyCompat.js";
import { state } from "./sharedUrlState";

// Translation lookups over the shared `translations` slice, usable without the legacy runtime. The runtime's own
// `tr`/`trf` read the same slice.
export const tr = (key: string, fallback = ""): string => trCompat(state, key, fallback);
export const trf = (
  key: string,
  fallback?: string | Record<string, unknown>,
  values: Record<string, unknown> = {},
): string => trfCompat(state, key, fallback, values);

export const setTranslationDictionary = (
  locale: string,
  dictionary: Record<string, unknown> = {},
  base: Record<string, unknown> = {},
  info: Record<string, unknown> = {},
) => setTranslationDictionaryCompat(state, locale, dictionary, base, info);

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

import { englishDefault } from "./englishDefault";

export type Tr = (key: string, fallback?: string) => string;
export type Values = Record<string, unknown>;
export type Trf = (key: string, fallbackOrValues?: string | Values, values?: Values) => string;
type RawTrf = (key: string, fallback: string, values?: Values) => string;

/**
 * Bind tr/trf so call sites pass a key (and interpolations). English comes from
 * enUsDefaults.json, exported from api/app/locales/en_us.py.
 */
export function bindCopy(tr: Tr, trf: RawTrf) {
  const t = (key: string, fallback?: string) => tr(key, fallback || englishDefault(key) || key);
  const tf = (key: string, fallbackOrValues?: string | Values, values?: Values) => {
    if (fallbackOrValues && typeof fallbackOrValues === "object") {
      return trf(key, englishDefault(key) || key, fallbackOrValues);
    }
    return trf(
      key,
      (typeof fallbackOrValues === "string" && fallbackOrValues) || englishDefault(key) || key,
      values || {},
    );
  };
  return { t, tf, tr: t, trf: tf };
}

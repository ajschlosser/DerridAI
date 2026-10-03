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

import enUsDefaults from "./enUsDefaults.json";

const EN_US_DEFAULTS = enUsDefaults as Record<string, string>;

export const COMMON_KEY_ALIASES: Record<string, string> = {
  "runtime.apply": "common.apply",
  "runtime.cancel": "common.cancel",
  "pdf_corpus.cancel": "common.cancel",
  "runtime.clear": "common.clear",
  "runtime.close": "common.close",
  "runtime.delete": "common.delete",
  "users.delete": "common.delete",
  "runtime.next": "common.next",
  "runtime.no": "common.no",
  "runtime.previous": "common.previous",
  "runtime.yes": "common.yes",
  "ui.apply": "common.apply",
  "ui.cancel": "common.cancel",
  "ui.clear": "common.clear",
  "ui.close": "common.close",
  "ui.delete": "common.delete",
  "ui.next": "common.next",
  "ui.no": "common.no",
  "ui.previous": "common.previous",
  "ui.yes": "common.yes",
};

/** Canonical English for a UI key. Source of truth is api/app/locales/en_us.py. */
export function englishDefault(key: string): string {
  return EN_US_DEFAULTS[key] || EN_US_DEFAULTS[COMMON_KEY_ALIASES[key]] || "";
}

export { EN_US_DEFAULTS };

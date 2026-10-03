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

/**
 * Parse api/app/locales/en_us.py into a {key: value} map.
 * Adjacent Python string literals are concatenated, matching the locale module.
 */
export function parseEnUsPy(text) {
  const start = text.indexOf("{");
  if (start < 0) throw new Error("EN_US dict not found");
  const body = text.slice(start);
  const map = {};
  const keyRe = /'((?:\\'|[^'])*)'\s*:/g;
  let match;
  while ((match = keyRe.exec(body))) {
    const key = match[1].replace(/\\'/g, "'");
    let i = keyRe.lastIndex;
    const parts = [];
    // A long value may be wrapped in parentheses: 'key': ('first part ' 'second part').
    while (i < body.length && /[\s(]/.test(body[i])) i += 1;
    for (;;) {
      while (i < body.length && /\s/.test(body[i])) i += 1;
      const quote = body[i];
      if (quote !== "'" && quote !== '"') break;
      i += 1;
      let value = "";
      while (i < body.length) {
        if (body[i] === "\\" && i + 1 < body.length) {
          const next = body[i + 1];
          value += next === "n" ? "\n" : next === "t" ? "\t" : next;
          i += 2;
          continue;
        }
        if (body[i] === quote) {
          i += 1;
          break;
        }
        value += body[i];
        i += 1;
      }
      parts.push(value);
    }
    while (i < body.length && /[\s)]/.test(body[i])) i += 1;
    map[key] = parts.join("");
    keyRe.lastIndex = i;
  }
  return map;
}

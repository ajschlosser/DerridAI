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

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

/**
 * The global stylesheet as the browser sees it: src/style.css with each `@import "./x.css";`
 * replaced by that file's contents, in import order (which is the cascade order).
 */
export function readGlobalCss(entry = "src/style.css"): string {
  const path = resolve(process.cwd(), entry);
  return readFileSync(path, "utf8").replace(/^@import "([^"]+)";$/gm, (_m, rel: string) =>
    readGlobalCss(resolve(dirname(path), rel)),
  );
}

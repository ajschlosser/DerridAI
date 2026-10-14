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

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parseEnUsPy } from "./parse-en-us-locale.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = fs.readFileSync(path.join(root, "api/app/locales/en_us.py"), "utf8");
const map = parseEnUsPy(source);
const keys = Object.keys(map);
if (keys.length < 3000) throw new Error(`parsed too few keys: ${keys.length}`);
const out = path.join(root, "web/src/i18n/enUsDefaults.json");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, `${JSON.stringify(map, null, 2)}\n`);
console.log(`wrote ${keys.length} keys to ${path.relative(root, out)}`);

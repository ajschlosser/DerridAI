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

import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

export const DERRIDAI_LICENSE_HEADER = `/*
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
 */`;

const LEGACY_HEADERS = [
  "/* Copyright 2026 Aaron John Schlosser, PhD. */",
  "/* Copyright 2026 Aaron John Schlosser, PhD */",
];

export async function applyCopyrightHeader(path) {
  let text = await readFile(path, "utf8");
  if (text.startsWith(DERRIDAI_LICENSE_HEADER)) return false;

  const leadingWhitespace = text.length - text.trimStart().length;
  const trimmed = text.slice(leadingWhitespace);
  const legacy = LEGACY_HEADERS.find((candidate) => trimmed.startsWith(candidate));
  if (legacy) {
    text = trimmed.slice(legacy.length).replace(/^\s+/, "");
  } else {
    text = text.replace(/^\s+/, "");
  }

  await writeFile(path, `${DERRIDAI_LICENSE_HEADER}\n\n${text}`, "utf8");
  return true;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  for (const path of process.argv.slice(2)) {
    await applyCopyrightHeader(path);
  }
}

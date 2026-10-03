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

import type { WikisourceHit } from "../../../api/corpus";

/** Wikisource hits grouped by work: a chapter (Work/Chapter I) offers its whole work first. */
export interface WorkGroup {
  key: string;
  work: string;
  workUrl: string;
  parts: WikisourceHit[];
  snippet: string;
  words: number;
  isWorkPage: boolean;
}

function workUrl(hit: WikisourceHit, work: string) {
  try {
    return `${new URL(hit.url).origin}/wiki/${encodeURIComponent(work.replaceAll(" ", "_"))}`;
  } catch {
    return hit.url;
  }
}

export function groupWikisourceHits(hits: WikisourceHit[]): WorkGroup[] {
  const groups = new Map<string, WorkGroup>();
  for (const hit of hits) {
    const work = hit.title.split("/")[0].trim() || hit.title;
    const group = groups.get(work) || {
      key: work,
      work,
      workUrl: workUrl(hit, work),
      parts: [],
      snippet: "",
      words: 0,
      isWorkPage: false,
    };
    if (hit.title === work) group.isWorkPage = true;
    else group.parts.push(hit);
    group.snippet ||= hit.snippet;
    group.words += Number(hit.word_count || 0);
    groups.set(work, group);
  }
  return [...groups.values()];
}

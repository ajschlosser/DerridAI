// Copyright 2026 Aaron John Schlosser, PhD.
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

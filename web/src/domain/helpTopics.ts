/* Copyright 2026 Aaron John Schlosser, PhD. */
/**
 * Help Center structure. Text lives in the locale files under
 * `help.section.<id>` and `help.q.<id>.{question,answer,impact}`, so English and
 * French stay in parity; this file only orders topics and says who may see them.
 */
export interface HelpSection {
  id: string;
  /** Corpus-review topics describe administrator-only workflows. */
  adminOnly?: boolean;
  questions: string[];
}

export const HELP_SECTIONS: HelpSection[] = [
  { id: "basics", questions: ["what_is", "authoritative", "citations"] },
  {
    id: "review",
    adminOnly: true,
    questions: [
      "confirm_value",
      "evidence",
      "no_value",
      "save_all",
      "second_opinion",
      "precedents_panel",
      "research_claims_panel",
      "accept_record",
    ],
  },
  { id: "memory", adminOnly: true, questions: ["retrieval_policy", "agree_on", "autofill"] },
  {
    id: "research",
    questions: ["cached_responses", "cached_provenance", "validate_claims", "grading"],
  },
];

export interface HelpEntry {
  id: string;
  question: string;
  answer: string;
  impact: string;
}

/** Sections visible to this user, with questions filtered by a free-text query. */
export function visibleHelp(
  isAdmin: boolean,
  query: string,
  t: (key: string) => string,
): Array<{ id: string; title: string; entries: HelpEntry[] }> {
  const needle = query.trim().toLocaleLowerCase();
  return HELP_SECTIONS.filter((section) => isAdmin || !section.adminOnly)
    .map((section) => ({
      id: section.id,
      title: t(`help.section.${section.id}`),
      entries: section.questions
        .map((id) => ({
          id,
          question: t(`help.q.${id}.question`),
          answer: t(`help.q.${id}.answer`),
          impact: t(`help.q.${id}.impact`),
        }))
        .filter(
          (entry) =>
            !needle ||
            [entry.question, entry.answer, entry.impact].some((text) =>
              text.toLocaleLowerCase().includes(needle),
            ),
        ),
    }))
    .filter((section) => section.entries.length);
}

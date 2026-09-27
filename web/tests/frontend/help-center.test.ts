// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import enUsDefaults from "../../src/i18n/enUsDefaults.json";
import { HELP_SECTIONS, visibleHelp } from "../../src/domain/helpTopics";

const copy = enUsDefaults as Record<string, string>;
const t = (key: string) => copy[key] ?? key;

describe("Help Center", () => {
  it("has English copy for every section, question, answer, and impact", () => {
    const keys = HELP_SECTIONS.flatMap((section) => [
      `help.section.${section.id}`,
      ...section.questions.flatMap((id) =>
        ["question", "answer", "impact"].map((part) => `help.q.${id}.${part}`),
      ),
    ]);
    expect(keys.filter((key) => !copy[key])).toEqual([]);
  });

  it("hides administrator-only workflows from researchers", () => {
    const researcher = visibleHelp(false, "", t).map((section) => section.id);
    const admin = visibleHelp(true, "", t).map((section) => section.id);
    expect(researcher).not.toContain("review");
    expect(admin).toContain("review");
  });

  it("searches questions, answers, and downstream impact", () => {
    const hits = visibleHelp(true, "blind second opinion", t).flatMap((section) =>
      section.entries.map((entry) => entry.id),
    );
    expect(hits).toContain("second_opinion");
    expect(visibleHelp(true, "zzz-no-such-topic", t)).toEqual([]);
  });
});

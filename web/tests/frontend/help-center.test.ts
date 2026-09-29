// Copyright 2026 Aaron John Schlosser, PhD.
import { describe, expect, it } from "vitest";
import enUsDefaults from "../../src/i18n/enUsDefaults.json";
import {
  HELP_GLOSSARY,
  HELP_PAGE_GUIDES,
  HELP_SECTIONS,
  visibleGlossary,
  visibleHelp,
  visiblePageGuides,
} from "../../src/domain/helpTopics";
import { APP_ROUTES } from "../../src/router";

const copy = enUsDefaults as Record<string, string>;
const t = (key: string, fallback?: string) => copy[key] ?? fallback ?? key;

describe("Help Center", () => {
  it("has English copy for every question, page guide, and glossary term", () => {
    const questionKeys = HELP_SECTIONS.flatMap((section) => [
      `help.section.${section.id}`,
      ...section.questions.flatMap((id) =>
        ["question", "answer", "impact"].map((part) => `help.q.${id}.${part}`),
      ),
    ]);
    const pageKeys = HELP_PAGE_GUIDES.flatMap((guide) =>
      ["title", "summary", "tasks", "impact"].map((part) => `help.page.${guide.id}.${part}`),
    );
    const glossaryKeys = HELP_GLOSSARY.flatMap((entry) =>
      ["term", "definition", "practical"].map((part) => `help.glossary.${entry.id}.${part}`),
    );
    expect([...questionKeys, ...pageKeys, ...glossaryKeys].filter((key) => !copy[key])).toEqual([]);
  });

  it("keeps a guide for every route that renders an application page", () => {
    const renderedRouteNames = APP_ROUTES.filter((route) => route.component)
      .map((route) => String(route.name))
      .sort();
    const guideRouteNames = HELP_PAGE_GUIDES.map((guide) => guide.routeName).sort();
    expect(guideRouteNames).toEqual(renderedRouteNames);
  });

  it("hides administrator-only workflows from researchers", () => {
    const researcherQuestions = visibleHelp(false, "", t).map((section) => section.id);
    const adminQuestions = visibleHelp(true, "", t).map((section) => section.id);
    expect(researcherQuestions).not.toContain("review");
    expect(adminQuestions).toContain("review");

    const canResearch = (capability: string) =>
      new Set([
        "page.dashboard",
        "page.search",
        "page.research",
        "page.works",
        "page.record",
        "page.annotations",
        "page.semantic_map",
        "page.compare",
        "page.vector",
        "page.settings",
      ]).has(capability);
    const researcherPages = visiblePageGuides(false, canResearch, "", t).map((guide) => guide.id);
    const adminPages = visiblePageGuides(true, () => true, "", t).map((guide) => guide.id);
    expect(researcherPages).toContain("research");
    expect(researcherPages).not.toContain("corpus_builder");
    expect(researcherPages).not.toContain("providers");
    expect(adminPages).toContain("corpus_builder");
    expect(adminPages).toContain("providers");
  });

  it("searches page guides and workflow questions in plain language", () => {
    const questionHits = visibleHelp(true, "blind second opinion", t).flatMap((section) =>
      section.entries.map((entry) => entry.id),
    );
    expect(questionHits).toContain("second_opinion");

    const pageHits = visiblePageGuides(true, () => true, "build a corpus", t).map(
      (guide) => guide.id,
    );
    expect(pageHits).toContain("corpus_builder");

    expect(visibleHelp(true, "zzz-no-such-topic", t)).toEqual([]);
    expect(visiblePageGuides(true, () => true, "zzz-no-such-topic", t)).toEqual([]);
  });

  it("searches glossary definitions, aliases, and parameter categories", () => {
    expect(visibleGlossary("cross-encoder", "all", t).map((entry) => entry.id)).toContain(
      "cross_encoder",
    );
    expect(visibleGlossary("nucleus sampling", "all", t).map((entry) => entry.id)).toContain(
      "top_p",
    );
    const parameters = visibleGlossary("", "parameters", t);
    expect(parameters.length).toBeGreaterThan(5);
    expect(parameters.every((entry) => entry.category === "parameters")).toBe(true);
    expect(parameters.map((entry) => entry.id)).toContain("fetch_k");
    expect(parameters.map((entry) => entry.id)).toContain("mmr_lambda");
  });
});

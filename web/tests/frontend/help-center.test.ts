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
      ...section.questions.flatMap((question) => [
        `help.q.${question.id}.question`,
        `help.q.${question.id}.answer`,
        ...(question.showImpact ? [`help.q.${question.id}.impact`] : []),
      ]),
    ]);
    const pageKeys = HELP_PAGE_GUIDES.flatMap((guide) => [
      `help.page.${guide.id}.title`,
      `help.page.${guide.id}.summary`,
      `help.page.${guide.id}.tasks`,
      ...(guide.showImpact ? [`help.page.${guide.id}.impact`] : []),
    ]);
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

  it("offers a substantial workflow FAQ without exposing admin-only guidance to researchers", () => {
    const questionCount = HELP_SECTIONS.reduce(
      (total, section) => total + section.questions.length,
      0,
    );
    expect(questionCount).toBeGreaterThanOrEqual(30);

    const commonIds = visibleHelp(false, "", t).flatMap((section) =>
      section.entries.map((entry) => entry.id),
    );
    expect(commonIds).toContain("search_vs_research");
    expect(commonIds).toContain("retrieval_modes");
    expect(commonIds).toContain("slow_run");
    expect(commonIds).not.toContain("needs_review");

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

  it("shows downstream effects only for actions that actually have them", () => {
    const common = visibleHelp(false, "", t).flatMap((section) => section.entries);
    expect(common.find((entry) => entry.id === "search_vs_research")?.impact).toBeUndefined();
    expect(common.find((entry) => entry.id === "select_evidence")?.impact).toBeTruthy();

    const guides = visiblePageGuides(true, () => true, "", t);
    expect(guides.find((guide) => guide.id === "dashboard")?.impact).toBeUndefined();
    expect(guides.find((guide) => guide.id === "research")?.impact).toBeTruthy();
  });

  it("searches page guides and workflow questions in plain language", () => {
    const questionHits = visibleHelp(true, "blind second opinion", t).flatMap((section) =>
      section.entries.map((entry) => entry.id),
    );
    expect(questionHits).toContain("second_opinion");
    expect(
      visibleHelp(true, "confidence not reported", t).flatMap((section) =>
        section.entries.map((entry) => entry.id),
      ),
    ).toContain("confidence_not_reported");

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

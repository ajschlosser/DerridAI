// Copyright 2026 Aaron John Schlosser, PhD.
import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { serveBuiltStorybook } from "./support/built-app";
import AxeBuilder from "@axe-core/playwright";

// Every Corpus Builder story, in light and in dark, against WCAG 2.0 to 2.2 A and AA. One test
// per theme so the two run in parallel; new stories are picked up from Storybook's index.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const isCorpusStory = (id: string) =>
  id.startsWith("corpus") || id.startsWith("metadata-enrichment");

async function scan(page: Page) {
  // Storybook's a11y addon runs axe as each story loads; wait out its run rather than racing it.
  for (let attempt = 0; ; attempt++) {
    try {
      return await new AxeBuilder({ page }).withTags(TAGS).analyze();
    } catch (error) {
      if (attempt >= 10 || !String(error).includes("already running")) throw error;
      await page.waitForTimeout(400);
    }
  }
}

for (const scheme of ["light", "dark"] as const) {
  test(`every Corpus Builder story is WCAG 2.2 AA clean in ${scheme} mode`, async ({
    browser,
    baseURL,
  }, testInfo) => {
    test.skip(
      testInfo.project.name !== "chromium-desktop",
      "The story sweep runs once, at desktop width.",
    );
    test.setTimeout(600_000);
    const index = process.env.CORPUS_OFFLINE_APP==='1' ? JSON.parse(readFileSync("storybook-static/index.json","utf8")) : await (await fetch(`${baseURL}/index.json`)).json();
    const ids = Object.entries<{ type: string }>(index.entries)
      .filter(([id, entry]) => entry.type === "story" && isCorpusStory(id))
      .map(([id]) => id);
    expect(ids.length, "the sweep found no Corpus Builder stories").toBeGreaterThan(100);

    const context = await browser.newContext({ colorScheme: scheme, reducedMotion: "reduce" });
    const page = await context.newPage();
    if(process.env.CORPUS_OFFLINE_APP==='1')await serveBuiltStorybook(page,baseURL!);
    const failures: Record<string, unknown> = {};
    for (const id of ids) {
      await page.goto(`${baseURL}/iframe.html?id=${id}&viewMode=story`);
      await page.evaluate((s) => {
        document.documentElement.dataset.colorScheme = s;
      }, scheme);
      await expect(page.locator("body"), `${id} rendered`).toHaveClass(/sb-show-main/);
      await page.waitForTimeout(500);
      const { violations } = await scan(page);
      if (violations.length) {
        failures[id] = violations.map((v) => ({
          rule: v.id,
          nodes: v.nodes.slice(0, 2).map((n) => ({
            target: n.target.join(" "),
            why: n.failureSummary ?? n.any[0]?.message ?? n.all[0]?.message,
          })),
        }));
      }
    }
    await context.close();
    await testInfo.attach("theme-sweep-summary",{body:JSON.stringify({scheme,storyCount:ids.length,failures},null,2),contentType:"application/json"});
    expect(failures, JSON.stringify(failures, null, 2)).toEqual({});
  });
}

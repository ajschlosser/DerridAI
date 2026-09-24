import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Every Corpus Builder story, in light and dark, against WCAG 2.0 through 2.2 A/AA.
// The inventory is split into stable batches so CI can scan it concurrently and retry/fail
// a small slice rather than serializing the entire Storybook catalogue behind one test.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const BATCHES = 4;
const isCorpusStory = (id: string) =>
  id.startsWith("corpus") || id.startsWith("metadata-enrichment");

async function scan(page: Page) {
  // Local Storybook development still runs the a11y addon automatically. Static CI builds
  // disable that automatic run, but retain this bounded retry so the test remains usable locally.
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
  for (let batch = 0; batch < BATCHES; batch += 1) {
    test(`Corpus Builder stories batch ${batch + 1}/${BATCHES} is WCAG 2.2 AA clean in ${scheme} mode`, async ({
      browser,
      baseURL,
    }) => {
      test.setTimeout(240_000);
      const index = await (await fetch(`${baseURL}/index.json`)).json();
      const allIds = Object.entries<{ type: string }>(index.entries)
        .filter(([id, entry]) => entry.type === "story" && isCorpusStory(id))
        .map(([id]) => id)
        .sort();
      expect(allIds.length, "the sweep found too few Corpus Builder stories").toBeGreaterThan(100);

      const ids = allIds.filter((_, storyIndex) => storyIndex % BATCHES === batch);
      expect(ids.length, `batch ${batch + 1} has no stories`).toBeGreaterThan(0);

      const context = await browser.newContext({ colorScheme: scheme, reducedMotion: "reduce" });
      const page = await context.newPage();
      const failures: Record<string, unknown> = {};

      for (const id of ids) {
        await page.goto(`${baseURL}/iframe.html?id=${id}&viewMode=story`);
        await page.evaluate((s) => {
          document.documentElement.dataset.colorScheme = s;
        }, scheme);
        await page.waitForTimeout(250);
        const { violations } = await scan(page);
        if (violations.length) {
          failures[id] = violations.map((v) => ({
            rule: v.id,
            nodes: v.nodes.slice(0, 2).map((n) => ({
              target: n.target.join(" "),
              why: n.any[0]?.message ?? n.all[0]?.message,
            })),
          }));
        }
      }

      await context.close();
      expect(failures, JSON.stringify(failures, null, 2)).toEqual({});
    });
  }
}

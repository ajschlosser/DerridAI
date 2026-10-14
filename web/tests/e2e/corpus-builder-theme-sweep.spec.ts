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

import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Full scans remain the merge-to-master/release gate. Ordinary PRs use a deterministic,
// breadth-preserving sample because the composed workflow suite already scans interactive states.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const SCOPE = process.env.DERRIDAI_A11Y_SCOPE === "representative" ? "representative" : "full";
const BATCHES = SCOPE === "full" ? 4 : 2;
const REPRESENTATIVE_STORIES = 16;
const isCorpusStory = (id: string) =>
  id.startsWith("corpus") || id.startsWith("metadata-enrichment");

function evenlySample(ids: string[], target: number): string[] {
  if (ids.length <= target) return ids;
  const chosen = new Set<number>();
  for (let index = 0; index < target; index += 1) {
    chosen.add(Math.round((index * (ids.length - 1)) / (target - 1)));
  }
  return [...chosen].sort((a, b) => a - b).map((index) => ids[index]);
}

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
    test(`Corpus Builder stories batch ${batch + 1}/${BATCHES} is WCAG 2.2 AA clean in ${scheme} mode (${SCOPE})`, async ({
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

      let ownedIds = allIds;
      if (SCOPE === "representative") {
        ownedIds = evenlySample(allIds, REPRESENTATIVE_STORIES);
        // Structural accessibility is theme-independent. Dark mode keeps a second contrast-focused
        // sample while avoiding a complete duplicate Axe traversal of the same DOM structures.
        if (scheme === "dark") ownedIds = ownedIds.filter((_, index) => index % 2 === 0);
      }
      const ids = ownedIds.filter((_, storyIndex) => storyIndex % BATCHES === batch);
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

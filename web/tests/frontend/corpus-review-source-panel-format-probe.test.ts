import { readFileSync } from "node:fs";
import { format, resolveConfig } from "prettier";
import { expect, it } from "vitest";

for (const filepath of [
  "../CBI_PROGRESS.md",
  "src/components/corpus-builder/CorpusReviewSourcePanel.stories.ts",
  "src/components/corpus-builder/CorpusReviewSourcePanel.vue",
  "tests/frontend/corpus-review-source-panel.test.ts",
]) {
  it(`prints the exact Prettier delta for ${filepath}`, async () => {
    const source = readFileSync(filepath, "utf8");
    const config = (await resolveConfig(filepath)) || {};
    const formatted = await format(source, { ...config, filepath });
    expect(source).toBe(formatted);
  });
}

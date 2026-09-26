import { readFileSync } from "node:fs";
import { createPatch } from "diff";
import { format, resolveConfig } from "prettier";
import { expect, it } from "vitest";

for (const filepath of [
  "src/components/corpus-builder/CorpusReviewSourcePanel.stories.ts",
  "src/components/corpus-builder/CorpusReviewSourcePanel.vue",
  "tests/frontend/corpus-review-source-panel.test.ts",
]) {
  it(`prints the full Prettier patch for ${filepath}`, async () => {
    const source = readFileSync(filepath, "utf8");
    const config = (await resolveConfig(filepath)) || {};
    const formatted = await format(source, { ...config, filepath });
    if (source !== formatted) {
      console.error(createPatch(filepath, source, formatted, "current", "prettier"));
    }
    expect(source).toBe(formatted);
  });
}

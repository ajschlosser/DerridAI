import { readFileSync } from "node:fs";
import { format, resolveConfig } from "prettier";
import { expect, it } from "vitest";

it("prints the exact Prettier delta for CorpusReviewRecordQueue", async () => {
  const filepath = "src/components/corpus-builder/CorpusReviewRecordQueue.vue";
  const source = readFileSync(filepath, "utf8");
  const config = (await resolveConfig(filepath)) || {};
  const formatted = await format(source, { ...config, filepath });

  expect(source).toBe(formatted);
});

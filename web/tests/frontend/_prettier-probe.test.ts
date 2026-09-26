import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { format, resolveConfig } from "prettier";

describe("temporary Prettier probe", () => {
  it("reports exact enrichment formatter deltas", async () => {
    const path = resolve(
      process.cwd(),
      "src/components/corpus-builder/CorpusEnrichmentConfiguration.vue",
    );
    const source = readFileSync(path, "utf8");
    const config = (await resolveConfig(path)) || {};
    const formatted = await format(source, { ...config, filepath: path });
    const before = source.split("\n");
    const after = formatted.split("\n");
    const max = Math.max(before.length, after.length);
    const deltas: Array<{ line: number; before: string; after: string }> = [];
    for (let index = 0; index < max; index += 1) {
      if (before[index] !== after[index]) {
        deltas.push({
          line: index + 1,
          before: before[index] ?? "<missing>",
          after: after[index] ?? "<missing>",
        });
      }
    }
    expect(deltas, "Prettier line deltas").toEqual([]);
  });
});

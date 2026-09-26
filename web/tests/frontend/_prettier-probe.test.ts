import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { diffWordsWithSpace } from "diff";
import { describe, expect, it } from "vitest";
import { format, resolveConfig } from "prettier";

describe("temporary Prettier probe", () => {
  it("reports the exact CorpusEnrichmentConfiguration formatter delta", async () => {
    const path = resolve(
      process.cwd(),
      "src/components/corpus-builder/CorpusEnrichmentConfiguration.vue",
    );
    const source = readFileSync(path, "utf8");
    const config = (await resolveConfig(path)) || {};
    const formatted = await format(source, { ...config, filepath: path });
    const delta = diffWordsWithSpace(source, formatted)
      .filter((part) => part.added || part.removed)
      .map((part) => `${part.added ? "+" : "-"} ${part.value}`)
      .join("\n");

    expect(delta, "Prettier delta").toBe("");
  });
});

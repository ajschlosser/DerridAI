/* Copyright 2026 Aaron John Schlosser, PhD. */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "vitest";
import { format } from "prettier";

describe("temporary semantic graph formatter probe", () => {
  it("prints formatter output for CI repair", async () => {
    const relativePath = "src/components/corpus-builder/CorpusSemanticGraphPanel.vue";
    const absolutePath = resolve(process.cwd(), relativePath);
    const source = readFileSync(absolutePath, "utf8");
    const formatted = await format(source, { filepath: absolutePath, printWidth: 100 });
    const encoded = Buffer.from(formatted, "utf8").toString("base64");
    const chunks = encoded.match(/.{1,4000}/g) || [];
    chunks.forEach((chunk, index) => {
      console.log(`PRETTIER_GRAPH|${index + 1}|${chunks.length}|${chunk}`);
    });
  });
});

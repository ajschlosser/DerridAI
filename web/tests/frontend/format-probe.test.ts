/*
 * Temporary formatting probe for PR CI. Removed after the formatted sources are captured.
 */
import { readFileSync } from "node:fs";
import { describe, it } from "vitest";
import { format } from "prettier";

const FILES = [
  "src/components/CorpusBulkMetadataEditor.vue",
  "src/domain/inspectorLayout.ts",
  "tests/frontend/inspector-layout.test.ts",
  "tests/frontend/works-workspace.test.ts",
];

describe("format probe", () => {
  it("prints canonical Prettier output for the changed files", async () => {
    for (const path of FILES) {
      const source = readFileSync(path, "utf8");
      const parser = path.endsWith(".vue") ? "vue" : "typescript";
      const formatted = await format(source, { parser, printWidth: 100 });
      console.log(`FORMAT_OUTPUT_BEGIN:${path}\n${formatted}FORMAT_OUTPUT_END:${path}`);
    }
  });
});

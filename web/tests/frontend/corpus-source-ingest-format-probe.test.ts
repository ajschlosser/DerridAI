/*
 * Temporary formatting probe for PR #507. Remove after CI reveals Prettier's exact output.
 */
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import prettier from "prettier";

describe("CorpusSourceIngest formatting probe", () => {
  it("prints Prettier output around the changed audio sections", async () => {
    const sourcePath = path.resolve(process.cwd(), "src/components/CorpusSourceIngest.vue");
    const source = fs.readFileSync(sourcePath, "utf8");
    const formatted = await prettier.format(source, {
      parser: "vue",
      printWidth: 100,
    });
    if (formatted === source) return;

    const markers = [
      "function confirmPendingFile",
      'class="kind-mark"',
      'v-if="audioPending"',
      ".audio-ingest-options",
    ];
    const excerpts = markers.map((marker) => {
      const index = formatted.indexOf(marker);
      const start = Math.max(0, formatted.lastIndexOf("\n", Math.max(0, index - 700)));
      const end = formatted.indexOf("\n", index + 1500);
      return formatted.slice(start, end < 0 ? index + 1500 : end);
    });
    expect.fail("PRETTIER EXCERPTS\n" + excerpts.join("\n---\n"));
  });
});

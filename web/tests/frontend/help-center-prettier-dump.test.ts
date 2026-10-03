/*
 * Temporary CI-only formatting diagnostic. Remove after applying the emitted Prettier output.
 */
import { readFileSync } from "node:fs";
import { format } from "prettier";
import { expect, it } from "vitest";

const paths = [
  "../docs/requirements/TRACEABILITY_MATRIX.md",
  "../docs/requirements/UX_ACCESSIBILITY_AND_I18N.md",
  "src/components/help/HelpContentsNav.stories.ts",
  "src/domain/helpTopics.ts",
];

it("prints canonical Prettier output for changed Help Center files", async () => {
  const differences: string[] = [];
  for (const path of paths) {
    const source = readFileSync(path, "utf8");
    const formatted = await format(source, { filepath: path, printWidth: 100 });
    if (formatted !== source) {
      differences.push(path);
      console.log(`PRETTIER_BEGIN ${path}\n${formatted}PRETTIER_END ${path}`);
    }
  }
  expect(differences).toEqual([]);
});

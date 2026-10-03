import { readFileSync } from "node:fs";
import { format } from "prettier";
import { expect, it } from "vitest";

it("prints Help Topics Prettier output", async () => {
  const path = "src/domain/helpTopics.ts";
  const source = readFileSync(path, "utf8");
  const formatted = await format(source, { filepath: path, printWidth: 100 });
  if (formatted !== source) {
    console.log(`PRETTIER_BEGIN\n${formatted}PRETTIER_END`);
  }
  expect(formatted).toBe(source);
});

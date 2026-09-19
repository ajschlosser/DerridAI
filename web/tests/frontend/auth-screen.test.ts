import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AuthScreen from "../../src/components/AuthScreen.vue";
import pkg from "../../package.json";

describe("AuthScreen", () => {
  it("never shows a version other than the package version", () => {
    const text=mount(AuthScreen).text();
    for(const found of text.match(/\d+\.\d+\.\d+/g)??[])expect(found).toBe(pkg.version);
  });
});

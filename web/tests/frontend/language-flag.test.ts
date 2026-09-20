import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import LanguageFlag from "../../src/components/LanguageFlag.vue";

describe("LanguageFlag", () => {
  it("shows the flag it is given and nothing keyed on the language code", () => {
    expect(mount(LanguageFlag, { props: { code: "fr-CA", symbol: "🇺🇸", label: "x" } }).text()).toBe("🇺🇸");
    expect(mount(LanguageFlag, { props: { code: "en-US", symbol: "🌐", label: "x" } }).text()).toBe("🌐");
  });

  it("falls back to the neutral globe when there is no flag, whatever the code", () => {
    for (const code of ["en-US", "fr-CA", "de-DE"]) {
      expect(mount(LanguageFlag, { props: { code, label: "x" } }).text()).toBe("🌐");
    }
  });
});

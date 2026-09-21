/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import UiPageHeader from "../../src/components/ui/UiPageHeader.vue";

describe("UiPageHeader", () => {
  it("connects the heading and optional action/meta regions", () => {
    const wrapper = mount(UiPageHeader, {
      props: {
        kicker: "Corpus",
        title: "Records",
        description: "Review loaded records.",
        titleId: "records-title",
        actionsLabel: "Record actions",
      },
      slots: {
        actions: "<button type='button'>Import</button>",
        meta: "<span>1,248 records</span>",
      },
    });

    const header = wrapper.get("header");
    expect(header.attributes("aria-labelledby")).toBe("records-title");
    expect(wrapper.get("#records-title").text()).toBe("Records");
    expect(wrapper.get(".ui-page-header-description").text()).toBe("Review loaded records.");
    expect(wrapper.get(".ui-page-header-actions").attributes("aria-label")).toBe("Record actions");
    expect(wrapper.get(".ui-page-header-meta").text()).toContain("1,248 records");
  });

  it("does not render empty optional regions", () => {
    const wrapper = mount(UiPageHeader, { props: { title: "Settings" } });

    expect(wrapper.find(".ui-page-header-kicker").exists()).toBe(false);
    expect(wrapper.find(".ui-page-header-description").exists()).toBe(false);
    expect(wrapper.find(".ui-page-header-actions").exists()).toBe(false);
    expect(wrapper.find(".ui-page-header-meta").exists()).toBe(false);
  });
});

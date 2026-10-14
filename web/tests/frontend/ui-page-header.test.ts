/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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

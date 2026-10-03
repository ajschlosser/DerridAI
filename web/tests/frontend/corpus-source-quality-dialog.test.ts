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
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusSourceQualityDialog from "../../src/components/CorpusSourceQualityDialog.vue";

describe("CorpusSourceQualityDialog", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("preserves don't-show-again when the dialog close control is used", async () => {
    const wrapper = mount(CorpusSourceQualityDialog, {
      props: { open: true, issues: [{ code: "source_quality_warning" }] },
      global: {
        stubs: {
          UiDialog: {
            template:
              '<div><button data-close @click="$emit(\'close\')">close</button><slot/><slot name="footer"/></div>',
          },
          CorpusSourceIssuePanel: true,
          AppIcon: true,
        },
      },
    });

    await wrapper.get('input[type="checkbox"]').setValue(true);
    await wrapper.get("[data-close]").trigger("click");

    expect(wrapper.emitted("close")?.at(-1)?.[0]).toBe(true);
  });
});

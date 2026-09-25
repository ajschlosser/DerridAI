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

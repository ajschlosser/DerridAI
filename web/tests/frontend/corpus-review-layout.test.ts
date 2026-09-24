import { mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusActionMenu from "../../src/components/CorpusActionMenu.vue";
import { usePdfCorpusPaneSizing } from "../../src/composables/usePdfCorpusPaneSizing";
import { useSplitter } from "../../src/composables/useSplitter";

const items = [
  { id: "prev", label: "Combine with previous record" },
  {
    id: "next",
    label: "Combine with next record",
    reason: "There is no next record to combine with.",
  },
  { id: "slice", label: "Slice record" },
];
const mountMenu = () =>
  mount(CorpusActionMenu, { props: { label: "More actions", items }, attachTo: document.body });
const key = (wrapper: any, selector: string, k: string) =>
  wrapper.get(selector).trigger("keydown", { key: k });

describe("CorpusActionMenu", () => {
  it("is a menu button that opens with Enter or the arrows and focuses an item", async () => {
    const wrapper = mountMenu();
    const trigger = wrapper.get("button[aria-haspopup='menu']");
    expect(trigger.attributes("aria-expanded")).toBe("false");
    await trigger.trigger("click");
    expect(trigger.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get("[role=menu]").attributes("aria-label")).toBe("More actions");
    expect(document.activeElement?.textContent).toContain("Combine with previous record");
    wrapper.unmount();
  });

  it("moves with the arrows, wraps, and jumps with Home and End", async () => {
    const wrapper = mountMenu();
    await wrapper.get("button[aria-haspopup='menu']").trigger("click");
    await key(wrapper, "[role=menu]", "ArrowDown");
    expect(document.activeElement?.textContent).toContain("Combine with next record");
    await key(wrapper, "[role=menu]", "End");
    expect(document.activeElement?.textContent).toContain("Slice record");
    await key(wrapper, "[role=menu]", "ArrowDown");
    expect(document.activeElement?.textContent).toContain("Combine with previous record");
    await key(wrapper, "[role=menu]", "ArrowUp");
    expect(document.activeElement?.textContent).toContain("Slice record");
    wrapper.unmount();
  });

  it("closes on Escape and returns focus to the button", async () => {
    const wrapper = mountMenu();
    const trigger = wrapper.get("button[aria-haspopup='menu']");
    await trigger.trigger("click");
    await key(wrapper, "[role=menu]", "Escape");
    expect(wrapper.find("[role=menu]").exists()).toBe(false);
    expect(document.activeElement).toBe(trigger.element);
    wrapper.unmount();
  });

  it("emits the chosen action and closes", async () => {
    const wrapper = mountMenu();
    await wrapper.get("button[aria-haspopup='menu']").trigger("click");
    await wrapper.findAll("[role=menuitem]")[2].trigger("click");
    expect(wrapper.emitted("select")).toEqual([["slice"]]);
    expect(wrapper.find("[role=menu]").exists()).toBe(false);
    wrapper.unmount();
  });

  it("keeps an unavailable action focusable with its reason, and does not run it", async () => {
    const wrapper = mountMenu();
    await wrapper.get("button[aria-haspopup='menu']").trigger("click");
    const unavailable = wrapper.findAll("[role=menuitem]")[1];
    expect(unavailable.attributes("aria-disabled")).toBe("true");
    expect(unavailable.attributes("disabled")).toBeUndefined();
    const reasonId = unavailable.attributes("aria-describedby")!;
    expect(wrapper.get(`#${reasonId}`).text()).toBe("There is no next record to combine with.");
    await unavailable.trigger("click");
    expect(wrapper.emitted("select")).toBeUndefined();
    expect(wrapper.find("[role=menu]").exists()).toBe(true);
    wrapper.unmount();
  });

  it("does not open when disabled", async () => {
    const wrapper = mount(CorpusActionMenu, {
      props: { label: "More actions", items, disabled: true },
    });
    await wrapper.get("button[aria-haspopup='menu']").trigger("click");
    expect(wrapper.find("[role=menu]").exists()).toBe(false);
  });
});

function harness(options: {
  edge: "start" | "end";
  dir?: "ltr" | "rtl";
  width?: number;
  axis?: "horizontal" | "vertical";
}) {
  const container = document.createElement("div");
  container.style.direction = options.dir ?? "ltr";
  container.getBoundingClientRect = () =>
    ({
      left: 0,
      right: options.width ?? 1000,
      top: 0,
      bottom: 600,
      width: options.width ?? 1000,
      height: 600,
      x: 0,
      y: 0,
      toJSON() {},
    }) as DOMRect;
  document.body.appendChild(container);
  let api!: ReturnType<typeof useSplitter>;
  const Host = defineComponent({
    setup() {
      api = useSplitter({
        key: "test.splitter",
        min: 200,
        max: 500,
        initial: 300,
        edge: options.edge,
        axis: options.axis,
        container: () => container,
      });
      return () =>
        h("div", {
          role: "separator",
          tabindex: 0,
          ...api.aria(),
          onKeydown: api.onKeydown,
          onPointerdown: api.onPointerDown,
          onDblclick: api.reset,
        });
    },
  });
  const wrapper = mount(Host);
  return { api, wrapper, container };
}
const press = (wrapper: any, k: string, shiftKey = false) =>
  wrapper.get("[role=separator]").trigger("keydown", { key: k, shiftKey });

describe("useSplitter", () => {
  beforeEach(() => localStorage.clear());

  it("starts at the initial size and exposes it to assistive technology", () => {
    const { wrapper, api } = harness({ edge: "start" });
    expect(api.size.value).toBe(300);
    expect(wrapper.get("[role=separator]").attributes()).toMatchObject({
      "aria-valuemin": "200",
      "aria-valuemax": "500",
      "aria-valuenow": "300",
    });

    describe("usePdfCorpusPaneSizing", () => {
      beforeEach(() => localStorage.clear());

      it("owns the three review pane splitters and their persisted defaults", () => {
        let sizing!: ReturnType<typeof usePdfCorpusPaneSizing>;
        const Host = defineComponent({
          setup() {
            sizing = usePdfCorpusPaneSizing();
            return () => h("div", { ref: sizing.reviewGridEl });
          },
        });
        const wrapper = mount(Host);

        expect(sizing.queueSplitter.size.value).toBe(256);
        expect(sizing.inspectorSplitter.size.value).toBe(368);
        expect(sizing.reviewHeightSplitter.size.value).toBe(680);
        expect(sizing.queueSplitter.aria()).toMatchObject({
          "aria-valuemin": 224,
          "aria-valuemax": 420,
        });
        expect(sizing.inspectorSplitter.aria()).toMatchObject({
          "aria-valuemin": 320,
          "aria-valuemax": 640,
        });
        expect(sizing.reviewHeightSplitter.aria()).toMatchObject({
          "aria-valuemin": 420,
          "aria-valuemax": 1200,
        });

        sizing.queueSplitter.reset();
        sizing.inspectorSplitter.reset();
        sizing.reviewHeightSplitter.reset();
        expect(localStorage.getItem("derridai.review.queueWidth")).toBe("256");
        expect(localStorage.getItem("derridai.review.inspectorWidth")).toBe("368");
        expect(localStorage.getItem("derridai.review.height")).toBe("680");
        wrapper.unmount();
      });
    });
  });

  it("the right arrow grows a pane on the left and shrinks one on the right", async () => {
    const start = harness({ edge: "start" });
    await press(start.wrapper, "ArrowRight");
    expect(start.api.size.value).toBe(316);
    localStorage.clear();
    const end = harness({ edge: "end" });
    await press(end.wrapper, "ArrowRight");
    expect(end.api.size.value).toBe(284);
  });

  it("follows the writing direction, so right-to-left resizes the way it looks", async () => {
    const start = harness({ edge: "start", dir: "rtl" });
    await press(start.wrapper, "ArrowRight");
    expect(start.api.size.value).toBe(284); // the "start" pane is on the right, so moving right shrinks it
  });

  it("takes larger steps with Shift, jumps with Home and End, and stays within its limits", async () => {
    const { wrapper, api } = harness({ edge: "start" });
    await press(wrapper, "ArrowRight", true);
    expect(api.size.value).toBe(364);
    await press(wrapper, "End");
    expect(api.size.value).toBe(500);
    await press(wrapper, "ArrowRight", true);
    expect(api.size.value).toBe(500);
    await press(wrapper, "Home");
    expect(api.size.value).toBe(200);
  });

  it("ignores other keys and remembers the size", async () => {
    const { wrapper, api } = harness({ edge: "start" });
    await press(wrapper, "a");
    expect(api.size.value).toBe(300);
    await press(wrapper, "ArrowRight");
    expect(localStorage.getItem("test.splitter")).toBe("316");
    const again = harness({ edge: "start" });
    expect(again.api.size.value).toBe(316);
  });

  it("can be dragged, measured from the pane's own outer edge", async () => {
    const { wrapper, api } = harness({ edge: "end", width: 1000 });
    await wrapper.get("[role=separator]").trigger("pointerdown", { button: 0, pointerId: 1 });
    window.dispatchEvent(new MouseEvent("pointermove", { clientX: 700 }));
    expect(api.size.value).toBe(300); // 1000 - 700
    window.dispatchEvent(new MouseEvent("pointermove", { clientX: 100 }));
    expect(api.size.value).toBe(500); // clamped to the maximum
    window.dispatchEvent(new MouseEvent("pointerup"));
    window.dispatchEvent(new MouseEvent("pointermove", { clientX: 900 }));
    expect(api.size.value).toBe(500); // no longer following the pointer
  });

  it("can be reset", async () => {
    const { wrapper, api } = harness({ edge: "start" });
    await press(wrapper, "End");
    api.reset();
    expect(api.size.value).toBe(300);
  });

  it("supports vertical resizing with down/up keys and pointer distance", async () => {
    const vertical = harness({ edge: "start", axis: "vertical" });
    await press(vertical.wrapper, "ArrowDown");
    expect(vertical.api.size.value).toBe(316);
    await vertical.wrapper.get("[role=separator]").trigger("pointerdown", { button: 0, pointerId: 1 });
    window.dispatchEvent(new MouseEvent("pointermove", { clientY: 700 }));
    expect(vertical.api.size.value).toBe(500);
    window.dispatchEvent(new MouseEvent("pointerup"));
  });
});

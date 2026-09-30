// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import UiRelationNodeShell from "../../src/components/relations/UiRelationNodeShell.vue";
import UiRelationViewport from "../../src/components/relations/UiRelationViewport.vue";

function transform(wrapper: ReturnType<typeof mount>) {
  return wrapper.get("[data-relation-viewport-layer]").attributes("style") || "";
}

describe("UiRelationViewport", () => {
  it("does not pan until the pointer crosses the drag threshold", async () => {
    const wrapper = mount(UiRelationViewport, {
      props: { accessibleLabel: "Relations", resizeLabel: "Resize relations", resizable: false },
    });
    const surface = wrapper.get(".ui-relation-viewport");
    const before = transform(wrapper);
    await surface.trigger("pointerdown", { button: 0, pointerId: 1, clientX: 10, clientY: 10 });
    await surface.trigger("pointermove", { pointerId: 1, clientX: 12, clientY: 11 });
    expect(transform(wrapper)).toBe(before);
    await surface.trigger("pointermove", { pointerId: 1, clientX: 25, clientY: 20 });
    expect(transform(wrapper)).not.toBe(before);
    await surface.trigger("pointerup", { pointerId: 1 });
  });

  it("supports wheel zoom and keyboard panning", async () => {
    const wrapper = mount(UiRelationViewport, {
      props: { accessibleLabel: "Relations", resizeLabel: "Resize relations", resizable: false },
    });
    const surface = wrapper.get(".ui-relation-viewport");
    await surface.trigger("wheel", { deltaY: -1, clientX: 100, clientY: 100 });
    expect(transform(wrapper)).toContain("scale(1.15)");
    const afterZoom = transform(wrapper);
    await surface.trigger("keydown", { key: "ArrowLeft" });
    expect(transform(wrapper)).not.toBe(afterZoom);
  });

  it("resizes from the keyboard", async () => {
    const wrapper = mount(UiRelationViewport, {
      props: {
        accessibleLabel: "Relations",
        resizeLabel: "Resize relations",
        resizeAxis: "vertical",
      },
    });
    await wrapper.get("[data-relation-resize-handle]").trigger("keydown", { key: "ArrowDown" });
    expect(wrapper.get(".ui-relation-viewport").attributes("style")).toContain("height: 252px");
  });
});

describe("UiRelationNodeShell", () => {
  it("converts pointer drag distance through the current zoom", async () => {
    const wrapper = mount(UiRelationNodeShell, {
      props: {
        nodeId: "n1",
        x: 100,
        y: 50,
        zoom: 2,
        accessibleLabel: "Node one",
      },
      slots: { default: "Node one" },
    });
    const node = wrapper.get("button");
    await node.trigger("pointerdown", { button: 0, pointerId: 2, clientX: 10, clientY: 10 });
    await node.trigger("pointermove", { pointerId: 2, clientX: 30, clientY: 20 });
    await node.trigger("pointerup", { pointerId: 2 });
    expect(wrapper.emitted("move")?.at(-1)?.[0]).toEqual({ x: 110, y: 55 });
  });

  it("supports Alt+Arrow keyboard nudging", async () => {
    const wrapper = mount(UiRelationNodeShell, {
      props: {
        nodeId: "n1",
        x: 100,
        y: 50,
        zoom: 1,
        accessibleLabel: "Node one",
      },
    });
    await wrapper.get("button").trigger("keydown", { key: "ArrowUp", altKey: true });
    expect(wrapper.emitted("move")?.[0]?.[0]).toEqual({ x: 100, y: 42 });
  });
});

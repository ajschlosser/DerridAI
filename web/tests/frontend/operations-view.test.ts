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

import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const calls = vi.hoisted(() => ({
  mountOperationsPanelHost: vi.fn(),
  unmountOperationsPanel: vi.fn(),
}));
vi.mock("../../src/domain/operationsPanelHooks", () => ({
  mountOperationsPanelHost: calls.mountOperationsPanelHost,
}));
vi.mock("../../src/domain/operationsPanelHost", () => ({
  unmountOperationsPanel: calls.unmountOperationsPanel,
}));

import OperationsView from "../../src/views/OperationsView.vue";

describe("OperationsView", () => {
  it("mounts the panel host immediately and unmounts it on leave", async () => {
    const wrapper = mount(OperationsView);
    expect(wrapper.find("#operationsPanelHost").exists()).toBe(true);
    expect(calls.mountOperationsPanelHost).toHaveBeenCalledTimes(1);
    await flushPromises();
    wrapper.unmount();
    expect(calls.unmountOperationsPanel).toHaveBeenCalledTimes(1);
  });
});

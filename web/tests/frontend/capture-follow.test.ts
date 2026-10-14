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

import { describe, expect, it, vi, beforeEach } from "vitest";
import { defineComponent } from "vue";
import { mount } from "@vue/test-utils";

const stop = vi.fn();
const follows: Array<{ topic: string; refresh: () => unknown; isDone?: () => boolean }> = [];
vi.mock("../../src/realtime/follow", () => ({
  followResource: (options: (typeof follows)[number]) => {
    follows.push(options);
    return stop;
  },
}));
const { getCapture } = vi.hoisted(() => ({ getCapture: vi.fn() }));
vi.mock("../../src/api/corpus", () => ({ corpusCaptureApi: { getCapture } }));

import { useCaptureFollow } from "../../src/composables/useCaptureFollow";

const running = { capture_id: "c1", active_job: { id: "j1" } } as never;
const idle = { capture_id: "c1", active_job: null } as never;

function setup(onSettled = vi.fn()) {
  let api!: ReturnType<typeof useCaptureFollow>;
  mount(
    defineComponent({
      setup() {
        api = useCaptureFollow({ onSettled });
        return () => null;
      },
    }),
  );
  return { api, onSettled };
}

describe("useCaptureFollow", () => {
  beforeEach(() => {
    follows.length = 0;
    stop.mockClear();
    getCapture.mockReset();
  });

  it("follows the running job once and settles when it finishes", async () => {
    const { api, onSettled } = setup();
    api.accept(running);
    api.accept(running);
    expect(follows.map((f) => f.topic)).toEqual(["job:j1"]);

    getCapture.mockResolvedValue(idle);
    await follows[0].refresh();
    expect(getCapture).toHaveBeenCalledWith("c1");
    expect(follows[0].isDone?.()).toBe(true);
    expect(stop).toHaveBeenCalled();
    expect(onSettled).toHaveBeenCalledTimes(1);
  });

  it("does not follow an idle capture and stops on unmount", () => {
    const { api } = setup();
    api.accept(idle);
    expect(follows).toHaveLength(0);
  });
});

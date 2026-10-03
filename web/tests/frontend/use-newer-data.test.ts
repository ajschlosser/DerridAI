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

import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h, nextTick } from "vue";
import { mount, flushPromises } from "@vue/test-utils";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { queryClient } from "../../src/realtime/dataQuery";
import { useNewerData } from "../../src/composables/useNewerData";

let exposed: ReturnType<typeof useNewerData>;
const Probe = defineComponent({
  setup() {
    exposed = useNewerData();
    return () => h("div");
  },
});
const mounted = () => mount(Probe, { global: { plugins: [[VueQueryPlugin, { queryClient }]] } });

afterEach(() => queryClient.clear());

describe("useNewerData", () => {
  it("reports newer data only after a server invalidation and clears on acknowledge", async () => {
    const wrapper = mounted();
    await flushPromises();
    expect(exposed.hasNewer.value).toBe(false);

    // A refetch (focus, fallback poll) is not a change signal.
    await queryClient.refetchQueries({ queryKey: ["data", "corpus_records"] });
    expect(exposed.hasNewer.value).toBe(false);

    // Another resource changing is not ours.
    await queryClient.invalidateQueries({ queryKey: ["data", "users"] });
    expect(exposed.hasNewer.value).toBe(false);

    await queryClient.invalidateQueries({ queryKey: ["data", "corpus_records"] });
    await nextTick();
    expect(exposed.hasNewer.value).toBe(true);

    exposed.acknowledge();
    expect(exposed.hasNewer.value).toBe(false);
    wrapper.unmount();
  });
});

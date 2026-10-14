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
import AppBuildInfo from "../../src/components/AppBuildInfo.vue";
import pkg from "../../package.json";

describe("AppBuildInfo", () => {
  it("shows the copyright holder and package version", () => {
    const text = mount(AppBuildInfo).text();
    expect(text).toContain("The New England Transcendental Club of California");
    expect(text).toContain(`DerridAI ${pkg.version}`);
    expect(text).toContain(pkg.codename);
    expect(text).toContain("© 2026");
  });

  it("hides the git commit unless asked", () => {
    expect(mount(AppBuildInfo).text()).not.toContain("Build vitest");
    expect(mount(AppBuildInfo, { props: { showCommit: true } }).text()).toContain("Build vitest");
  });

  it("can omit copyright for compact version-only chrome", () => {
    const text = mount(AppBuildInfo, { props: { showCopyright: false } }).text();
    expect(text).toContain(`DerridAI ${pkg.version}`);
    expect(text).not.toContain("The New England Transcendental Club of California");
  });
});

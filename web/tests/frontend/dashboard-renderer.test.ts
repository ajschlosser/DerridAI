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
import { createDashboardRenderer } from "../../src/domain/dashboardRenderer";

// The dashboard's markup is covered by the legacy baseline's home scenarios; this pins the latest-annotation click.
describe("dashboard latest annotation", () => {
  it("opens the shared annotation's record in its own store", () => {
    const openAnnotationsWorkspaceRecord = vi.fn();
    const deps = new Proxy(
      { state: {}, openAnnotationsWorkspaceRecord } as Record<string, unknown>,
      { get: (target, name: string) => target[name] ?? vi.fn() },
    );
    createDashboardRenderer(deps as never).openSharedAnnotationRecord("derrida", "rec-7");
    expect(openAnnotationsWorkspaceRecord).toHaveBeenCalledWith({
      server: true,
      source: "derrida",
      record_id: "rec-7",
    });
  });
});

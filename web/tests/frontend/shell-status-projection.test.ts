/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { invalidateCorpusCache } from "../../src/domain/corpusCache";
import {
  getShellStatusProjection,
  invalidateShellStatusProjection,
} from "../../src/domain/shellStatusProjection";
import { state } from "../../src/domain/sharedUrlState";

describe("shell status projection", () => {
  beforeEach(() => {
    state.files = [];
    state.stores = [];
    state.activeStore = "";
    state.selectedEvidence = {};
    state.health = null;
    invalidateShellStatusProjection();
  });

  afterEach(() => {
    state.files = [];
    state.stores = [];
    state.activeStore = "";
    state.selectedEvidence = {};
    state.health = null;
    invalidateShellStatusProjection();
  });

  it("reuses the projection across unrelated shell reads", () => {
    state.files = [{ records: [{}, {}] }];
    invalidateShellStatusProjection();

    const first = getShellStatusProjection();
    const second = getShellStatusProjection();

    expect(first).toBe(second);
    expect(first.totalLoaded).toBe(2);
  });

  it("is invalidated by corpus changes rather than rescanning on every shell refresh", () => {
    state.files = [{ records: [{}] }];
    invalidateShellStatusProjection();
    expect(getShellStatusProjection().totalLoaded).toBe(1);

    state.files[0].records.push({});
    expect(getShellStatusProjection().totalLoaded).toBe(1);

    invalidateCorpusCache();
    expect(getShellStatusProjection().totalLoaded).toBe(2);
  });

  it("summarizes stores and selected evidence without inspecting record contents", () => {
    state.health = { ok: true, chroma: { available: true } };
    state.stores = [
      { name: "primary", count: 12 },
      { name: "_response_cache", count: 99, metadata: { kind: "response_cache" } },
    ];
    state.activeStore = "primary";
    state.selectedEvidence = { a: { key: "a" }, b: null };
    invalidateShellStatusProjection();

    expect(getShellStatusProjection()).toMatchObject({
      corpusStoreCount: 1,
      dbRecords: 12,
      hasCorpusDb: true,
      activeStore: "primary",
      selectedEvidenceCount: 1,
    });
  });
});

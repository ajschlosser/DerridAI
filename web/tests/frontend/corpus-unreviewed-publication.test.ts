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

import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const publish = vi.fn();
const reconcile = vi.fn();
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusBuilderApi: { publish, reconcile, publicationUrl: (id: string) => `/download/${id}` },
}));

const { useCorpusPublication } = await import(
  "../../src/features/corpus-builder/composables/useCorpusPublication"
);

function setup() {
  const setMessage = vi.fn();
  const tf = vi.fn((key: string, values: Record<string, string | number>) =>
    [key, ...Object.values(values)].join("|"),
  );
  const composable = useCorpusPublication({
    currentBuild: ref({ build_id: "build-1" } as never),
    selectedRecord: ref(null),
    busy: ref(""),
    setMessage,
    refreshBuild: async () => {},
    refreshBuilds: async () => {},
    t: (key) => key,
    tf,
  });
  return { composable, setMessage };
}

describe("unreviewed corpus publication", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    reconcile.mockResolvedValue({
      build_id: "build-1",
      publication_readiness: { can_publish: true },
    });
  });

  it("requests an autonomous publication and reports its independent decision status", async () => {
    publish.mockResolvedValueOnce({
      publication_id: "p1",
      filename: "c.jsonl.zst",
      sha256: "abc",
      record_count: 3,
      created_at: "",
      celf_conformant: true,
      review_mode: "autonomous",
      unreviewed_record_count: 2,
      unreviewed_accepted_field_count: 5,
    });
    const { composable, setMessage } = setup();
    await composable.publish({ acceptUnreviewed: true });
    expect(publish).toHaveBeenCalledWith("build-1", { acceptUnreviewed: true });
    expect(setMessage).toHaveBeenCalledWith("pdf_corpus.published_unreviewed|3|2|5");
  });

  it("reconciles before publication and keeps the user in cleanup when blockers remain", async () => {
    reconcile.mockResolvedValueOnce({
      build_id: "build-1",
      publication_readiness: {
        can_publish: false,
        blockers: [{ code: "source_validation", count: 1 }],
      },
    });
    const { composable, setMessage } = setup();

    const result = await composable.publish();

    expect(result).toBeNull();
    expect(reconcile).toHaveBeenCalledWith("build-1");
    expect(publish).not.toHaveBeenCalled();
    expect(setMessage).toHaveBeenCalledWith("pdf_corpus.publication_waiting_help");
  });

  it("keeps the normal publication path reviewed", async () => {
    publish.mockResolvedValueOnce({
      publication_id: "p2",
      filename: "c.jsonl.zst",
      sha256: "abcdef0123456789",
      record_count: 1,
      created_at: "",
      celf_conformant: true,
    });
    const { composable, setMessage } = setup();
    await composable.publish();
    expect(publish).toHaveBeenLastCalledWith("build-1", { acceptUnreviewed: undefined });
    expect(setMessage).toHaveBeenCalledWith("pdf_corpus.published|1|abcdef012345");
  });
});

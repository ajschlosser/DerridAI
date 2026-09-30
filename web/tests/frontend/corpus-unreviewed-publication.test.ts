/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";

const publish = vi.fn();
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusBuilderApi: { publish, publicationUrl: (id: string) => `/download/${id}` },
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
    expect(setMessage).toHaveBeenCalledWith("pdf_corpus.published|3|abc");
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

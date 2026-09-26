// Copyright 2026 Aaron John Schlosser, PhD.
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

const corpusBuilderApi = vi.hoisted(() => ({
  importUrl: vi.fn(),
  importGutenberg: vi.fn(),
  listAssets: vi.fn(),
}));
vi.mock("../../src/api/corpus", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/corpus")>()),
  corpusBuilderApi,
}));
const apiRequest = vi.hoisted(() => vi.fn());
vi.mock("../../src/api/http", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/api/http")>()),
  apiRequest,
}));

import { useCorpusSourceConfiguration } from "../../src/features/corpus-builder/composables/useCorpusSourceConfiguration";
import { corpusSourcesApi } from "../../src/api/corpus/sources";

const connection = {
  provider_profile_id: "admin-openai",
  provider: "openai",
  model: "gpt-test",
  base_url: "https://api.openai.com/v1",
  api_key: "sk-browser",
};

describe("model-assisted page numbers on import", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    corpusBuilderApi.importUrl.mockResolvedValue({ asset_id: "a1", filename: "w.html" });
    corpusBuilderApi.listAssets.mockResolvedValue({ items: [] });
  });

  it("sends the browser profile's connection, since the server cannot resolve an administrator profile by ID", async () => {
    const source = useCorpusSourceConfiguration(
      ref(""),
      () => undefined,
      () => "admin-openai",
      () => connection,
    );
    await source.importLibraryUrl("https://fr.wikisource.org/wiki/Lettres_persanes");
    const pages = corpusBuilderApi.importUrl.mock.calls[0][2];
    expect(pages).toMatchObject({
      mode: "auto_llm",
      providerProfileId: "admin-openai",
      connection: { provider: "openai", model: "gpt-test", api_key: "sk-browser" },
    });
    expect(source.libraryImported.value).toBe(1);
  });

  it("puts the connection on the URL import request body", () => {
    apiRequest.mockResolvedValue({});
    void corpusSourcesApi.importUrl("https://fr.wikisource.org/wiki/X", 0, {
      mode: "auto_llm",
      providerProfileId: "admin-openai",
      connection: { provider: "openai", model: "gpt-test", api_key: "sk-browser" },
    });
    const body = JSON.parse(apiRequest.mock.calls[0][1].body);
    expect(body).toMatchObject({ provider: "openai", model: "gpt-test", api_key: "sk-browser" });
  });

  it("keeps a failed import's error in the library dialog", async () => {
    corpusBuilderApi.importUrl.mockRejectedValue(new Error("Wikisource: page not found"));
    const setMessage = vi.fn();
    const source = useCorpusSourceConfiguration(
      ref(""),
      setMessage,
      () => "",
      () => null,
    );
    await source.importLibraryUrl("https://fr.wikisource.org/wiki/Missing");
    expect(source.libraryError.value).toContain("page not found");
    expect(source.libraryImported.value).toBe(0);
    expect(source.libraryImporting.value).toBe("");
  });
});

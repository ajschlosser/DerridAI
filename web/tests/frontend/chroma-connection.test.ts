import { describe, expect, it } from "vitest";
import { chromaIdentity, parseChromaHttpUrl } from "../../src/domain/chromaConnection";

describe("chroma connection URL parsing", () => {
  it("strips API version suffixes and rejects credentials in the URL", () => {
    expect(parseChromaHttpUrl("https://chroma.example:8000/api/v2").display).toBe(
      "https://chroma.example:8000",
    );
    expect(parseChromaHttpUrl("http://chroma:8000/").ssl).toBe(false);
    expect(() => parseChromaHttpUrl("chroma:8000")).toThrow("url-invalid");
    expect(() => parseChromaHttpUrl("http://user:secret@chroma:8000")).toThrow("url-credentials");
  });

  it("never puts a token into the identity label", () => {
    expect(chromaIdentity("http", undefined, "http://chroma:8000")).toBe(
      "Chroma server · http://chroma:8000",
    );
    expect(chromaIdentity("embedded", "./data/chroma")).toBe("Local Chroma · ./data/chroma");
  });
});

/* Copyright 2026 Aaron John Schlosser, PhD. */

const RESEARCHER_LEET: Record<string, string> = {
  "0": "o",
  "1": "i",
  "3": "e",
  "4": "a",
  "5": "s",
  "7": "t",
  "@": "a",
  $: "s",
};

export function normalizeResearcherToken(value: unknown): string {
  const text = String(value || "")
    .normalize("NFKC")
    .replace(/[013457@$]/g, (ch) => RESEARCHER_LEET[ch] || ch)
    .toLocaleLowerCase();
  return text.replace(/(?<=\w)[._*~-]+(?=\w)/g, "");
}

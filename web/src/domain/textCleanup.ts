export type TextCleanupRule = "page_numbers" | "repeated_short_lines" | "line_hyphenation" | "whitespace";
export type TextCleanupPreview = { text: string; removed: string[]; changes: number };

const PAGE_NUMBER_RE = /^\s*(?:page\s+)?(?:[ivxlcdm]+|\d{1,4})\s*$/i;

export function cleanupText(input: string, rules: Set<TextCleanupRule>, recurringLines: string[] = []): TextCleanupPreview {
  let text = String(input || "");
  const removed: string[] = [];
  let changes = 0;
  const recurring = new Set(recurringLines.map(v => v.trim().toLocaleLowerCase()).filter(Boolean));

  if (rules.has("line_hyphenation")) {
    const next = text.replace(/(?<=\p{L})-\s*\n\s*(?=\p{L})/gu, "");
    if (next !== text) { changes++; text = next; }
  }

  if (rules.has("page_numbers") || rules.has("repeated_short_lines")) {
    const lines = text.split(/\r?\n/);
    const kept: string[] = [];
    for (const line of lines) {
      const normalized = line.trim().toLocaleLowerCase();
      const pageNumber = rules.has("page_numbers") && PAGE_NUMBER_RE.test(line);
      const recurringLine = rules.has("repeated_short_lines") && normalized.length > 0 && normalized.length <= 120 && recurring.has(normalized);
      if (pageNumber || recurringLine) {
        removed.push(line.trim());
        changes++;
      } else kept.push(line);
    }
    text = kept.join("\n");
  }

  if (rules.has("whitespace")) {
    const next = text.replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").replace(/[ \t]{2,}/g, " ").trim();
    if (next !== text) { changes++; text = next; }
  }
  return { text, removed, changes };
}

export function recurringShortLines(texts: string[], minimumOccurrences = 3): string[] {
  const counts = new Map<string, { count: number; display: string }>();
  for (const text of texts) {
    const seen = new Set<string>();
    for (const line of String(text || "").split(/\r?\n/)) {
      const display = line.trim();
      const key = display.toLocaleLowerCase();
      if (!key || key.length > 120 || PAGE_NUMBER_RE.test(display) || seen.has(key)) continue;
      seen.add(key);
      const prior = counts.get(key) || { count: 0, display };
      prior.count += 1;
      counts.set(key, prior);
    }
  }
  return Array.from(counts.values()).filter(item => item.count >= minimumOccurrences).sort((a,b)=>b.count-a.count).map(item => item.display).slice(0,50);
}

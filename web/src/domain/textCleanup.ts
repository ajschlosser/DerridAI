export type TextCleanupRule = "page_numbers" | "repeated_short_lines" | "line_hyphenation" | "paragraph_lines" | "empty_lines" | "whitespace";
export type TextCleanupPreview = { text: string; removed: string[]; changes: number };

const PAGE_NUMBER_RE = /^\s*(?:page\s+)?(?:[ivxlcdm]+|\d{1,4})\s*$/i;
const LIST_OR_QUOTE_RE = /^\s*(?:[-*•]|\d+[.)]|[a-z][.)]|[ivxlcdm]+[.)]|[>»«“”\"'])\s*/i;
const HEADINGISH_RE = /^\s*(?:[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 '\u2019\-–—:;,.]{3,}|.{0,80}:)\s*$/u;
const SENTENCE_END_RE = /[.!?…:;][\]\)\}"'»”’]*\s*$/u;
const LOWERCASE_START_RE = /^\s*[a-zà-öø-ÿ]/u;

/** Join line wraps that look like PDF layout artifacts while preserving semantic breaks.
 *
 * This intentionally errs on the side of keeping a line break. Lists, short headings,
 * quotations, already blank-separated paragraphs, and lines ending in sentence punctuation
 * remain separate. The immutable extracted source is never modified by this utility.
 */
function joinWrappedParagraphLines(text: string): {text:string; changes:number} {
  const lines=text.split(/\r?\n/);
  const out:string[]=[];
  let changes=0;
  for(let i=0;i<lines.length;i++){
    const current=lines[i];
    const next=lines[i+1];
    if(next===undefined){out.push(current);continue}
    const a=current.trimEnd();
    const b=next.trimStart();
    const shouldJoin=Boolean(
      a.trim() && b.trim() &&
      !SENTENCE_END_RE.test(a) &&
      !LIST_OR_QUOTE_RE.test(a) && !LIST_OR_QUOTE_RE.test(b) &&
      !HEADINGISH_RE.test(a) && !HEADINGISH_RE.test(b) &&
      (LOWERCASE_START_RE.test(b) || a.length >= 45)
    );
    if(shouldJoin){
      out.push(`${a} ${b}`);
      i += 1;
      changes += 1;
    }else out.push(current);
  }
  return {text:out.join("\n"),changes};
}

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

  if(rules.has("paragraph_lines")){
    // Run twice because PDF line wraps can create pairs after the first join. Two passes
    // are enough for ordinary book prose while remaining intentionally conservative.
    for(let pass=0;pass<2;pass++){
      const result=joinWrappedParagraphLines(text);
      text=result.text; changes+=result.changes;
      if(!result.changes)break;
    }
  }

  if(rules.has("empty_lines")){
    const next=text.replace(/^[ \t]+$/gm, "").replace(/\n[ \t]*\n(?:[ \t]*\n)+/g,"\n\n");
    if(next!==text){changes++;text=next}
  }

  if (rules.has("whitespace")) {
    const next = text.replace(/[ \t]+\n/g, "\n").replace(/[ \t]{2,}/g, " ").trim();
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

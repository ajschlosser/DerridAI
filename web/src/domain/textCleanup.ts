/* Copyright 2026 Aaron John Schlosser, PhD. */
export type TextCleanupRule = "page_numbers" | "repeated_short_lines" | "line_hyphenation" | "paragraph_lines" | "empty_lines" | "ocr_artifacts" | "whitespace";
export type TextCleanupPreview = { text: string; removed: string[]; changes: number };

const PAGE_NUMBER_RE = /^\s*(?:page\s+)?(?:[ivxlcdm]+|\d{1,4})\s*$/i;
const LIST_OR_QUOTE_RE = /^\s*(?:[-*•]|\d+[.)]|[a-z][.)]|[ivxlcdm]+[.)]|[>»«“”"'])\s*/i;
const HEADINGISH_RE = /^\s*(?:[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 '\u2019\-–—:;,.]{3,}|.{0,80}:)\s*$/u;
// eslint-disable-next-line no-useless-escape -- SA-14: preserve legacy matching/serialization until dedicated text fixtures cover it.
const SENTENCE_END_RE = /[.!?…:;][\]\)\}"'»”’]*\s*$/u;
const LOWERCASE_START_RE = /^\s*[a-zà-öø-ÿ]/u;
const OCR_GARBAGE_RE = /(?:�|[|¦]{3,}|[_~^]{4,}|(?:[^\p{L}\p{N}\s.,;:!?()'"–—-]){5,})/u;
const OCR_BOILERPLATE_RE = /(?:downloaded\s+from|all\s+use\s+subject\s+to|digitized\s+by\s+the\s+internet\s+archive|created\s+from\s+.+ebooks|ebook\s+central|jstor\.org|proquest\s+ebook)/iu;

function looksLikePoetryOrQuotation(lines: string[]): boolean {
  const meaningful = lines.map(line=>line.trim()).filter(Boolean);
  if (meaningful.length < 4) return false;
  const short = meaningful.filter(line=>line.length<=52).length;
  const quoted = meaningful.filter(line=>/^["“‘'>«]/u.test(line)).length;
  return short/meaningful.length>=0.72 || quoted/meaningful.length>=0.5;
}

/** Repair PDF line wrapping conservatively while preserving poetry, lists, headings,
 * and explicit quotations. The immutable extracted source is never changed here. */
function joinWrappedParagraphLines(text: string): {text:string; changes:number} {
  const chunks=text.split(/(\n\s*\n)/);
  let changes=0;
  const output=chunks.map(chunk=>{
    if(!chunk || /^\n\s*\n$/.test(chunk))return chunk;
    const lines=chunk.split(/\r?\n/);
    if(looksLikePoetryOrQuotation(lines))return chunk;
    const out:string[]=[];
    for(let i=0;i<lines.length;i++){
      const current=lines[i].trimEnd();
      const next=lines[i+1]?.trimStart();
      if(next===undefined){out.push(current);continue}
      const shouldJoin=Boolean(
        current.trim() && next.trim() &&
        !SENTENCE_END_RE.test(current) &&
        !LIST_OR_QUOTE_RE.test(current) && !LIST_OR_QUOTE_RE.test(next) &&
        !HEADINGISH_RE.test(current) && !HEADINGISH_RE.test(next) &&
        (LOWERCASE_START_RE.test(next) || current.length>=45)
      );
      if(shouldJoin){
        out.push(current.endsWith("-")&&LOWERCASE_START_RE.test(next)?`${current.slice(0,-1)}${next}`:`${current} ${next}`);
        i+=1;changes+=1;
      }else out.push(lines[i]);
    }
    return out.join("\n");
  });
  return {text:output.join(""),changes};
}

function looksLikeOcrArtifact(line:string):boolean{
  const value=line.trim();if(!value)return false;
  if(OCR_GARBAGE_RE.test(value)||OCR_BOILERPLATE_RE.test(value))return true;
  let printable=0;
  for(const ch of value){if(/[\p{L}\p{N}\s.,;:!?()[\]{}'"–—-]/u.test(ch))printable+=1}
  return value.length>=5 && printable/Math.max(1,value.length)<0.55;
}

export function cleanupText(input: string, rules: Set<TextCleanupRule>, recurringLines: string[] = [], documentTerms: string[] = []): TextCleanupPreview {
  let text = String(input || "");
  const removed: string[] = [];
  let changes = 0;
  const recurring = new Set(recurringLines.map(v => v.trim().toLocaleLowerCase()).filter(Boolean));
  const terms = new Set(documentTerms.map(v => v.trim().toLocaleLowerCase()).filter(v => v.length >= 3));

  if (rules.has("ocr_artifacts")) {
    const next = text
      // eslint-disable-next-line no-misleading-character-class -- SA-15: OCR Unicode matching needs corpus fixtures before changing character semantics.
      .replace(/[\u00ad\u200b\u200c\u200d\ufeff]/gu, "")
      .replace(/ﬁ/gu, "fi").replace(/ﬂ/gu, "fl").replace(/ﬀ/gu, "ff").replace(/ﬃ/gu, "ffi").replace(/ﬄ/gu, "ffl")
      .replace(/\f/gu, "\n");
    if (next !== text) { changes++; text = next; }
  }

  if (rules.has("line_hyphenation")) {
    const next = text.replace(/(?<=\p{L})-\s*\n\s*(?=\p{L})/gu, "");
    if (next !== text) { changes++; text = next; }
  }

  if (rules.has("page_numbers") || rules.has("repeated_short_lines") || rules.has("ocr_artifacts")) {
    const lines = text.split(/\r?\n/);
    const kept: string[] = [];
    const meaningfulIndexes=lines.map((line,index)=>line.trim()?index:-1).filter(index=>index>=0);
    const boundaryIndexes=new Set([...meaningfulIndexes.slice(0,3),...meaningfulIndexes.slice(-3)]);
    for (const [index,line] of lines.entries()) {
      const normalized = line.trim().toLocaleLowerCase();
      const pageNumber = rules.has("page_numbers") && boundaryIndexes.has(index) && PAGE_NUMBER_RE.test(line);
      const recurringLine = rules.has("repeated_short_lines") && boundaryIndexes.has(index) && normalized.length > 0 && normalized.length <= 120 && (recurring.has(normalized) || terms.has(normalized));
      const ocrArtifact = rules.has("ocr_artifacts") && looksLikeOcrArtifact(line);
      if (pageNumber || recurringLine || ocrArtifact) { removed.push(line.trim()); changes++; }
      else kept.push(line);
    }
    text = kept.join("\n");
  }

  if(rules.has("paragraph_lines")){
    for(let pass=0;pass<4;pass++){
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

export function recurringShortLines(texts: string[], minimumOccurrences = 2): string[] {
  const counts = new Map<string, { count: number; display: string }>();
  for (const text of texts) {
    const seen = new Set<string>();
    const meaningful=String(text||"").split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
    for (const display of [...meaningful.slice(0,3),...meaningful.slice(-3)]) {
      const key = display.toLocaleLowerCase();
      if (!key || key.length > 120 || PAGE_NUMBER_RE.test(display) || seen.has(key)) continue;
      seen.add(key);
      const prior = counts.get(key) || { count: 0, display };
      prior.count += 1;
      counts.set(key, prior);
    }
  }
  return Array.from(counts.values()).filter(item => item.count >= minimumOccurrences).sort((a,b)=>b.count-a.count).map(item => item.display).slice(0,80);
}

const LIGATURES: Record<string, string> = { "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "ft", "ﬆ": "st" };

/** Undo PDF-extraction ligatures, soft hyphens, zero-width marks, and mid-word line breaks. Used by the
 * single-click OCR cleanup action (distinct from the multi-rule cleanupText dialog above). */
export function stripLigaturesAndArtifacts(text: unknown): { text: string; changed: boolean } {
  const before = String(text ?? "");
  const s = before
    .replace(/[ﬀﬁﬂﬃﬄﬅﬆ]/g, (c) => LIGATURES[c] || c)
    .replace(/\u00ad/g, "")
    // eslint-disable-next-line no-misleading-character-class -- SA-15: OCR Unicode matching needs corpus fixtures before changing character semantics.
    .replace(/[\u200b\u200c\u200d\u2060\ufeff\ufffe\uffff]/g, "")
    .replace(/([A-Za-zÀ-ÖØ-öø-ÿ])-[ \t]*\r?\n[ \t]*([a-zà-öø-ÿ])/g, "$1$2")
    .replace(/\r\n/g, "\n");
  return { text: s, changed: s !== before };
}

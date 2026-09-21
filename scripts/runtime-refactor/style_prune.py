"""Remove style.css rules that can never match (run from web/, after style_audit.py has written /tmp/style_lists.json).

A rule is removed when every selector in its list requires at least one class that no source file uses, literally or
through a dynamic prefix (`"status-"+x`, `pie-series-${i}`). Rules with any live selector are left exactly as they are.
Empty @media blocks left behind are removed too. Comments are kept; only whole rules go.
"""
import json
import os
import re
import sys

CSS = "src/style.css"
raw = open(CSS).read()
lists = json.load(open("/tmp/style_lists.json"))
unused = set(lists["unused"])

# dynamic class prefixes anywhere in the sources
prefixes = set()
for root in ("src", "index.html"):
    paths = [root] if os.path.isfile(root) else [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs]
    for p in paths:
        if p == CSS or not p.endswith((".vue", ".ts", ".js", ".html")):
            continue
        text = open(p, errors="ignore").read()
        prefixes.update(re.findall(r"([a-z][a-z0-9-]*-)\$\{", text))
        prefixes.update(re.findall(r"[\"'`]([a-z][a-z0-9-]*-)[\"'`]\s*\+", text))
        prefixes.update(re.findall(r"\+\s*[\"'`]-?([a-z][a-z0-9-]+)[\"'`]", text))  # "x"+"suffix" style
dead = {c for c in unused if not any(c.startswith(p) for p in prefixes if len(p) >= 3)}
print("unused", len(unused), "kept because of dynamic prefixes", len(unused) - len(dead), file=sys.stderr)

masked = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), raw, flags=re.S)
class_re = re.compile(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)")


def selector_is_dead(sel):
    cleaned = re.sub(r"\[[^\]]*\]", "", sel)
    return any(c in dead for c in class_re.findall(cleaned))


def matching_brace(text, i):
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return len(text) - 1


removals = []  # (start, end) in raw


def walk(start, end):
    i = start
    stmt_start = start
    while i < end:
        c = masked[i]
        if c == "{":
            head = masked[stmt_start:i].strip()
            close = matching_brace(masked, i)
            if head.startswith("@media") or head.startswith("@supports") or head.startswith("@container"):
                walk(i + 1, close)
            elif head.startswith("@"):
                pass
            else:
                sels = [s for s in head.split(",")]
                if sels and all(selector_is_dead(s) for s in sels):
                    removals.append((stmt_start + (len(masked[stmt_start:i]) - len(masked[stmt_start:i].lstrip())), close + 1))
            i = close
            stmt_start = i + 1
        elif c == "}":
            stmt_start = i + 1
        i += 1


walk(0, len(masked))
out = raw
for a, b in sorted(removals, reverse=True):
    out = out[:a] + out[b:]
# drop @media blocks emptied by the removals
prev = None
while prev != out:
    prev = out
    out = re.sub(r"@media[^{}]*\{\s*\}", "", out)
out = re.sub(r"\n{3,}", "\n\n", out)
open(CSS, "w").write(out)
print("removed rules:", len(removals), "lines before/after:", raw.count("\n"), out.count("\n"), file=sys.stderr)

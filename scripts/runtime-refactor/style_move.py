"""Move global rules that belong to exactly one Vue component into that component's <style scoped> block.

Run from web/. Usage: style_move.py [--dry-run] [--only path/to/File.vue ...]

A class is movable to component F when
  * F is the only source file that mentions it (Vue templates/scripts, runtime, domain, tests, stories all counted),
  * F has no v-html (its markup could come from elsewhere, and scoped styles do not reach v-html content),
  * the class is not built dynamically anywhere (no matching `prefix-${...}` / "prefix-"+x pattern), and
  * every rule in style.css that mentions the class involves only classes that are themselves movable to F (a fixpoint),
    so no rule outside F can tie with or override the moved one and the cascade stays as it was.
Rules move whole, in their original order, with their @media wrapper; classless rules and rules that touch anything else
stay. Nothing is rewritten: a moved rule is the same text, now scoped.
"""
import os
import re
import sys
from collections import defaultdict

CSS = "src/style.css"
dry = "--dry-run" in sys.argv
only = set()
if "--only" in sys.argv:
    only = set(sys.argv[sys.argv.index("--only") + 1 :])
raw = open(CSS).read()
masked = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), raw, flags=re.S)
class_re = re.compile(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)")


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


rules = []  # dict(start,end,selector,media(list of head strings))


def walk(start, end, media):
    i = start
    stmt = start
    while i < end:
        c = masked[i]
        if c == "{":
            head = masked[stmt:i].strip()
            close = matching_brace(masked, i)
            if head.startswith(("@media", "@supports", "@container")):
                walk(i + 1, close, media + [head])
            elif not head.startswith("@"):
                lead = len(masked[stmt:i]) - len(masked[stmt:i].lstrip())
                rules.append({"start": stmt + lead, "end": close + 1, "selector": head, "media": media, "text": raw[stmt + lead : close + 1]})
            i = close
            stmt = i + 1
        elif c == "}":
            stmt = i + 1
        i += 1


walk(0, len(masked), [])


def rule_classes(sel):
    return set(class_re.findall(re.sub(r"\[[^\]]*\]", "", sel)))


for r in rules:
    r["classes"] = rule_classes(r["selector"])

# source usage
files = []
for root in ("src", "tests", "index.html"):
    paths = [root] if os.path.isfile(root) else [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs]
    for p in paths:
        if p == CSS or not p.endswith((".vue", ".ts", ".js", ".html")):
            continue
        files.append((p, open(p, errors="ignore").read()))


def strip_style(p, t):
    return re.sub(r"<style[^>]*>.*?</style>", "", t, flags=re.S) if p.endswith(".vue") else t


dyn_prefixes = set()
for p, t in files:
    t = strip_style(p, t)
    dyn_prefixes.update(re.findall(r"([a-z][a-z0-9-]*-)\$\{", t))
    dyn_prefixes.update(re.findall(r"[\"'`]([a-z][a-z0-9-]*-)[\"'`]\s*\+", t))

all_classes = set().union(*(r["classes"] for r in rules)) if rules else set()
owner = {}
for c in all_classes:
    pat = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(c))
    users = {p for p, t in files if pat.search(strip_style(p, t))}
    owner[c] = users


def owner_file(c):
    users = owner[c]
    if len(users) != 1:
        return None
    (p,) = users
    if not p.endswith(".vue"):
        return None
    if any(c.startswith(x) for x in dyn_prefixes if len(x) >= 3):
        return None
    text = open(p).read()
    if "v-html" in text:
        return None
    return p


# Classes that some component already styles itself: a global rule and a scoped rule for the same class interact
# (specificity, order, !important), and moving the global one changes which wins. Leave those alone.
in_component_styles = set()
for p, t in files:
    if p.endswith(".vue"):
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", t, flags=re.S):
            in_component_styles.update(class_re.findall(m.group(1)))

cand = {c: owner_file(c) for c in all_classes if c not in in_component_styles}
cand = {c: f for c, f in cand.items() if f and (not only or f in only)}

# fixpoint: a class stays a candidate only if every rule mentioning it has all its classes candidates for the same file
by_class = defaultdict(list)
for r in rules:
    for c in r["classes"]:
        by_class[c].append(r)
changed = True
while changed:
    changed = False
    for c in list(cand):
        f = cand[c]
        for r in by_class[c]:
            if not all(cand.get(k) == f for k in r["classes"]):
                del cand[c]
                changed = True
                break

moves = defaultdict(list)
for r in rules:
    if r["classes"] and all(k in cand for k in r["classes"]):
        fs = {cand[k] for k in r["classes"]}
        if len(fs) == 1:
            moves[next(iter(fs))].append(r)

total = sum(len(v) for v in moves.values())
print(f"{len(moves)} components, {total} rules of {len(rules)} would move", file=sys.stderr)
for f, rs in sorted(moves.items(), key=lambda kv: -len(kv[1]))[:40]:
    print(f"  {len(rs):4d} rules -> {f}", file=sys.stderr)
if dry:
    sys.exit(0)

# write components
for f, rs in moves.items():
    rs.sort(key=lambda r: r["start"])
    parts = []
    for r in rs:
        text = r["text"].strip()
        for head in reversed(r["media"]):
            text = head + " {\n" + text + "\n}"
        parts.append(text)
    block = "\n".join(parts)
    src = open(f).read()
    m = list(re.finditer(r"<style scoped[^>]*>", src))
    if m:
        # append inside the last scoped style block
        end = src.rindex("</style>")
        src = src[:end].rstrip("\n") + "\n" + block + "\n" + src[end:]
    else:
        src = src.rstrip("\n") + "\n\n<style scoped>\n" + block + "\n</style>\n"
    open(f, "w").write(src)

# remove from style.css
cuts = sorted((r["start"], r["end"]) for rs in moves.values() for r in rs)
out = raw
for a, b in reversed(cuts):
    out = out[:a] + out[b:]
prev = None
while prev != out:
    prev = out
    out = re.sub(r"@media[^{}]*\{\s*\}", "", out)
out = re.sub(r"\n{3,}", "\n\n", out)
open(CSS, "w").write(out)
print(f"moved {total} rules; style.css {raw.count(chr(10))} -> {out.count(chr(10))} lines", file=sys.stderr)

"""Audit of web/src/style.css (run from web/): who uses each class, what is dead, what is duplicated.

Prints a JSON summary. It is a static approximation: a class built dynamically (`pie-series-${i}`) is matched by its
prefix; classes set only by code that concatenates arbitrary strings can be missed, so "unused" means "no literal or
prefix match", to be confirmed before deleting.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

CSS = "src/style.css"
raw = open(CSS).read()
css = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)


def parse(text):
    """Yield (at_rule_context, selector_text, body) for every style rule, flattening @media/@supports."""
    out = []
    i = 0
    stack = []
    buf = ""
    while i < len(text):
        c = text[i]
        if c == "{":
            head = buf.strip()
            buf = ""
            if head.startswith("@media") or head.startswith("@supports") or head.startswith("@container") or head.startswith("@layer"):
                stack.append(("at", head))
            elif head.startswith("@"):
                # @keyframes, @font-face, ... skip the block
                depth = 1
                j = i + 1
                while j < len(text) and depth:
                    depth += (text[j] == "{") - (text[j] == "}")
                    j += 1
                i = j - 1
            else:
                depth = 1
                j = i + 1
                while j < len(text) and depth:
                    depth += (text[j] == "{") - (text[j] == "}")
                    j += 1
                body = text[i + 1 : j - 1]
                ctx = " | ".join(h for k, h in stack if k == "at")
                out.append((ctx, head, body))
                i = j - 1
        elif c == "}":
            if stack:
                stack.pop()
            buf = ""
        else:
            buf += c
        i += 1
    return out


rules = parse(css)
class_re = re.compile(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)")
css_classes = defaultdict(int)
for ctx, sel, body in rules:
    for sub in sel.split(","):
        for m in class_re.finditer(re.sub(r"\[[^\]]*\]|:[a-z-]+\([^)]*\)", "", sub)):
            css_classes[m.group(1)] += 1

# source corpus
roots = ["src", "index.html", "tests"]
files = {"vue": [], "runtime": [], "domain": [], "other": [], "tests": []}
for root in roots:
    paths = [root] if os.path.isfile(root) else [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs]
    for p in paths:
        if p == CSS or not p.endswith((".vue", ".ts", ".js", ".html")):
            continue
        text = open(p, errors="ignore").read()
        if p.startswith("tests"):
            files["tests"].append((p, text))
        elif p.endswith(".vue"):
            files["vue"].append((p, text))
        elif p.startswith("src/runtime") or p.startswith("src/domain"):
            files["runtime" if p.startswith("src/runtime") else "domain"].append((p, text))
        else:
            files["other"].append((p, text))


def token_in(text, cls):
    return re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(cls), text) is not None


def prefix_of(cls):
    m = re.match(r"^(.*-)(\d+|[a-z]|[A-Z])$", cls)
    return m.group(1) if m else None


usage = {}
scoped_classes = set()
for p, text in files["vue"]:
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", text, flags=re.S):
        for c in class_re.findall(m.group(1)):
            scoped_classes.add(c)
for cls in css_classes:
    where = set()
    pre = prefix_of(cls)
    for kind in ("vue", "runtime", "domain", "other"):
        for p, text in files[kind]:
            # strip style blocks from Vue files so a scoped rule does not count as use
            body = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S) if kind == "vue" else text
            if token_in(body, cls) or (pre and re.search(re.escape(pre) + r"\$\{", body)):
                where.add(kind)
                break
    if not where:
        for p, text in files["tests"]:
            if token_in(text, cls):
                where.add("tests")
                break
    usage[cls] = where

by_owner = Counter()
for cls, w in usage.items():
    key = "unused" if not w else "+".join(sorted(w))
    by_owner[key] += 1

runtime_only = sorted(c for c, w in usage.items() if w and w <= {"runtime", "domain"} and "vue" not in w)
vue_only = sorted(c for c, w in usage.items() if w == {"vue"})
both = sorted(c for c, w in usage.items() if "vue" in w and w & {"runtime", "domain"})
unused = sorted(c for c, w in usage.items() if not w)
tests_only = sorted(c for c, w in usage.items() if w == {"tests"})

# rule-level metrics
colors = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)", css)
var_uses = re.findall(r"var\(--[a-z0-9-]+", css)
important = css.count("!important")
id_selectors = sum(1 for _, s, _ in rules if re.search(r"#[a-zA-Z]", re.sub(r"\[[^\]]*\]", "", s)))
media = Counter(ctx for ctx, _, _ in rules if ctx)
selectors = Counter(s.strip() for _, s, _ in rules)
dup_selectors = sorted((s for s, n in selectors.items() if n > 1), key=lambda s: -selectors[s])
complex_sel = sum(1 for _, s, _ in rules if len(re.findall(r"[ >+~]", s.strip())) >= 3)
tokens_defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", open("src/styles/tokens.css").read()))
tokens_used = set(m[4:] if m.startswith("var(") else m for m in [v for v in var_uses])
tokens_used = {t for t in tokens_used}
undefined_vars = sorted({v for v in tokens_used if v not in tokens_defined and v not in set(re.findall(r"(--[a-z0-9-]+)\s*:", css))})

# classes styled both globally and in scoped component styles
overlap = sorted(c for c in css_classes if c in scoped_classes)

# section headers (block comments that look like titles)
sections = re.findall(r"/\*\s*([A-Za-z0-9 &/\-:.,()]+?)\s*\*/", raw)
sections = [s for s in sections if 3 < len(s) < 70][:60]

summary = {
    "lines": raw.count("\n") + 1,
    "rules": len(rules),
    "distinct_classes": len(css_classes),
    "classes_by_owner": dict(by_owner.most_common()),
    "runtime_only_classes": len(runtime_only),
    "vue_only_classes": len(vue_only),
    "shared_vue_and_runtime_classes": len(both),
    "unused_classes": len(unused),
    "test_only_classes": len(tests_only),
    "hardcoded_colors": len(colors),
    "distinct_hardcoded_colors": len(set(colors)),
    "var_uses": len(var_uses),
    "important": important,
    "id_selectors": id_selectors,
    "long_selectors_3plus_combinators": complex_sel,
    "media_queries": dict(media.most_common(12)),
    "duplicate_selectors": len(dup_selectors),
    "top_duplicate_selectors": dup_selectors[:12],
    "tokens_defined": len(tokens_defined),
    "css_vars_used_but_undefined": undefined_vars[:20],
    "classes_also_in_scoped_styles": len(overlap),
    "overlap_sample": overlap[:25],
}
detail = sys.argv[1] if len(sys.argv) > 1 else ""
if detail == "lists":
    json.dump({"runtime_only": runtime_only, "vue_only": vue_only, "shared": both, "unused": unused, "tests_only": tests_only, "overlap": overlap}, open("/tmp/style_lists.json", "w"), indent=1)
print(json.dumps(summary, indent=1))

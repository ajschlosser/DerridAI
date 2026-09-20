"""Usage (from web/): mk_factory.py <module> <factoryName> <header> <imports> <deps-type> <destructure> <edits-json> <fn1,fn2,...> [--const NAME ...]

Copies the named functions (and optional top-level consts) VERBATIM from runtime.js into a factory function
`export function <factoryName>(deps) { const {<destructure>}=deps; ...; return {fn1,fn2,...}; }` in
src/domain/<module>.ts, applying only the explicit string edits given as JSON {"from":"to"} (used to turn
state/hoisted-helper references into deps.* calls). Removes them from runtime.js and inserts

    const {fn1,fn2,...}=<factoryName>({...});

is NOT generated: add the call site by hand, so the dependency wiring is reviewed.
"""
import json
import re
import sys

module, factory, header, imports, deps_type, destructure, edits_json, fns = sys.argv[1:9]
consts = []
if "--const" in sys.argv:
    consts = sys.argv[sys.argv.index("--const") + 1 :]
edits = json.loads(edits_json)
names = fns.split(",")
p = "src/runtime/runtime.js"
s = open(p).read()


def cut(s, name, is_const=False):
    if is_const:
        m = re.search(r"^const %s\s*=" % re.escape(name), s, re.M)
        a = m.start()
        b = s.index("\n};\n", a) + 4
        return s[:a] + s[b:], s[a:b]
    m = re.search(r"^(async )?function %s\(" % re.escape(name), s, re.M)
    if not m:
        sys.exit("not found " + name)
    a = m.start()
    le = s.index("\n", a)
    first = s[a:le]
    if first.rstrip().endswith("}") and first.count("{") == first.count("}"):
        b = le + 1
    else:
        b = s.index("\n}\n", a) + 3
    return s[:a] + s[b:], s[a:b]


chunks = []
for c in consts:
    s, text = cut(s, c, True)
    chunks.append(text)
for n in names:
    s, text = cut(s, n)
    chunks.append(text)
body = "".join(t if t.endswith("\n") else t + "\n" for t in chunks)
for a, b in edits.items():
    body = body.replace(a, b)
indented = "\n".join(("  " + line if line.strip() else line) for line in body.splitlines())
out = (
    "/* Copyright 2026 Aaron John Schlosser, PhD. */\n"
    + imports
    + "\n\n"
    + header
    + "\n\n"
    + deps_type
    + "\n\nexport function %s(deps: Deps) {\n  const {%s} = deps;\n" % (factory, destructure)
    + indented
    + "\n  return {%s};\n}\n" % ",".join(names)
)
open("src/domain/%s.ts" % module, "w").write(out)
open(p, "w").write(s)
print("moved", len(names), "functions and", len(consts), "consts")

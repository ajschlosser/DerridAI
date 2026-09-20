"""Usage: mv_fn.py <module.ts> <header comment> <imports...> -- name:signature ...
Copies named top-level functions VERBATIM (bodies untouched) from runtime.js into src/domain/<module>.ts,
replacing only the signature line with a typed one, exporting them, and removing them from runtime.js.
Signatures come from argv as  name=typed signature line (e.g. 'lineChart=function lineChart(series: Row[], title: string, legendLabel: string = title): string {')"""
import re
import sys

module = sys.argv[1]
header = sys.argv[2]
imports = sys.argv[3]  # ts import lines, '\n'-separated, may be ''
specs = dict(a.split("=", 1) for a in sys.argv[4:])
p = "src/runtime/runtime.js"
s = open(p).read()
out = []
for name, sig in specs.items():
    m = re.search(r"^(async )?function %s\(" % re.escape(name), s, re.M)
    if not m:
        sys.exit("not found " + name)
    start = m.start()
    line_end = s.index("\n", start)
    first = s[start:line_end]
    if first.rstrip().endswith("}") and first.count("{") == first.count("}"):
        end = line_end + 1
        body = "\n".join(first.splitlines()[1:])
        text = sig.replace("{", "{ ", 1) if False else first
        # one-line function: replace the signature part before its first '{'
        idx = first.index("{", first.index(")"))
        text = "export " + sig.rstrip("{ ").rstrip() + " " + first[idx:]
    else:
        end = s.index("\n}\n", start) + 3
        lines = s[start:end].splitlines()
        text = "export " + sig + "\n" + "\n".join(lines[1:]) + "\n"
    out.append(text)
    s = s[:start] + s[end:]
ts = "/* Copyright 2026 Aaron John Schlosser, PhD. */\n" + imports + "\n\n" + header + "\n\n" + "\n".join(out)
open("src/domain/%s.ts" % module, "w").write(ts)
names = ", ".join(sorted(specs))
anchor = 'import { esc, icon } from "../domain/html";'
s = s.replace(anchor, anchor + '\nimport { %s } from "../domain/%s";' % (names, module), 1)
open(p, "w").write(s)
print("moved", names)

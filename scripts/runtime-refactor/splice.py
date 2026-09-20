"""Usage: splice.py <module> <name1,name2,...>
Removes the named top-level functions from runtime.js (each ends at the first line that is exactly '}'
or is a one-line function) and adds an import from ../domain/<module>."""
import re
import sys

module, names = sys.argv[1], sys.argv[2].split(",")
p = "src/runtime/runtime.js"
s = open(p).read()
for name in names:
    m = re.search(r"^(async )?function %s\(" % re.escape(name), s, re.M)
    if not m:
        sys.exit("not found: " + name)
    start = m.start()
    line_end = s.index("\n", start)
    first = s[start:line_end]
    if first.rstrip().endswith("}") and first.count("{") == first.count("}"):
        end = line_end + 1
    else:
        end = s.index("\n}\n", start) + 3
    s = s[:start] + s[end:]
imp = 'import { %s } from "../domain/%s";\n' % (", ".join(sorted(names)), module)
anchor = 'import { fullCitation,'
s = s.replace(anchor, imp + anchor, 1)
open(p, "w").write(s)
print("removed", len(names))

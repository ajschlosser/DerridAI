import re

s = open("src/runtime/runtime.js").read()
starts = [(m.start(), m.group(2)) for m in re.finditer(r"^(async )?function ([A-Za-z0-9_]+)\(", s, re.M)]
funcs = {}
for i, (a, name) in enumerate(starts):
    b = starts[i + 1][0] if i + 1 < len(starts) else len(s)
    funcs[name] = s[a:b]
impure = re.compile(r"\bstate\b|\bdocument\b|\bwindow\b|\bapi\(|\btoast\(|\blocalStorage\b|\bnavigator\b|\bicon\(|\btr\(|\btrf\(|innerHTML|\bhasCapability\b|\bisResearcher\b|\bmain\b|\bfetch\(")
names = set(funcs)
rows = []
for name, body in funcs.items():
    if impure.search(body):
        continue
    deps = sorted({n for n in names if n != name and re.search(r"\b%s\(" % re.escape(n), body)})
    rows.append((len(body.splitlines()), name, deps))
rows.sort(reverse=True)
for n, name, deps in rows[:60]:
    print(f"{n:4d} {name}  <- {','.join(deps)}"[:170])
print(len(rows), "pure-looking functions of", len(funcs))

"""Usage (from web/): deps.py fn1,fn2,... -- lists the runtime.js top-level names each function uses, and state fields."""
import re, sys
s = open("src/runtime/runtime.js").read()
tops = {m.group(2) for m in re.finditer(r"^(async )?function (\w+)\(", s, re.M)} | {m.group(1) for m in re.finditer(r"^(?:const|let) (\w+)\s*=", s, re.M)}
group = sys.argv[1].split(",")
for n in group:
    m = re.search(r"^(async )?function %s\(" % n, s, re.M)
    if not m: print(n, "-"); continue
    a = m.start(); le = s.index("\n", a); first = s[a:le]
    b = le + 1 if first.rstrip().endswith("}") and first.count("{") == first.count("}") else s.index("\n}\n", a) + 3
    body = s[a:b]
    used = sorted({t for t in tops if t != n and t not in group and re.search(r"\b%s\b" % t, body)})
    st = sorted(set(re.findall(r"state\.(\w+)", body)))
    print(f"{n}({len(body.splitlines())}L) uses={used} state={st}")

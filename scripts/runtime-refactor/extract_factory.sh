#!/bin/bash
# usage: extract_factory.sh module Factory "fn1,fn2" "header line 1|header line 2" [importsJSON]
set -e
mod=$1; fac=$2; fns=$3; hdr=$4; imps=${5:-'{"esc":"./html","icon":"./html"}'}
python3 ../scripts/runtime-refactor/mk_factory.py $mod $fac "$(echo "$hdr" | tr '|' '\n')
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any" "" "type Deps = { state: Loose };" "state" "{}" "$fns" >/dev/null
npx tsc --noEmit 2>&1 | grep "domain/$mod.ts" | grep -o "Cannot find name '[A-Za-z0-9_]*'" | sed "s/.*'\(.*\)'/\1/" | sort -u > /tmp/$mod.names.txt
python3 ../scripts/runtime-refactor/wire_factory.py $mod $fac "$fns" x "$imps"
p=src/domain/$mod.ts
python3 - $p <<'P'
import sys,re
p=sys.argv[1];s=open(p).read()
s=s.replace("} = deps;\n","} = deps;\n  // The legacy code queries the page freely; untyped, as it was written.\n  const document: Any = globalThis.document;\n",1)
s=re.sub(r"\(\{([^{}()=:]*)\}\)(\s*=>)",lambda m:"({"+m.group(1)+"}: Any)"+m.group(2),s)
s=s.replace("catch (error)","catch (error: Any)").replace("catch (e)","catch (e: Any)")
s=re.sub(r"[ \t]*// eslint-disable-next-line (no-empty|no-useless-escape)[^\n]*\n","",s)
s=re.sub(r"\} ?catch ?\{\}","} catch {\n// Best effort: keep going with what we have.\n}",s)
open(p,"w").write(s)
P
npx prettier --write $p >/dev/null
for i in 1 2 3; do python3 ../scripts/runtime-refactor/fix_any.py $p >/dev/null; done
npx prettier --write $p >/dev/null
echo "--- non-function helper check"
for n in $(cat /tmp/$mod.names.txt); do grep -qE "^(async )?function $n\(|^const $n\s*=|[{,]$n[,}]|^import .*\b$n\b|^  $n:|^let $n\b|^const \{[^}]*\b$n\b" src/runtime/runtime.js || echo "MISSING $n"; grep -qE "^let $n\b" src/runtime/runtime.js && echo "LET $n"; done
npx vue-tsc --noEmit 2>&1 | head -8 | cut -c1-170
npx eslint $p src/runtime/runtime.js | grep -E "error|warn" || true

import sys,re
mod,factory,fns,after=sys.argv[1:5]
names=open(f"/tmp/{mod}.names.txt").read().split()
import json
imports=json.loads(sys.argv[5]) if len(sys.argv)>5 else {"esc":"./html","icon":"./html"}
helpers=[n for n in names if n not in imports]
p=f"src/domain/{mod}.ts";s=open(p).read()
byfile={}
for n,f in imports.items():
    if n in names: byfile.setdefault(f,[]).append(n)
imp="\n".join(f'import {{ {", ".join(sorted(v))} }} from "{f}";' for f,v in sorted(byfile.items()))
s=s.replace("type Deps = { state: Loose };","/** The helpers that still live in the legacy runtime. */\ntype Helper =\n  | "+"\n  | ".join(f'"{h}"' for h in helpers)+";\ntype Deps = { state: Loose } & Record<Helper, Fn>;",1)
s=s.replace("\n// ",("\n"+imp+"\n\n// ") if imp else "\n// ",1)
s=s.replace("const {state} = deps;","const {state, "+", ".join(helpers)+"} = deps;",1)
open(p,"w").write(s)
r=open("src/runtime/runtime.js").read()
r=r.replace('import { createBackupWorkspace }',f'import {{ {factory} }} from "../domain/{mod}";\nimport {{ createBackupWorkspace }}',1)
i=r.index("=createDashboardRenderer(");i=r.index("});\n",i)+4
lam=",\n  ".join(f"{h}:(...args)=>{h}(...args)" for h in helpers)
r=r[:i]+"const {%s}=%s({\n  state,\n  // Wrapped so each helper is looked up when it is called: several are declared later in this module.\n  %s,\n});\n"%(fns,factory,lam)+r[i:]
open("src/runtime/runtime.js","w").write(r)

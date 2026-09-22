import re,subprocess,sys
p=sys.argv[1]; 
for rnd in range(4):
    out=subprocess.run("npx vue-tsc --noEmit 2>&1",shell=True,capture_output=True,text=True).stdout
    errs=[(int(m.group(1)),int(m.group(2)),m.group(3)) for m in re.finditer(re.escape(p)+r"\((\d+),(\d+)\): error TS7006: Parameter '(\w+)' implicitly",out)]
    if not errs: break
    lines=open(p).read().split("\n")
    for line,col,name in sorted(errs,reverse=True):
        l=lines[line-1]; i=col-1
        if l[i:i+len(name)]!=name: continue
        after=l[i+len(name):]
        # skip if next char is ':' (already typed)
        if after.startswith(":"): continue
        # for default values keep as-is: name = x -> name: Any = x
        lines[line-1]=l[:i+len(name)]+": Any"+after
    open(p,"w").write("\n".join(lines))
    print("round",rnd,"patched",len(errs))

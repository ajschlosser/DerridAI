import re,sys
p="src/runtime/runtime.js";s=open(p).read()
ex=s.index("\nexport {")
tot=0
while True:
    head,tail=s[:ex],s[ex:]
    blocks=[]
    for m in re.finditer(r"^(?:async )?function ([A-Za-z_$][\w$]*)\(",head,re.M):
        a=m.start();le=head.index("\n",a);first=head[a:le]
        if first.count("{")==first.count("}") and first.rstrip().endswith("}"): b=le+1
        else:
            k=head.find("\n}\n",a)
            if k<0: continue
            b=k+3
        blocks.append((m.group(1),a,b))
    dead=[]
    for n,a,b in blocks:
        rest=head[:a]+head[b:]+tail
        if not re.search(r"(?<![\w$.])"+re.escape(n)+r"(?![\w$])",rest): dead.append((n,a,b))
    if not dead: break
    for n,a,b in sorted(dead,key=lambda x:-x[1]): head=head[:a]+head[b:]
    tot+=len(dead);print("removed",len(dead),[d[0] for d in dead][:40])
    s=head+tail;ex=s.index("\nexport {")
open(p,"w").write(s);print("total",tot)

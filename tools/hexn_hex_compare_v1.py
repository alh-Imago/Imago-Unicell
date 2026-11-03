import sys, random, json, time; sys.path.insert(0,'/home/claude/hexn-wt/tools')
import hexn_pattern_designer_v10 as D, hexn_wrgrid_v21 as GS, hexn_wrgrid_hex_v1 as GH, hexn_hexgeom_v1 as HX
from multiprocessing import Pool
MIX={"sq7":{"UN":1,"AL":2,"JN":4,"BR":1,"MG":1},"hex7":{"UN":3,"AL":4,"JN":7,"BR":2,"MG":2},"hex7b":{"UN":2,"AL":3,"JN":6,"BR":2,"MG":1},"sq9":{"UN":2,"AL":3,"JN":6,"BR":3,"MG":2},"hex9":{"UN":4,"AL":5,"JN":11,"BR":4,"MG":3},"sq11":{"UN":4,"AL":5,"JN":10,"BR":3,"MG":3},"hex9b":{"UN":4,"AL":5,"JN":11,"BR":4,"MG":3},"hex9c":{"UN":4,"AL":5,"JN":11,"BR":4,"MG":3},"hex7c":{"UN":3,"AL":3,"JN":7,"BR":2,"MG":2}}
SIZE={"hex9b":9,"hex9c":9,"hex7c":7,"sq7":7,"hex7":7,"hex7b":7,"sq9":9,"hex9":9,"sq11":11}
OFF={"hex7":0,"hex7b":1,"hex9":0,"hex9b":1,"hex9c":2,"hex7c":2}
BIN=["add","sub","xor","min","max"]; UN=["shl","shr"]
def mk(N,rnd):
    ins=["x","y","z","w"][:rnd.choice([2,3,4])]; avail=list(ins); nodes=[]; k=rnd.choice([3,4,5])
    for i in range(k):
        r=rnd.random()
        if r<0.25 and len(avail)>=2:
            a,b=rnd.sample(avail,2); nodes.append(N("b%d"%i,"branch",[a,b],["lo%d"%i,"hi%d"%i],cfg=dict(route_lt=1,route_eq=1,route_gt=2,emit=3))); avail+=["lo%d"%i,"hi%d"%i]
        elif r<0.45: nodes.append(N("n%d"%i,rnd.choice(UN),[rnd.choice(avail)],k=rnd.randrange(1,5))); avail.append("n%d"%i)
        else:
            a,b=rnd.sample(avail,2); nodes.append(N("n%d"%i,rnd.choice(BIN),[a,b])); avail.append("n%d"%i)
    used=set(x for n in nodes for x in n.ins); outs=[o for n in nodes for o in (n.outs if n.outs else [n.name]) if o not in used]
    ins=[x for x in ins if x in used]
    return nodes,ins,outs
def one(args):
    kind,seed=args
    rnd=random.Random(seed)
    if kind.startswith("sq"):
        G=GS; base=D.make_base({"n":SIZE[kind],"counts":MIX[kind],"ram":"none"}); ct=base.type; R=C=SIZE[kind]
    else:
        G=GH; n=SIZE[kind]; GH.OFFSET=OFF[kind]; wc=GH.Grid12(n,n).work_cells(); seq=[]; cnt=dict(MIX[kind])
        while any(cnt.values()):
            for kk in list(cnt):
                if cnt[kk]: seq.append(kk); cnt[kk]-=1
        seq=(seq+["AL"]*len(wc))[:len(wc)]; ct={w:t for w,t in zip(wc,seq)}; R=C=n
    t=mk(G.Node9,rnd)
    try:
        P=G.plan10(t[0],t[1],t[2],R,C,ct,tries=10)
        ok,why=G.check_task(P,*t)
    except (RuntimeError, IndexError) as e: return (kind,seed,False,None)
    if not ok: return (kind,seed,False,None)
    iv={k:(37+13*i) for i,k in enumerate(t[1])}
    cap=G.simulate9(P,iv,t[2])
    first=max((v[0][0] for v in cap.values() if v),default=0)
    wires=len(P.g.used); work=len(P.g.work)
    return (kind,seed,True,dict(tick=first,wires=wires,work=work,chosen=sum(1 for i in P.g.work.values() if i["cfg"].get("fi") or i["cfg"].get("fo")),nodes=len(t[0])))
KINDS=('sq7','hex7','hex7b','hex7c','sq9','hex9','hex9b','hex9c','sq11')
if __name__=="__main__":
    N=int(sys.argv[1]) if len(sys.argv)>1 else 150
    jobs=[(k,s) for s in range(N) for k in KINDS]
    t0=time.time()
    with Pool(8) as p: res=p.map(one,jobs,chunksize=2)
    json.dump(res,open('/tmp/cmp_hex.json','w'))
    print("done",time.time()-t0)

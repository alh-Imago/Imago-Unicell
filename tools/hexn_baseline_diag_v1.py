"""Hex-N baseline comparison, DIAGNOSTICS (new file, 30 Oct 2026; Python model only). Companion of tools/hexn_baseline_v1.py. Part 1: where the detector loses accuracy (cap on the burst, silence, ties, answer rule). Part 2: coverage and precision of the detector against the nearest-template classifier given the SAME coverage. Run: python3 tools/hexn_baseline_diag_v1.py"""
import sys, os, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import hexn_baseline_v1 as B; R = B.R

def diag(seed,K,nb,q,S,per_test=100):
    rnd=random.Random(seed); tpl=R.templates(rnd,K,nb,4)
    tr=[(R.sample(rnd,tpl[c],q),c) for c in range(K) for _ in range(S)]; random.Random(seed+5).shuffle(tr)
    te=[(R.sample(rnd,tpl[c],q),c) for c in range(K) for _ in range(per_test)]
    m=R.train_bank([x for x,_ in tr],[c for _,c in tr],K,R.AW,S); rr=random.Random(seed+1)
    o=dict(cap6=0,silent=0,tie=0,uncap=0,argmax_tot=0,margin_rand=0)
    for x,c in te:
        tt=[R.tot(m["w"][k],x,m["cap"]) for k in range(K)]
        g=[R.burst(tt[k],m["thr"][k]) for k in range(K)]; a=R.answer(g); o["cap6"]+=(a==c)
        if max(g)==0: o["silent"]+=1
        elif g.count(max(g))>1: o["tie"]+=1
        u=[(tt[k]-m["thr"][k]) if (tt[k]>0 and tt[k]>=m["thr"][k]) else -99 for k in range(K)]
        mx=max(u); o["uncap"]+=(mx>-99 and u.count(mx)==1 and u.index(mx)==c)
        mx=max(tt); o["argmax_tot"]+=(tt.count(mx)==1 and tt.index(mx)==c)
        mm=[tt[k]-m["thr"][k] for k in range(K)]; mx=max(mm); cand=[k for k in range(K) if mm[k]==mx]; o["margin_rand"]+=(rr.choice(cand)==c)
    return {k:v/len(te) for k,v in o.items()}
def cov(seed,K,nb,q,S,per_test=100):
    rnd=random.Random(seed); tpl=R.templates(rnd,K,nb,4)
    tr=[(R.sample(rnd,tpl[c],q),c) for c in range(K) for _ in range(S)]; random.Random(seed+5).shuffle(tr)
    te=[(R.sample(rnd,tpl[c],q),c) for c in range(K) for _ in range(per_test)]
    m=R.train_bank([x for x,_ in tr],[c for _,c in tr],K,R.AW,S)
    mean=[[sum(x[j] for x,c in tr if c==k)/S for j in range(nb)] for k in range(K)]; tm=[[1 if v>=.5 else 0 for v in r] for r in mean]
    det=[];tmp=[]
    for x,c in te:
        a=R.answer(R.bursts(m,x)); det.append((a>=0,a==c))
        d=[sum(p!=q2 for p,q2 in zip(x,tm[k])) for k in range(K)]; mn=min(d); srt=sorted(d)
        tmp.append((mn, srt[1]-srt[0], d.index(mn)==c))
    n=len(te); answered=sum(a for a,_ in det); right=sum(r for _,r in det)
    order=sorted(range(n),key=lambda i:(-tmp[i][1],tmp[i][0]))[:answered]
    trt=sum(tmp[i][2] and tmp[i][1]>0 for i in order)
    return answered/n, right/max(1,answered), trt/max(1,answered), sum(1 for t in tmp if t[2] and t[1]>0)/n
if __name__ == "__main__":
    for K,nb,q,S in ((4,12,.15,16),(8,18,.15,16),(8,18,.25,4),(16,18,.15,16)):
        rs=[diag(s,K,nb,q,S) for s in range(25)]; tm=st.mean(B.one(s,K,nb,q,S)["tmpl"] for s in range(25))
        print(f"K={K} wires={nb} noise={q} S={S}: "+"  ".join(f"{k} {st.mean(r[k] for r in rs):.3f}" for k in rs[0])+f"  | nearest template {tm:.3f}")
    print("coverage = share of events answered; precision = right among answered; template given the same coverage (rejects its smallest-margin cases)")
    for K,nb,q,S in ((4,12,.15,16),(8,18,.15,16),(8,18,.25,4),(16,18,.15,16),(16,18,.25,16)):
        rs=[cov(s,K,nb,q,S) for s in range(25)]
        print(f"K={K} wires={nb} noise={q} S={S}: detector coverage {st.mean(r[0] for r in rs):.3f} precision {st.mean(r[1] for r in rs):.3f} | template at same coverage precision {st.mean(r[2] for r in rs):.3f}")

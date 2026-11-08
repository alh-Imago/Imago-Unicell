"""hexn_busnet_traffic_diag_v1 (8 Nov 2026): where packets are accepted and dropped, per layer, for the lean net and the pruned dense net (start threshold 5, seed 1). Alan 20:42. Finding (section 41): the drops are at the layer 2 buses and come from layer 1 firing about twice as often in the pruned dense net. Usage: python3 tools/hexn_busnet_traffic_diag_v1.py"""
import sys,random,copy; sys.path.insert(0,'tools')
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H
pats=[B.pattern(random.Random(100+k)) for k in range(8)]
def diag(net,lab):
    drops={1:0,2:0,3:0}; acc={1:0,2:0,3:0}; fires={1:0,2:0,3:0}; runs=0
    for k in range(8):
        for j in range(3):
            n=copy.deepcopy(net); n.acc={g:0 for g in n.acc}; n.rleft={g:0 for g in n.rleft}
            for q in n.queues.values(): q.clear()
            n.reset_stats(); orig=n.push
            def hook(bus,src,n=n,orig=orig):
                before=n.dropped; orig(bus,src)
                (drops if n.dropped>before else acc)[bus[0]]+=1
            n.push=hook; n.run(B.noisy(pats[k],random.Random(8000+10*k+j)),100); runs+=1
            for g,c in n.fires.items(): fires[n.layer_of(g)]+=c
    r=runs
    print(lab,"fires/run L1 %.0f L2 %.0f L3 %.0f | accepted at layer-1/2/3 buses %.0f/%.0f/%.0f | dropped at layer-1/2/3 buses %.0f/%.0f/%.0f"%(fires[1]/r,fires[2]/r,fires[3]/r,acc[1]/r,acc[2]/r,acc[3]/r,drops[1]/r,drops[2]/r,drops[3]/r))
s=1; th=5
lean=H.make(s,0.5,fb_k=4,fb_w=2,k=10,refr=6,th=th); tg2=T.targets(lean,s); t1=P.layer1_targets(lean,pats); H.train(lean,pats,tg2,t1,50); diag(lean,"lean        ")
rich=H.make(s,0.5,fb_k=8,fb_w=2,k=24,refr=6,th=th); t1r=P.layer1_targets(rich,pats); H.train(rich,pats,tg2,t1r,40); Q.prune_by(rich,P.LEAN_KEEP,"weight"); H.train(rich,pats,tg2,t1r,10); diag(rich,"dense pruned")

// Checks the page's counting code (between CORE-START/CORE-END in docs/hex-n/frontend/hexn_explorer_v1.html, saved as core.js) against a reference dump of tools/hexn_bank_model_v2.py (ref.json). Result when run: 20 models, 17160 samples, 0 mismatches.
const c=require('./core.js');const ref=require('./ref.json');let bad=0,nsamp=0;
for(const r of ref){
  const tr=r.train.map(([b,y])=>({bits:b,y}));const te=r.test.map(([b,y])=>({bits:b,y}));
  const m=c.trainBank(tr,{K:r.K,NB:r.NB,AW:r.AW,T:r.T});
  const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const tag=r.K+'/'+r.NB+'/s'+r.seed;
  for(const f of ['cnt','wts','thr','sump','sumn'])if(!eq(m[f],r[f])){bad++;console.log('MISMATCH',tag,f)}
  const all=tr.concat(te);
  all.forEach((s,i)=>{const o=c.classifyBits(m,s.bits);nsamp++;if(o.pred!==r.pred[i]||!eq(o.g,r.g[i])){bad++;if(bad<8)console.log('SAMPLE',tag,i,o.pred,r.pred[i],o.g,r.g[i])}});
}
console.log('models',ref.length,'samples',nsamp,'mismatches',bad);
// extra: T for 5 samples (half-even) and divRoundEven
console.log(c.weightCutoff(5,0.5),c.weightCutoff(16,0.5),c.weightCutoff(1,0.5),c.divRoundEven(5,2),c.divRoundEven(7,2),c.divRoundEven(1,3));

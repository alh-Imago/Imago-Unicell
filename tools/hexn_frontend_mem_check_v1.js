// Checks the page's memory code (between MEM-START/MEM-END in docs/hex-n/frontend/hexn_explorer_v1.html) against the Python rules (tools/hexn_mem_host_v1.py MemRef) on a scripted save/recall, and prints the four write-rule presets averaged over 10 seeds (compare with: python3 tools/hexn_mem_write_v1.py 10; the page uses its own random numbers, so only the averages agree).
// Usage: node tools/hexn_frontend_mem_check_v1.js
const fs=require('fs'),path=require('path');
const src=fs.readFileSync(path.join(__dirname,'../docs/hex-n/frontend/hexn_explorer_v1.html'),'utf8');
const mul=src.match(/function mulberry32[^\n]*\n/)[0], mem=src.split('/*MEM-START*/')[1].split('/*MEM-END*/')[0];
eval(mul+mem+`
const m=new MemRef();m.clrall();const a=0x2a5b3,b=0x15a4c;
m.clr();for(let i=0;i<3;i++)m.watch(a,0x3ffff);m.save(2);m.clr();for(let i=0;i<2;i++)m.watch(b,0x3ffff);m.save(5);
m.clr();m.watch(a^0x41,0x3f0ff);m.watch(a,0x3f0ff);m.watch(a^2,0x3f0ff);const r=m.recall();
console.log('scripted recall (python gives (2, 14, 14, 0, 172211, 173491, 0)):',[r.id,r.best,r.known,r.second,r.cue,r.rec,r.dev].join(', '));
const par={nc:3,qc:.15,T:400,hideP:1/3,chgP:.1,fam:.75};
for(const p of MEM_PRESETS){const x=memStudy(p,par,10);console.log(p.name.padEnd(46),['hot2','hot1_early','old_late','hold_hot2','hold_hot1','dup','err','wrong','falsefam'].map(k=>x[k].toFixed(2)).join(' '))}`);

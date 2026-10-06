import json, os, subprocess, sys, shutil, glob
from multiprocessing import Pool
ROOT="/home/claude/Imago-Unicell"
sys.path.insert(0, ROOT+"/tools")
import flexsub_assemble_v1 as fsa
CELLS=[c for c in fsa.cells_for("flex")]
WIDTHS=[4,8,16,18,24,32]
def parse(out):
    c={}
    for line in out.split("Number of cells")[-1].splitlines():
        p=line.split()
        if len(p)==2 and p[1].isdigit(): c[p[0]]=int(p[1])
    return dict(lut4=sum(v for k,v in c.items() if k.startswith("LUT")), alu=c.get("ALU",0), dff=sum(v for k,v in c.items() if k.startswith("DFF")), mult=sum(v for k,v in c.items() if k.startswith("MULT")), raw=c)
def run(job):
    cell,w=job
    if cell=="mul_dsp" and w>36: return None
    d=f"/tmp/sw/{cell}_w{w}_n9"
    shutil.rmtree(d,ignore_errors=True)
    r=subprocess.run(["python3",ROOT+"/tools/project_assemble_v1.py","-s","flex","-S",cell,"-w",str(w),"--cells","9","--output",d],capture_output=True,text=True,cwd=ROOT)
    if r.returncode: return dict(cell=cell,w=w,error=r.stderr[-300:]+r.stdout[-200:])
    rec=json.load(open(d+"/ASSEMBLY.json"))
    mod=rec["cell_module"]; top=rec["top"]
    files=[f for f in os.listdir(d) if f.endswith(".v")]
    deps=[f for f in files if f!=top+".v"]
    stub=[]
    res=dict(cell=cell,w=w,module=mod)
    def synth(srcs,topn,pre,extra):
        o=subprocess.run(["yosys","-p",f"read_verilog -sv {' '.join(srcs)}; {pre} hierarchy -top {topn}; synth_gowin -top {topn} {extra} -json /dev/null; stat"],cwd=d,capture_output=True,text=True,timeout=3000).stdout
        return parse(o)
    try:
        pre=f"chparam -set WIDTH {w} {mod};"
        res["single_wide"]=synth(deps,mod,pre,"")
        res["single_nowide"]=synth(deps,mod,pre,"-nowidelut")
        res["array9_nowide"]=synth([top+".v"]+deps,top,"","-nowidelut")
    except Exception as e:
        res["error"]=str(e)[:300]
    json.dump(res,open(f"/tmp/sw/res_{cell}_w{w}.json","w"))
    return res
if __name__=="__main__":
    jobs=[(c,w) for c in CELLS for w in WIDTHS]
    with Pool(2) as p:
        for r in p.imap_unordered(run,jobs): print(r and (r["cell"],r["w"],r.get("error","ok")),flush=True)
    open("/tmp/sw/done","w").write("x")

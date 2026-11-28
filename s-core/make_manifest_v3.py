"""make_manifest_v3.py - make_manifest_v2.py plus the multiply-unit count (6th argument MULU, 0 or 1, default 0): name prefix hm, top sc_top_k7_v19, dispatcher sc_sys_v23, fields mul_units and mul_unit_dsp_blocks (3 per unit per block; ledger #1584).  With MULU 0 the manifest equals the v2 one.  Cloned from make_manifest_v2.py (left as proven)."""
#!/usr/bin/env python3
"""make_manifest_v2.py (make_manifest_v1 for the hk line, ledger #1531) - write the manifest of an S-Core build and say what fits on which board (ledger #1522).
Usage:  python3 make_manifest_v2.py (make_manifest_v1 for the hk line, ledger #1531) NB S ULW NU IMEM [outdir]      (build name hj<NB>s<S>u<W>n<NU>i<IMEM>)
The manifest sits beside the generated Verilog; the front end reads it to set --blocks / --lw / --unit-lw / --imem and to show the targets.
Size model (Vivado, Kintex line, #1501): LUT = 1,042 + 3,151 x blocks + 674 x total slices, within 1.53 % over nine builds, plus units.
Unit sizes: 16 lanes 2,550 LUTs each (measured by difference, #1511); 32 lanes about 5,000 to 5,300 (derived by difference from the hj8s32u32n1i1024 build, #1526); other widths not measured -> no total claimed.
The code store (block RAM) is not in the model; its LUT cost is not measured yet."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
UNIT_LUTS = {16: (2550, 2550), 32: (5000, 5300)}      # (low, high); 32 lanes derived from hj8s32u32n1i1024 (#1526); widths 2, 4, 8 not measured

def predict(nb, s, ulw, nu):
    base = 1042 + 3151 * nb + 674 * nb * s
    if ulw == 0: return base, base, 'model, unit-less builds'
    w = 1 << ulw
    if w not in UNIT_LUTS: return None, None, 'unit size for %d lanes not measured' % w
    lo, hi = UNIT_LUTS[w]
    kind = 'model plus measured unit size' if lo == hi else 'model plus a unit size derived from one build'
    return base + nb * nu * lo, base + nb * nu * hi, kind

def manifest(nb, s, ulw, nu, imem, mulu=0, targets=None):
    if targets is None: targets = json.load(open(os.path.join(HERE, 'targets_v1.json')))
    if ulw == 0: nu = 1
    w = 1 << ulw
    name = '%s%ds%du%dn%di%d' % ('hm' if mulu else 'hk', nb, s, w, nu, imem)     # v3 (ledger #1584): hm = the same build with the multiply unit
    lo, hi, how = predict(nb, s, ulw, nu)
    m = {'build': name, 'line': 'hm' if mulu else 'hk', 'top': 'sc_top_k7_v19' if mulu else 'sc_top_k7_v18', 'dispatcher': 'sc_sys_v23' if mulu else 'sc_sys_v22', 'mul_units': mulu, 'mul_unit_dsp_blocks': 3 * mulu * nb, 'blocks': nb, 'slices_per_block': s, 'total_slices': nb * s,
         'unit_lanes': w if ulw else 0, 'units_per_block': nu if ulw else 0, 'unit_lw': ulw, 'imem_words': imem, 'dsh_words': 256, 'dmw': 16, 'far_ram_words': 65536,
         'host_args': {'blocks': nb, 'lw': ulw if ulw else 0, 'unit_lw': ulw if ulw else 0, 'imem': imem},
         'predicted_luts': {'low': lo, 'high': hi, 'basis': how}, 'measured': None, 'targets': {}}
    meas = json.load(open(os.path.join(HERE, 'builds_measured_v1.json'))).get(name)
    if meas: m['measured'] = meas; lo = hi = meas['luts']; m['predicted_luts']['basis'] += '; the measured figure is used for the fit'
    for k, t in targets.items():
        if k.startswith('_'): continue
        r = {'board': t['name']}
        if not t.get('s_core_builds_measured'):
            r['fit'] = 'unknown'; r['why'] = 'no S-Core pool has been built for this board; vendor LUT4 count is not comparable with the LUT6 model'
        elif lo is None:
            r['fit'] = 'unknown'; r['why'] = how
        else:
            if nb > t['max_blocks'] or s > t['max_slices_per_block']: r['fit'] = 'no'; r['why'] = 'beyond the block or slice limit of the design (%d blocks, %d slices)' % (t['max_blocks'], t['max_slices_per_block'])
            else:
                pl, ph = lo / t['luts'], hi / t['luts']
                r['lut_fraction'] = [round(pl, 3), round(ph, 3)]
                r['fit'] = 'recommended' if ph <= t['target_fraction'] else ('possible' if pl <= t['target_fraction'] and ph <= 1.0 else ('tight' if ph <= 1.0 else 'no'))
                r['why'] = '%s; %.0f %% target = %d LUTs' % (how, 100 * t['target_fraction'], int(t['target_fraction'] * t['luts']))
        m['targets'][k] = r
    return m

def write(nb, s, ulw, nu, imem, mulu=0, outdir=HERE):
    m = manifest(nb, s, ulw, nu, imem, mulu)
    p = os.path.join(outdir, 'sc_k7_%s.manifest.json' % m['build'])
    json.dump(m, open(p, 'w'), indent=1); return p, m

if __name__ == '__main__':
    a = [int(x) for x in sys.argv[1:7]]
    p, m = write(*a, outdir=sys.argv[7] if len(sys.argv) > 7 else '.')
    print('wrote', p); print(json.dumps({k: m[k] for k in ('build', 'predicted_luts', 'targets')}, indent=1))

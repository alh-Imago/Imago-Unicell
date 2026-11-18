#!/usr/bin/env python3
"""make_fz_v4.py - clock-test kit for the registered-decode units (ledger #1372): variants d4, d8, d16 (uc_unitd<W>, no RAM interface) and e4, e8, e16 (uc_unite<W>, with the word-RAM interface).
Same stubs and settings as make_fz_v2.py / make_fz_v3.py (the p* and r* variants are re-labelled copies with the unit name changed), so the numbers compare with #1368 and #1370.
Needs sc_k7_fz_p*.v, sc_k7_fz_r*.v and the Makefile.fz_p* / Makefile.fz_r* from those scripts (run them first).  Usage: python3 make_fz_v4.py"""
import os
here = os.path.dirname(os.path.abspath(__file__))
for W in (4, 8, 16):
    for new, old, u_old, u_new, srcs in (('d%d' % W, 'p%d' % W, 'uc_unitp%d' % W, 'uc_unitd%d' % W, ['uc_unitd%d' % W]),
                                         ('e%d' % W, 'r%d' % W, 'uc_unitr%d' % W, 'uc_unite%d' % W, ['uc_unite%d' % W, 'uc_unitd%d' % W])):
        t = open(os.path.join(here, 'sc_k7_fz_%s.v' % old)).read().replace(u_old, u_new).replace('sc_k7_fz_%s' % old, 'sc_k7_fz_%s' % new)
        t = t.replace('make_fz_v2.py', 'make_fz_v4.py').replace('make_fz_v3.py', 'make_fz_v4.py').replace('(ledger #1364)', '(ledger #1372)').replace('(ledger #1369)', '(ledger #1372)')
        open(os.path.join(here, 'sc_k7_fz_%s.v' % new), 'w').write(t)
        m = open(os.path.join(here, 'Makefile.fz_%s' % old)).read().replace('sc_k7_fz_%s' % old, 'sc_k7_fz_%s' % new)
        import re
        m = re.sub(r'ADDITIONAL_SOURCES = .*', 'ADDITIONAL_SOURCES = ' + ' '.join('rtl/%s.sv' % x for x in srcs), m)
        m = m.replace('make_fz_v2.py', 'make_fz_v4.py').replace('make_fz_v3.py', 'make_fz_v4.py')
        open(os.path.join(here, 'Makefile.fz_%s' % new), 'w').write(m)
        print('wrote sc_k7_fz_%s.v and Makefile.fz_%s' % (new, new))

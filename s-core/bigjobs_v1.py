#!/usr/bin/env python3
"""bigjobs_v1.py - jobs longer than a build's shared RAM allows: split the data on the host, run the pieces as separate jobs, combine the answers (ledger #1428).

A job's window in the shared RAM is 8 header words + inputs + outputs, and all the jobs of a batch share it (256 words on every build so far), so one job holds at most
247 data words.  A long data set is cut into pieces; each piece is an ordinary job (so everything the card does stays as proven); the host combines the answers:
    concat   a per-word kind (vscale, vgain, vxor, made kinds without a summing-up): the answers are put one after the other
    sum / min / max / xor / or / and   a totalling kind: the same operation over the pieces' answers (these are associative, so the result is exact)
    prefix   vprefix (running sum): each piece's answers plus the sum of all the earlier pieces' inputs
Not split (refused with the reason): crc32 (a chain from word to word), made kinds with `diff` or `prefix` in a bigger recipe, and kinds this module does not know
(give `combine=RULE` to say how their answers combine).  "pair" kinds are split by cutting both halves at the same places.
Pure functions; the shell (score_shell_v1.py) keeps the pieces in the job list with a "big" entry on each job so a saved job file keeps the grouping."""
import json, os
M32 = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN = {'vsum': 'sum', 'vscale': 'concat', 'vstress': 'sum'}
LIBRARY = {'vgain': 'concat', 'vmax': 'max', 'vmin': 'min', 'vxor': 'concat', 'vcount': 'sum', 'vprefix': 'prefix'}
RULES = ('concat', 'sum', 'min', 'max', 'xor', 'or', 'and', 'prefix')

class BigError(Exception): pass

def made_recipe(kind):
    p = os.path.join(HERE, 'programs', 'made', kind + '.json')
    if not os.path.exists(p): return None
    return json.load(open(p))['words']

def rule_for(kind, override=None):
    """-> (rule, pair): how the answers of the pieces combine, and whether the data is two halves"""
    if override:
        if override not in RULES: raise BigError('combine= one of: %s' % ', '.join(RULES))
        return override, False
    if kind in BUILTIN: return BUILTIN[kind], False
    if kind in LIBRARY: return LIBRARY[kind], False
    if kind == 'crc32': raise BigError('crc32 cannot be split: each word depends on the ones before it')
    words = made_recipe(kind)
    if words is None: raise BigError('I do not know how the answers of %r combine: add combine=%s' % (kind, '|'.join(RULES)))
    import jobmaker_v2 as J
    steps, red = J.parse(words)
    pair = bool(steps and steps[0][0] == 'pair')
    if any(op in ('diff', 'prefix') for op, _ in steps): raise BigError('a recipe with diff or prefix cannot be split exactly (a piece needs the end of the piece before it)')
    return (red if red else 'concat'), pair

def default_chunk(kind_out_same, dsh):
    """a piece size that lets a few pieces share one batch: about a quarter of the shared RAM"""
    return max(8, (dsh - 32) // 4)

def split(inputs, chunk, pair=False):
    """the data cut into pieces of at most `chunk` words (pairs: both halves cut at the same places, a piece is its a-part then its b-part; an odd last word is dropped)"""
    inputs = [x & M32 for x in inputs]
    if chunk < 1: raise BigError('chunk must be at least 1')
    if not pair: return [inputs[i:i + chunk] for i in range(0, len(inputs), chunk)] or [[]]
    h = len(inputs) // 2; a, b = inputs[:h], inputs[h:2 * h]; step = max(1, chunk // 2)
    return [a[i:i + step] + b[i:i + step] for i in range(0, h, step)] or [[]]

def whole(parts, pair=False):
    """the original data back from the pieces"""
    if not pair: return [x for p in parts for x in p]
    return [x for p in parts for x in p[:len(p) // 2]] + [x for p in parts for x in p[len(p) // 2:]]

def combine(rule, results, parts):
    """results: the answer (list of words) of each piece; parts: the data of each piece"""
    if rule == 'concat': return [x for r in results for x in r]
    if rule == 'prefix':
        out, carry = [], 0
        for r, p in zip(results, parts):
            out += [(x + carry) & M32 for x in r]; carry = (carry + sum(p)) & M32
        return out
    vals = [r[0] for r in results if r]
    if not vals: return [0]
    if rule == 'sum': return [sum(vals) & M32]
    if rule == 'min': return [min(vals)]
    if rule == 'max': return [max(vals)]
    acc = {'xor': 0, 'or': 0, 'and': M32}[rule]
    for v in vals: acc = acc ^ v if rule == 'xor' else (acc | v if rule == 'or' else acc & v)
    return [acc]

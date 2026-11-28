"""divconst_v1.py - divide by a constant with ONE multiply and a shift (ledger #1590), for the cores that have no divide.
x // d  ==  (x * M mod 2^32) >> k   with  M = ceil(2^k / d).  The multiply keeps only the LOW 32 bits (lib_mul32), so two limits hold:
  * x * M must stay below 2^32 (no wrap):  x < d * 2^(32-k) roughly;
  * the rounding error of M must not reach the result:  with e = M*d - 2^k (0 <= e < d) the answer is exact for every x < 2^k / e  (all x when e = 0, i.e. d a power of two).
best(d) picks the k (and so M) that gives the largest range of x that is exact.  The range is checked by brute force on its edges (check()), not only by the formula.
`pack(d)` returns the single 32-bit job argument  (k << 27) | M  that programs/vdivc.s unpacks (M < 2^27 is required, so k is limited)."""
import sys
M32 = 0xFFFFFFFF

def params(d, k):
    M = -(-(1 << k) // d)                 # ceil(2^k / d)
    e = M * d - (1 << k)
    xmax_exact = (1 << 32) if e == 0 else ((1 << k) - 1) // e        # x <= this: rounding error cannot show (x*e < 2^k)
    xmax_wrap = M32 // M                  # x <= this: x*M < 2^32
    return M, e, min(xmax_exact, xmax_wrap, M32)

def best(d):
    """(M, k, xmax) with the largest xmax over k in 1..31 and M < 2^27; d in 1..2^31"""
    if d < 1: raise ValueError('divisor must be at least 1')
    bestv = None
    for k in range(1, 32):
        M, e, xmax = params(d, k)
        if M >= (1 << 27): continue
        if bestv is None or xmax > bestv[2]: bestv = (M, k, xmax)
    return bestv

def div(x, M, k): return ((x * M) & M32) >> k

def check(d, M, k, xmax):
    """brute-force the edges: all x up to 5000, the last 5000 up to xmax, and 20000 spread values; returns the first wrong x or None"""
    xs = set(range(0, min(xmax, 5000) + 1)) | set(range(max(0, xmax - 5000), xmax + 1)) | {xmax * i // 20000 for i in range(20001)}
    for x in sorted(xs):
        if x <= xmax and div(x, M, k) != x // d: return x
    return None

def pack(d):
    M, k, xmax = best(d)
    return (k << 27) | M, xmax

if __name__ == '__main__':
    for a in sys.argv[1:] or ['13']:
        d = int(a); M, k, xmax = best(d); bad = check(d, M, k, xmax)
        print('divide by %d: M = %d, k = %d, exact for x up to %d (%s); job argument %d' % (d, M, k, xmax, 'checked' if bad is None else 'WRONG at x = %d' % bad, (k << 27) | M))

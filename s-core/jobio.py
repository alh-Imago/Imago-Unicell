"""jobio.py - host side of the S-Core job input / result convention (stage 3, step 1).

Every job (program class) has a shared-RAM window.  The first 8 words of the window are a header, then the inputs, then the output area:
    w0 in_off   w1 in_len   w2 out_off   w3 out_len   w4 status   w5 n_out   w6 arg   w7 spare
  in_off / out_off are in words from the start of the window (the job sees its window starting at byte address 0x10000, wherever it sits in the RAM).
  status: 0 pending, 1 finished ok, >= 2 the job refused (2 = output area too small).   n_out: output words the job produced.   arg: one job-specific number.
The host writes the header and the inputs, submits the job, and after it has finished reads status and n_out, then moves exactly n_out words out of the
window.  Windows are laid out one after another, so the outputs of several jobs can be gathered (stitched) into one contiguous block of far RAM:
each job's n_out words are copied to the next free far address (stitch())."""
import os
import sclink, host_sc as hs
HERE = os.path.dirname(os.path.abspath(__file__))
M32 = 0xFFFFFFFF
HDR = 8
F_IN_OFF, F_IN_LEN, F_OUT_OFF, F_OUT_LEN, F_STATUS, F_NOUT, F_ARG, F_SPARE = range(8)
KINDS = {'vsum': 'jobio/vsum.s', 'vscale': 'jobio/vscale.s', 'vstress': 'jobio/vstress.s'}

class Job:
    def __init__(self, cid, kind, inputs, out_len, arg=0, clone_of=None, hdr_out_len=None):
        """clone_of: share the CODE of another job's class (a window of its own, same size) - saves code store when one program runs several jobs.
        hdr_out_len: tell the job a different output size than the window really has (a test: the job must refuse when it is too small)."""
        if kind not in KINDS: raise ValueError('unknown job kind %r' % kind)
        self.cid, self.kind, self.inputs, self.out_len, self.arg = cid, kind, [w & M32 for w in inputs], out_len, arg
        self.clone_of, self.hdr_out_len = clone_of, hdr_out_len
    @property
    def in_off(self): return HDR
    @property
    def out_off(self): return HDR + len(self.inputs)
    @property
    def window_words(self): return HDR + len(self.inputs) + self.out_len
    def expected(self):
        """the output words the job must produce (computed here in Python, independently of the core)"""
        if self.kind == 'vsum': return [sum(self.inputs) & M32]
        if self.kind == 'vscale': return [(2 * x + 1) & M32 for x in self.inputs]
        if self.kind == 'vstress': return [(self.arg * sum(self.inputs)) & M32] if self.arg and self.inputs else [0]

def build_link(jobs, shared_words=256, private_words=16, code_words=128):
    L = sclink.Linker(shared_words=shared_words, private_words=private_words, code_words=code_words)
    L.library(open(os.path.join(HERE, 'jobio', 'lib_io.s')).read())
    by = {j.cid: j for j in jobs}
    for j in jobs:
        if j.clone_of is None: L.add_class(j.cid, open(os.path.join(HERE, KINDS[j.kind])).read(), data_words=j.window_words)
    for j in jobs:
        if j.clone_of is not None:
            if by[j.clone_of].window_words != j.window_words or by[j.clone_of].kind != j.kind: raise ValueError('a clone needs the same program and window size as class %d' % j.clone_of)
            L.clone_class(j.cid, j.clone_of)
    return L.link()

def window_base(link, job): return link.classes[job.cid]['win'][0]

def prepare(link, job):
    """{shared word index: value}: header, inputs, and zeros for the status / n_out / output area"""
    b = window_base(link, job)
    m = {b + F_IN_OFF: job.in_off, b + F_IN_LEN: len(job.inputs), b + F_OUT_OFF: job.out_off, b + F_OUT_LEN: (job.out_len if job.hdr_out_len is None else job.hdr_out_len),
         b + F_STATUS: 0, b + F_NOUT: 0, b + F_ARG: job.arg & M32, b + F_SPARE: 0}
    for i, w in enumerate(job.inputs): m[b + job.in_off + i] = w
    for i in range(job.out_len): m[b + job.out_off + i] = 0
    return m

def prepare_cmds(link, job): return [hs.cmd_M(a, v) for a, v in sorted(prepare(link, job).items())]

def stitch(link, jobs_nouts, far_base):
    """jobs_nouts: [(job, n_out)] in the order the outputs should appear.  -> ([(near word, far word, count)], total words)
    The far addresses are consecutive: the result is one block in far RAM, whatever the jobs' windows look like."""
    plan, far = [], far_base
    for job, n in jobs_nouts:
        if n: plan.append((window_base(link, job) + job.out_off, far, n)); far += n
    return plan, far - far_base

"""
psychtrix_sketch.py — data-structure sketch for thematic meta-synthesis

EXPLORATORY. The point is to see whether the design we discussed holds as data
structures *before* any of it becomes part of the system. Vocabulary
deliberately mirrors cell_format.py (FormatDefinition, BridgeContract,
semantic_confidence, the confidence tiers, context_match) so it could drop into
the Trix + bridges framework if it survives scrutiny.

Pipeline modelled:
    per study   -> a ScopedCodebook        (codes carry SCOPE = the validity type)
    align each  -> CodeBridge into the hub  (fuzzy, confidence-weighted)
    grow hub    -> a MetaCodebook           (conglomerate; +1 study is O(1) vs hub)
    aggregate   -> theme robustness         (the fabric's job, at scale)

HONEST SEAMS — deliberately NOT solved here, because they live upstream of the
fabric and are interpretive:
  * Proposing which study-code matches which hub meta-code is the fuzzy step.
    In reality: embeddings/fuzzy logic PROPOSE candidates, the ANALYST confirms.
    The proposer is a pluggable function; the worked example below drives
    integration from analyst-confirmed bridges, which is the real workflow.
    `illustrative_overlap` is a TOY stand-in, not a semantic matcher.
  * The hub is REVISABLE, not frozen: split()/merge() mark where a later study
    forces the synthesis frame to change. Stubs here, on purpose.

Run:  python3 sketches/psychtrix_sketch.py
"""

from dataclasses import dataclass, field


# ── Confidence policy — mirrors cell_format.BridgeContract.compiler_policy ─────
def alignment_policy(semantic_confidence: float, scope_compatible: bool) -> str:
    """How to treat a proposed study->hub alignment. Same tiers as the bridge
    compiler policy, repurposed for analyst review instead of tile placement."""
    if semantic_confidence < 0.60:
        return "reject"                  # too weak — do not link
    if semantic_confidence < 0.80 or not scope_compatible:
        return "require_analyst"         # scope mismatch or borderline — confirm
    if semantic_confidence < 0.95:
        return "accept_with_flag"        # link, but mark for a glance
    return "accept"                      # strong, scope-compatible — link


# ── The typed alphabet element ────────────────────────────────────────────────
@dataclass
class ScopedCode:
    """One code in a single study's codebook. `scope` is the validity type:
    what the code relates to / the context it applies in. It is both the type
    tag and the guard against decontextualised cross-study equation."""
    code_id:    str
    label:      str
    definition: str
    scope:      str
    exemplars:  list = field(default_factory=list)   # verbatim provenance
    inclusion:  str = ""
    exclusion:  str = ""


# ── A per-study codebook = that dataset's bridge contract ─────────────────────
@dataclass
class ScopedCodebook:
    """Inductive: built from THESE interviews only. Each codebook is a contract
    declaring what its codes mean and where they apply."""
    study_id:    str
    codes:       dict = field(default_factory=dict)   # code_id -> ScopedCode
    occurrences: dict = field(default_factory=dict)   # code_id -> set(interview)

    def add(self, code: ScopedCode, interviews=()):
        self.codes[code.code_id] = code
        self.occurrences[code.code_id] = set(interviews)


# ── The bridge: study code -> hub meta-code ───────────────────────────────────
@dataclass
class CodeBridge:
    """Fuzzy, confidence-weighted link. semantic_confidence is the FINDING, not
    a warning flag. Mirrors cell_format.BridgeContract (source/target + scope +
    confidence + verification)."""
    study_id:            str
    code_id:             str
    meta_id:             str
    semantic_confidence: float
    scope_compatible:    bool                    # == BridgeContract.context_match
    rationale:           str = ""
    confirmed_by:        str = "auto-proposed"   # analyst id once confirmed

    @property
    def policy(self) -> str:
        return alignment_policy(self.semantic_confidence, self.scope_compatible)

    @property
    def linked(self) -> bool:
        """A bridge links iff it is strong enough, or an analyst confirmed it."""
        p = self.policy
        if p == "reject":
            return False
        if p == "require_analyst":
            return self.confirmed_by != "auto-proposed"
        return True                               # accept / accept_with_flag


# ── A hub entry — a third-order construct conglomerated across studies ─────────
@dataclass
class MetaCode:
    meta_id:    str
    label:      str
    definition: str
    scope:      str
    backlinks:  list = field(default_factory=list)   # list[CodeBridge] = provenance

    def supporting_studies(self) -> set:
        return {b.study_id for b in self.backlinks if b.linked}


# ── The hub ───────────────────────────────────────────────────────────────────
@dataclass
class MetaCodebook:
    """The conglomerate of meta-codes, aligned back to every dataset. Adding a
    study is O(1) against the hub, not O(N) against all prior studies."""
    meta_codes: dict = field(default_factory=dict)   # meta_id -> MetaCode
    studies:    list = field(default_factory=list)
    _seq:       int  = 0

    def seed(self, code: ScopedCode, study_id: str) -> MetaCode:
        """An unmatched study code starts a new meta-code (the hub grows)."""
        self._seq += 1
        mid = f"M{self._seq:03d}"
        m = MetaCode(mid, code.label, code.definition, code.scope)
        m.backlinks.append(CodeBridge(study_id, code.code_id, mid, 1.0, True,
                                      "seed: no prior match", "auto-seed"))
        self.meta_codes[mid] = m
        return m

    # ── revisable-hub seams (a later study can force the frame to change) ──
    def split(self, meta_id):  ...   # TODO: when one meta-code is really two
    def merge(self, a, b):     ...   # TODO: when two meta-codes are really one


def integrate(hub: MetaCodebook, book: ScopedCodebook, bridges):
    """Apply (analyst-reviewed) bridges; any code that did not link seeds a new
    meta-code. This is the only step that grows the hub."""
    if book.study_id not in hub.studies:
        hub.studies.append(book.study_id)
    linked = set()
    for b in bridges:
        # guard: only link a confirmed bridge whose target meta-code exists
        # (protects against a stale or mistyped meta_id) — suggested by Grok
        if b.linked and b.meta_id in hub.meta_codes:
            hub.meta_codes[b.meta_id].backlinks.append(b)
            linked.add(b.code_id)
    for cid, code in book.codes.items():
        if cid not in linked:
            hub.seed(code, book.study_id)
    return hub


def theme_robustness(hub: MetaCodebook):
    """The aggregate / fabric job: per meta-code, how many studies support it,
    confidence-weighted. This is the embarrassingly-parallel commonality
    detection that maps to the wired-OR 'aggregate neighbours' primitive."""
    n = len(hub.studies) or 1
    rows = []
    for m in hub.meta_codes.values():
        accepted = [b for b in m.backlinks if b.linked]
        support  = len({b.study_id for b in accepted})
        conf     = sum(b.semantic_confidence for b in accepted) / max(len(accepted), 1)
        rows.append((m.meta_id, m.label, support, n, round(conf, 2)))
    rows.sort(key=lambda r: (r[2], r[4]), reverse=True)
    return rows


# ── Illustrative-only candidate proposer (NOT a semantic matcher) ─────────────
def illustrative_overlap(code: ScopedCode, meta: MetaCode) -> float:
    """TOY: word-overlap of labels, purely to show WHERE the proposer plugs in.
    In reality this is an embedding/fuzzy model whose candidates an analyst
    then confirms. Do not mistake this for the real similarity step."""
    a, b = set(code.label.lower().split()), set(meta.label.lower().split())
    return len(a & b) / max(len(a | b), 1)


# ── Worked example ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Two studies on living with chronic illness — different wording, shared ideas.
    s1 = ScopedCodebook("S1")
    s1.add(ScopedCode("c1", "fear of relapse",
                      "anxiety the illness will return", "illness trajectory"),
           interviews=["p1", "p3", "p4"])
    s1.add(ScopedCode("c2", "loss of independence",
                      "reduced capacity for daily self-reliance", "self / autonomy"),
           interviews=["p2", "p3"])
    s1.add(ScopedCode("c3", "family support",
                      "practical and emotional help from family", "support network"),
           interviews=["p1", "p2", "p4"])

    s2 = ScopedCodebook("S2")
    s2.add(ScopedCode("c1", "worry about recurrence",
                      "preoccupation that symptoms will come back", "illness trajectory"),
           interviews=["q2", "q5"])
    s2.add(ScopedCode("c2", "being a burden",
                      "distress at depending on / costing others", "self / relationships"),
           interviews=["q1", "q4"])
    s2.add(ScopedCode("c3", "family as anchor",
                      "family as the steadying presence", "support network"),
           interviews=["q1", "q3", "q5"])

    hub = MetaCodebook()
    integrate(hub, s1, [])               # first study: every code seeds a meta-code

    # Second study: an embedding model would PROPOSE these; an analyst reviews.
    proposed = [
        # strong + scope-compatible -> accept
        CodeBridge("S2", "c3", "M003", 0.96, True, "family support ~ family as anchor"),
        # strong-ish + scope-compatible -> accept_with_flag
        CodeBridge("S2", "c1", "M001", 0.91, True, "relapse fear ~ recurrence worry"),
        # borderline + scope only partly matching -> require_analyst...
        CodeBridge("S2", "c2", "M002", 0.72, True,
                   "burden ~ loss of independence?", confirmed_by="auto-proposed"),
        # ...and the analyst decides 'being a burden' is a DISTINCT theme:
        #    leaving the proposal unconfirmed, so c2 seeds its own meta-code.
    ]
    integrate(hub, s2, proposed)

    print("HUB — meta-codes and their provenance")
    print("=" * 66)
    for m in hub.meta_codes.values():
        studies = ", ".join(sorted(m.supporting_studies())) or "—"
        print(f"  {m.meta_id}  {m.label:24}  scope: {m.scope}")
        print(f"        supported by: {studies}")
        for b in m.backlinks:
            print(f"        ← {b.study_id}.{b.code_id}  conf={b.semantic_confidence:.2f}"
                  f"  [{b.policy}{'' if b.linked else ', not linked'}]  {b.rationale}")
    print()
    print("THEME ROBUSTNESS  (aggregate across studies — the fabric's job)")
    print("=" * 66)
    print(f"  {'meta':5} {'theme':24} {'support':>9}  {'avg conf':>8}")
    for mid, label, support, n, conf in theme_robustness(hub):
        flag = "robust" if support == n else "tentative"
        print(f"  {mid:5} {label:24} {support:>4}/{n:<4}  {conf:>8}   {flag}")

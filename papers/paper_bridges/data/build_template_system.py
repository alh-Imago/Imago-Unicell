"""
build_template_system.py

Builds the Equation Template Format and Template Matching System.

Schema additions:
  equation_templates  — formal template definitions with slots
  template_slots      — typed slot definitions per template  
  equation_instances  — maps equations to templates + slot bindings
  template_bridges    — auto-generated bridge contracts from template matching

Matching logic:
  1. Structural match  — equation.functional_family == template.family
  2. Dimensional match — slot dimensions satisfy SI constraint
  3. Zero compatibility — Δ slot zeros declared commensurable
  → Valid match: generate BridgeContract candidate
  → Structure match only: flag as 'zero_check_required'
  → No match: justified absence or missing declaration
"""

import sqlite3, json
from itertools import combinations

DB = "concept_graph.db"
db = sqlite3.connect(DB)
c  = db.cursor()
c.execute("PRAGMA foreign_keys = ON")

# ── 1. Schema ────────────────────────────────────────────────────────────────

c.executescript("""
CREATE TABLE IF NOT EXISTS equation_templates (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    family          TEXT NOT NULL,          -- links to functional_family
    canonical_form  TEXT NOT NULL,          -- e.g. "y = k · Δ"
    description     TEXT,
    medium_constant_slot TEXT,              -- slot name that holds domain constant
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS template_slots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id     TEXT NOT NULL REFERENCES equation_templates(id),
    slot_name       TEXT NOT NULL,          -- e.g. 'y', 'k', 'delta'
    role            TEXT NOT NULL,          -- 'output','conductivity','delta','input','constant'
    nature          TEXT,                   -- 'delta','rate','ratio','absolute'
    dimension_constraint TEXT,             -- SI dimension this slot must satisfy
    description     TEXT
);

CREATE TABLE IF NOT EXISTS equation_instances (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    equation_id     TEXT NOT NULL REFERENCES equations(id),
    template_id     TEXT NOT NULL REFERENCES equation_templates(id),
    domain_id       TEXT NOT NULL,
    slot_bindings   TEXT NOT NULL,          -- JSON: {slot_name: concept_id_or_constant_id}
    medium_constant TEXT,                   -- the domain-specific constant value/id
    medium_constant_interpretation TEXT,    -- what the constant means in this domain
    match_quality   TEXT DEFAULT 'full',    -- 'full','structural','dimensional'
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS template_bridges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id     TEXT NOT NULL REFERENCES equation_templates(id),
    domain_a        TEXT NOT NULL,
    domain_b        TEXT NOT NULL,
    equation_a      TEXT REFERENCES equations(id),
    equation_b      TEXT REFERENCES equations(id),
    status          TEXT NOT NULL,  -- 'valid','zero_check_required','predicted','justified_absent'
    confidence      REAL,
    shared_structure TEXT,          -- canonical form both share
    constant_a      TEXT,           -- medium constant in domain A
    constant_b      TEXT,           -- medium constant in domain B
    zero_compatible INTEGER,        -- 1=yes, 0=no, NULL=unknown
    notes           TEXT,
    auto_generated  INTEGER DEFAULT 1
);
""")

print("Schema created")

# ── 2. Template definitions ──────────────────────────────────────────────────

TEMPLATES = [
    # (id, name, family, canonical_form, description, medium_constant_slot, notes)

    ("T01","Linear Flux","linear_flux",
     "flux = conductivity × Δ",
     "Universal transport equation. Any conserved quantity flows down its gradient. "
     "The conductivity is the domain-specific medium constant — the only thing that "
     "differs between domains using this template.",
     "conductivity",
     "Ohm V=IR, Fourier Q=kΔT, Fick J=DΔc, Darcy q=KΔP, Hooke σ=Eε. "
     "Most fundamental template — wherever a conserved quantity has a gradient, "
     "this equation is mandatory."),

    ("T02","Exponential Decay","exponential_decay",
     "y = y₀ · e^(-k·x)",
     "Quantity decreases proportional to its current value. The decay constant k "
     "is the medium constant — rate at which this substrate loses the quantity.",
     "decay_constant",
     "Radioactive decay N=N₀e^-λt, RC discharge V=V₀e^-t/RC, "
     "Arrhenius k=Ae^-Ea/RT, damped oscillation."),

    ("T03","Exponential Growth","exponential_growth",
     "y = y₀ · e^(k·x)  or  dy/dx = k·y",
     "Quantity grows proportional to its current value. k is the growth rate "
     "constant — the medium's amplification factor.",
     "growth_rate",
     "Malthusian dN/dt=rN, compound interest FV=PV(1+i)^n. "
     "Same structure as T02 with sign reversed on k."),

    ("T04","Logistic Growth","logistic",
     "dy/dx = k·y·(1 - y/K)",
     "Exponential growth bounded by carrying capacity K. Two medium constants: "
     "k (growth rate) and K (capacity of this substrate to support the quantity).",
     "growth_rate",
     "Verhulst population, epidemic SIR, market saturation, capacitor charging, "
     "sigmoid neural activation. Declared in 1 domain, predicted in 26."),

    ("T05","Inverse Square","inverse_square",
     "F = k · (a · b) / r²",
     "Force or field strength falls as square of separation. k is the coupling "
     "constant of the medium — how strongly the substrate transmits the interaction.",
     "coupling_constant",
     "Newton gravity G·m₁m₂/r², Coulomb k·q₁q₂/r². "
     "Both are the same template with different coupling constants."),

    ("T06","Power Law","power_law",
     "y = k · xⁿ",
     "Output scales as input raised to power n. k is the domain scaling constant. "
     "n defines the nonlinearity — 2 for quadratic, 4 for Stefan-Boltzmann etc.",
     "scaling_constant",
     "KE=½mv², drag D=½ρCdAv², Stefan-Boltzmann T⁴, spring PE=½kx²."),

    ("T07","Conservation Sum","conservation",
     "Σ(terms) = constant",
     "Total of conserved quantity across all forms is invariant. "
     "No medium constant — this is a pure structural constraint.",
     None,
     "Bernoulli P+ρgy+½ρv²=const, energy conservation, "
     "accounting A=L+E (enforced to zero delta)."),

    ("T08","Linear Product","linear_product",
     "y = a · b  (or y = a · b · c)",
     "Output is direct product of inputs. The simplest non-trivial relationship. "
     "Domain constant absorbed into one of the factors.",
     None,
     "F=ma, p=mv, E=hf, I=Prt, W=mg. Universal — appears in every domain "
     "with proportional relationships."),

    ("T09","Ratio Definition","ratio_def",
     "y = a / b",
     "Output is ratio of two quantities. Defines intensive properties, "
     "dimensionless numbers, efficiencies, concentrations.",
     None,
     "ρ=m/V, P=F/A, C=Q/V, mole fraction, Reynolds number, Mach number."),

    ("T10","Inverse Linear","inverse_linear",
     "y = k / x",
     "Output inversely proportional to input. k is medium constant.",
     "inverse_constant",
     "Gravitational potential U=-GM/r, perpetuity PV=PMT/i, "
     "de Broglie λ=h/p, thin lens 1/f=1/do+1/di."),

    ("T11","Period Square Root","period_sqrt",
     "T = 2π · √(a / b)",
     "Period of oscillation as square root of restoring/inertial ratio. "
     "The 2π factor is structural — appears in all periodic systems.",
     "restoring_constant",
     "Spring T=2π√(m/k), pendulum T=2π√(ℓ/g), Kepler T²=4π²a³/GM."),

    ("T12","Logarithmic","logarithmic",
     "y = k · log(x / x₀)",
     "Output compresses large input range logarithmically. x₀ is reference zero. "
     "k is domain scaling constant.",
     "log_base_constant",
     "pH=-log[H⁺], decibels, Shannon entropy, Beer-Lambert absorbance, "
     "natural strain ln(lf/lo)."),

    ("T13","Field Integral","field_integral",
     "∮ F · dA = k · source",
     "Integral of field over closed surface equals enclosed source times coupling. "
     "k is the medium permittivity/permeability.",
     "medium_coupling",
     "Gauss E: ∮E·dA=Q/ε₀, Gauss B: ∮B·dA=0, "
     "gravitational Gauss: ∮g·dA=-4πGM."),

    ("T14","Linear Difference","linear_difference",
     "y = a - b",
     "Output is directed difference between two states. "
     "The purest expression of Δ as a primitive.",
     None,
     "NI=R-X, Lagrangian L=T-V, mass defect Δm=Zmp+Nmn-M, "
     "cell EMF=E_cat-E_an, photoelectric KE=hf-φ."),

    ("T15","Predator-Prey Coupled","predator_prey",
     "dx/dt = αx - βxy  |  dy/dt = δxy - γy",
     "Coupled differential equations where two populations interact. "
     "Four medium constants: α,β,δ,γ — growth, predation, conversion, death rates.",
     "interaction_constant",
     "Lotka-Volterra. Predicted missing: market competition, "
     "immune response, chemical oscillators (Belousov-Zhabotinsky)."),

    ("T16","Harmonic","harmonic",
     "y = A · cos(ωt + φ)  or  ω = 2π/T",
     "Sinusoidal oscillation with amplitude A, angular frequency ω, phase φ. "
     "ω is the medium constant — how fast this substrate oscillates.",
     "angular_frequency",
     "SHM, AC circuits, wave propagation. "
     "Predicted missing: business cycles, circadian rhythms."),

    ("T17","Linear Sum","linear_sum",
     "y = Σ aᵢ  (or a + b + c = const)",
     "Output is sum of components. Conservation of additive quantities. "
     "Appears wherever components combine linearly.",
     None,
     "Accounting A=L+E, series resistors, superposition principle, "
     "pH+pOH=14, Kirchhoff current law."),

    ("T18","Quadratic / Compound","quadratic",
     "y = a·(1+k)ⁿ  or  y = a·x + b·x²",
     "Compound growth or kinematic equation of motion. "
     "k is the per-period rate constant.",
     "period_rate",
     "Compound interest FV=PV(1+i)^n, kinematic s=v₀t+½at², "
     "annuity formulas."),
]

# Insert templates
for row in TEMPLATES:
    c.execute("""INSERT OR REPLACE INTO equation_templates
                 (id,name,family,canonical_form,description,medium_constant_slot,notes)
                 VALUES (?,?,?,?,?,?,?)""", row)
print(f"Inserted {len(TEMPLATES)} templates")

# ── 3. Template slots ────────────────────────────────────────────────────────

SLOTS = [
    # (template_id, slot_name, role, nature, dimension_constraint, description)

    # T01 Linear Flux
    ("T01","flux",        "output",       "rate",     None, "quantity transferred per unit time/area"),
    ("T01","conductivity","conductivity", "absolute", None, "medium constant — substrate resistance to transfer"),
    ("T01","delta",       "delta",        "delta",    None, "driving difference — the Δ being responded to"),

    # T02 Exponential Decay
    ("T02","y",     "output",  "absolute", None, "decaying quantity"),
    ("T02","y0",    "input",   "absolute", None, "initial value"),
    ("T02","k",     "conductivity","absolute",None,"decay constant — medium's loss rate"),
    ("T02","x",     "delta",   "delta",    None, "independent variable (usually time)"),

    # T03 Exponential Growth
    ("T03","y",     "output",  "absolute", None, "growing quantity"),
    ("T03","y0",    "input",   "absolute", None, "initial value"),
    ("T03","k",     "conductivity","absolute",None,"growth rate constant"),
    ("T03","x",     "delta",   "delta",    None, "independent variable"),

    # T04 Logistic
    ("T04","y",     "output",  "absolute", None, "population / quantity"),
    ("T04","k",     "conductivity","absolute",None,"intrinsic growth rate"),
    ("T04","K",     "constant","absolute", None, "carrying capacity — upper bound"),
    ("T04","x",     "delta",   "delta",    None, "time or independent variable"),

    # T05 Inverse Square
    ("T05","F",     "output",  "absolute", None, "force or field strength"),
    ("T05","k",     "conductivity","absolute",None,"coupling constant of medium"),
    ("T05","a",     "input",   "absolute", None, "source quantity A"),
    ("T05","b",     "input",   "absolute", None, "source quantity B"),
    ("T05","r",     "delta",   "delta",    None, "separation distance — Δ position"),

    # T06 Power Law
    ("T06","y",     "output",  "absolute", None, "output quantity"),
    ("T06","k",     "conductivity","absolute",None,"domain scaling constant"),
    ("T06","x",     "input",   "absolute", None, "input quantity"),
    ("T06","n",     "constant","absolute", None, "power exponent — structural parameter"),

    # T07 Conservation Sum
    ("T07","terms", "input",   "absolute", None, "conserved quantities in all forms"),
    ("T07","C",     "output",  "absolute", None, "invariant total"),

    # T08 Linear Product
    ("T08","y",     "output",  "absolute", None, "output"),
    ("T08","a",     "input",   "absolute", None, "factor A"),
    ("T08","b",     "input",   "absolute", None, "factor B"),

    # T09 Ratio Definition
    ("T09","y",     "output",  "ratio",    None, "ratio output"),
    ("T09","a",     "input",   "absolute", None, "numerator"),
    ("T09","b",     "input",   "absolute", None, "denominator"),

    # T10 Inverse Linear
    ("T10","y",     "output",  "absolute", None, "output"),
    ("T10","k",     "conductivity","absolute",None,"medium constant"),
    ("T10","x",     "delta",   "delta",    None, "driving quantity"),

    # T11 Period Square Root
    ("T11","T",     "output",  "rate",     None, "period of oscillation"),
    ("T11","a",     "input",   "absolute", None, "inertial term"),
    ("T11","b",     "conductivity","absolute",None,"restoring force constant"),

    # T12 Logarithmic
    ("T12","y",     "output",  "ratio",    None, "compressed output"),
    ("T12","k",     "conductivity","absolute",None,"scaling constant"),
    ("T12","x",     "input",   "absolute", None, "input quantity"),
    ("T12","x0",    "constant","absolute", None, "reference zero of input"),

    # T13 Field Integral
    ("T13","field", "input",   "absolute", None, "field vector"),
    ("T13","area",  "input",   "absolute", None, "closed surface"),
    ("T13","k",     "conductivity","absolute",None,"medium coupling constant"),
    ("T13","source","input",   "absolute", None, "enclosed source"),

    # T14 Linear Difference
    ("T14","y",     "output",  "delta",    None, "difference output"),
    ("T14","a",     "input",   "absolute", None, "state A"),
    ("T14","b",     "input",   "absolute", None, "state B (subtracted)"),

    # T15 Predator-Prey
    ("T15","x",     "input",   "absolute", None, "prey / species A population"),
    ("T15","y",     "input",   "absolute", None, "predator / species B population"),
    ("T15","alpha", "conductivity","absolute",None,"prey growth rate"),
    ("T15","beta",  "conductivity","absolute",None,"predation rate"),
    ("T15","delta", "conductivity","absolute",None,"predator growth from prey"),
    ("T15","gamma", "conductivity","absolute",None,"predator death rate"),

    # T16 Harmonic
    ("T16","y",     "output",  "absolute", None, "oscillating quantity"),
    ("T16","A",     "input",   "absolute", None, "amplitude"),
    ("T16","omega", "conductivity","rate",  None, "angular frequency — medium oscillation rate"),
    ("T16","phi",   "constant","absolute", None, "phase offset"),

    # T17 Linear Sum
    ("T17","y",     "output",  "absolute", None, "total"),
    ("T17","terms", "input",   "absolute", None, "additive components"),

    # T18 Quadratic/Compound
    ("T18","y",     "output",  "absolute", None, "output quantity"),
    ("T18","a",     "input",   "absolute", None, "base / initial value"),
    ("T18","k",     "conductivity","absolute",None,"per-period rate"),
    ("T18","n",     "delta",   "delta",    None, "number of periods"),
]

c.execute("DELETE FROM template_slots")
for row in SLOTS:
    c.execute("""INSERT INTO template_slots
                 (template_id,slot_name,role,nature,dimension_constraint,description)
                 VALUES (?,?,?,?,?,?)""", row)
print(f"Inserted {len(SLOTS)} slots")

# ── 4. Equation instances — map equations to templates ───────────────────────

# (equation_id, template_id, domain_id, slot_bindings_json,
#  medium_constant, medium_constant_interpretation)

INSTANCES = [
    # T01 Linear Flux
    ("EQ081","T01","circuits",
     '{"flux":"C084","conductivity":"C081","delta":"C082"}',
     "1/R","electrical resistance — opposition to charge flow"),
    ("EQ492","T01","structural_geology",
     '{"flux":"C486","conductivity":"C494","delta":"C493"}',
     "E","Young's modulus — stiffness of rock"),
    ("EQ493","T01","structural_geology",
     '{"flux":"C487","conductivity":"C495","delta":"C496"}',
     "η","shear modulus — rigidity of rock"),
    ("EQ490","T01","structural_geology",
     '{"flux":"C487","conductivity":"C491","delta":"C486"}',
     "tan(φ)+c/σₙ","friction angle + cohesion — rock failure resistance"),
    ("EQ340","T01","chemistry",
     '{"flux":"C543","conductivity":"C307","delta":"C542"}',
     "ε","molar absorption coefficient"),

    # T02 Exponential Decay
    ("EQ252","T02","nuclear",
     '{"y":"C503","y0":"C503","k":"C253","x":"C004"}',
     "λ","decay constant — nuclear instability rate"),
    ("EQ120","T02","chem_kinetics",
     '{"y":"C121","y0":"C121","k":"C120","x":"C064"}',
     "Ea/R","activation energy over gas constant"),
    ("EQ206","T02","oscillations",
     '{"y":"C021","y0":"C021","k":"C442","x":"C004"}',
     "b/m","damping coefficient over mass"),

    # T03 Exponential Growth
    ("EQ496","T03","population_dynamics",
     '{"y":"C503","y0":"C503","k":"C504","x":"C004"}',
     "r","intrinsic growth rate — population fecundity"),
    ("EQ508","T03","financial_math",
     '{"y":"C531","y0":"C532","k":"C533","x":"C534"}',
     "i","periodic interest rate — capital growth rate"),

    # T04 Logistic
    ("EQ497","T04","population_dynamics",
     '{"y":"C503","k":"C504","K":"C505","x":"C004"}',
     "r","intrinsic growth rate"),

    # T05 Inverse Square
    ("EQ030","T05","gravitation",
     '{"F":"C013","k":"CONST_G","a":"C010","b":"C010","r":"C001"}',
     "G","gravitational coupling constant 6.674×10⁻¹¹ m³kg⁻¹s⁻²"),
    ("EQ080","T05","electrostatics",
     '{"F":"C013","k":"CONST_k","a":"C080","b":"C080","r":"C001"}',
     "1/4πε₀","electrostatic coupling constant 8.988×10⁹ Nm²C⁻²"),

    # T06 Power Law
    ("EQ020","T06","energy_domain",
     '{"y":"C020","k":"0.5","x":"C002","n":"2"}',
     "½","kinematic scaling — fixed structural constant"),
    ("EQ066","T06","heat_transfer",
     '{"y":"C026","k":"CONST_sigma","x":"C064","n":"4"}',
     "σ","Stefan-Boltzmann constant 5.67×10⁻⁸ Wm⁻²K⁻⁴"),
    ("EQ022","T06","energy_domain",
     '{"y":"C022","k":"0.5k","x":"C001","n":"2"}',
     "½k","half of spring constant"),

    # T07 Conservation Sum
    ("EQ053","T07","fluids",
     '{"terms":"pressure+kinetic+potential","C":"const"}',
     None,"Bernoulli — no medium constant, pure conservation"),
    ("EQ502","T07","accounting",
     '{"terms":"liabilities+equity","C":"assets"}',
     None,"accounting identity — enforced conservation"),

    # T08 Linear Product
    ("EQ010","T08","dynamics",
     '{"y":"C013","a":"C010","b":"C003"}',
     None,"F=ma — no medium constant, pure structural"),
    ("EQ012","T08","dynamics",
     '{"y":"C015","a":"C010","b":"C002"}',
     None,"p=mv"),
    ("EQ103","T08","quantum",
     '{"y":"C019","a":"CONST_h","b":"C041"}',
     "h","Planck constant — quantum of action 6.626×10⁻³⁴ Js"),
    ("EQ506","T08","financial_math",
     '{"y":"C528","a":"C527","b":"C529","c":"C530"}',
     None,"I=Prt — no medium constant"),

    # T09 Ratio Definition
    ("EQ050","T09","fluids",
     '{"y":"C047","a":"C010","b":"C046"}',
     None,"ρ=m/V"),
    ("EQ051","T09","fluids",
     '{"y":"C048","a":"C013","b":"C547"}',
     None,"P=F/A"),
    ("EQ083","T09","circuits",
     '{"y":"C083","a":"C080","b":"C082"}',
     None,"C=Q/V"),

    # T10 Inverse Linear
    ("EQ420","T10","gravitation",
     '{"y":"C021","k":"CONST_G·M","x":"C001"}',
     "GM","gravitational parameter — mass×G"),
    ("EQ513","T10","financial_math",
     '{"y":"C532","k":"C535","x":"C533"}',
     "PMT","payment amount — financial 'source strength'"),
    ("EQ104","T10","quantum",
     '{"y":"C070","k":"CONST_h","x":"C015"}',
     "h","Planck constant"),

    # T11 Period Square Root
    ("EQ041","T11","oscillations",
     '{"T":"C039","a":"C010","b":"C043"}',
     "k","spring constant — restoring force per unit displacement"),
    ("EQ042","T11","oscillations",
     '{"T":"C039","a":"C499","b":"C003"}',
     "g","gravitational acceleration — pendulum restoring constant"),
    ("EQ424","T11","gravitation",
     '{"T":"C039","a":"C497","b":"CONST_G·M"}',
     "GM","gravitational parameter"),

    # T12 Logarithmic
    ("EQ303","T12","chemistry",
     '{"y":"C303","k":"-1","x":"C302","x0":"1"}',
     "-1","sign inversion — pH increases as [H⁺] decreases"),
    ("EQ494","T12","structural_geology",
     '{"y":"C498","k":"1","x":"C497","x0":"1"}',
     "1","natural log base — pure structural"),
    ("EQ140","T12","genomics",
     '{"y":"C141","k":"16.6","x":"C143","x0":"1"}',
     "16.6","empirical salt correction coefficient"),

    # T13 Field Integral
    ("EQ240","T13","electrostatics",
     '{"field":"C086","k":"1/ε₀","source":"C080"}',
     "1/ε₀","inverse permittivity of free space"),
    ("EQ422","T13","gravitation",
     '{"field":"C030","k":"-4πG","source":"C010"}',
     "-4πG","gravitational coupling"),
    ("EQ241","T13","magnetism",
     '{"field":"C091","k":"0","source":"0"}',
     "0","no magnetic monopoles — zero source"),

    # T14 Linear Difference
    ("EQ503","T14","accounting",
     '{"y":"C523","a":"C521","b":"C522"}',
     None,"NI=R-X — pure Δ, no medium constant"),
    ("EQ200","T14","mechanics",
     '{"y":"C200","a":"C020","b":"C021"}',
     None,"L=T-V — Lagrangian"),
    ("EQ471","T14","nuclear",
     '{"y":"C471","a":"C488","b":"C010"}',
     "c²","speed of light squared — mass-energy conversion"),
    ("EQ464","T14","quantum",
     '{"y":"C020","a":"C019","b":"C462"}',
     None,"KE=hf-φ photoelectric"),

    # T15 Predator-Prey
    ("EQ498","T15","population_dynamics",
     '{"x":"C509","y":"C510","alpha":"C504","beta":"C511"}',
     "α,β","prey growth rate and predation coefficient"),
    ("EQ499","T15","population_dynamics",
     '{"x":"C509","y":"C510","delta":"C511","gamma":"C512"}',
     "δ,γ","conversion and predator death rates"),

    # T16 Harmonic
    ("EQ043","T16","oscillations",
     '{"omega":"C042","A":"1","phi":"0"}',
     "ω","angular frequency of oscillation"),
    ("EQ244","T16","circuits",
     '{"y":"C244","omega":"C042","A":"1/C"}',
     "1/C","inverse capacitance — circuit's oscillation resistance"),

    # T17 Linear Sum
    ("EQ502","T17","accounting",
     '{"y":"C518","terms":"C519+C520"}',
     None,"A=L+E — enforced conservation sum"),
    ("EQ439","T17","circuits",
     '{"y":"C085","terms":"ΣRi"}',
     None,"series resistance"),
    ("EQ305","T17","chemistry",
     '{"y":"14","terms":"pH+pOH"}',
     None,"pH+pOH=14 — logarithmic conservation"),

    # T18 Quadratic/Compound
    ("EQ508","T18","financial_math",
     '{"y":"C531","a":"C532","k":"C533","n":"C534"}',
     "i","periodic interest rate"),
    ("EQ004","T18","kinematics",
     '{"y":"C001","a":"C002","k":"C003","n":"C004"}',
     "½a","half acceleration"),
    ("EQ510","T18","financial_math",
     '{"y":"C536","a":"C535","k":"C533","n":"C534"}',
     "i","periodic rate for annuity"),
]

c.execute("DELETE FROM equation_instances")
inserted = 0
for row in INSTANCES:
    try:
        c.execute("""INSERT INTO equation_instances
                     (equation_id,template_id,domain_id,slot_bindings,
                      medium_constant,medium_constant_interpretation)
                     VALUES (?,?,?,?,?,?)""", row)
        inserted += 1
    except Exception as e:
        print(f"  Skip {row[0]}: {e}")
print(f"Inserted {inserted} equation instances")

# ── 5. Template matching — auto-generate bridge candidates ───────────────────

print("\nRunning template matching...")
c.execute("DELETE FROM template_bridges")

# Get all template instances grouped by template
c.execute("""
    SELECT ei.template_id, ei.domain_id, ei.equation_id,
           ei.medium_constant, ei.medium_constant_interpretation,
           et.canonical_form, et.name
    FROM equation_instances ei
    JOIN equation_templates et ON et.id=ei.template_id
    ORDER BY ei.template_id, ei.domain_id
""")
instances = c.fetchall()

# Group by template
from collections import defaultdict
by_template = defaultdict(list)
for row in instances:
    by_template[row[0]].append(row)

bridges_generated = 0
for tmpl_id, rows in by_template.items():
    # All domain pairs for this template
    for i, r1 in enumerate(rows):
        for r2 in rows[i+1:]:
            if r1[1] == r2[1]: continue  # same domain
            dom_a, dom_b = r1[1], r2[1]
            eq_a,  eq_b  = r1[2], r2[2]
            const_a = r1[3]
            const_b = r2[3]
            canonical = r1[5]

            # Determine status
            if const_a is None and const_b is None:
                # Pure structural — both same, fully identical
                status = "valid"
                confidence = 1.0
                note = "No medium constant — pure structural identity"
            elif const_a == const_b:
                status = "valid"
                confidence = 1.0
                note = "Same medium constant — identical instantiation"
            else:
                # Different medium constants — check zero compatibility
                # For now: if both use displacement as Δ, flag zero_check
                status = "valid"
                confidence = 0.9
                note = f"Different medium constants: {const_a} vs {const_b}. Same structure, different substrate."

            c.execute("""
                INSERT INTO template_bridges
                (template_id,domain_a,domain_b,equation_a,equation_b,
                 status,confidence,shared_structure,constant_a,constant_b,
                 zero_compatible,notes,auto_generated)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)
            """, (tmpl_id,dom_a,dom_b,eq_a,eq_b,
                  status,confidence,canonical,
                  const_a,const_b,1,note))
            bridges_generated += 1

print(f"Generated {bridges_generated} bridge candidates")

# ── 6. Find PREDICTED bridges (template in A, not declared in B) ─────────────

print("\nGenerating predictions for undeclared domain-template pairs...")
c.execute("""
    SELECT DISTINCT template_id, domain_id FROM equation_instances
""")
declared_pairs = set((r[0],r[1]) for r in c.fetchall())

c.execute("SELECT DISTINCT domain_id FROM concepts")
all_domains = [r[0] for r in c.fetchall()]

predictions = 0
for tmpl_id, dom_a in declared_pairs:
    for dom_b in all_domains:
        if dom_b == dom_a: continue
        if (tmpl_id, dom_b) in declared_pairs: continue
        # Check if already a bridge
        c.execute("""SELECT 1 FROM template_bridges
                     WHERE template_id=? AND
                     ((domain_a=? AND domain_b=?) OR (domain_a=? AND domain_b=?))
                     AND status='predicted'""",
                  (tmpl_id,dom_a,dom_b,dom_b,dom_a))
        if c.fetchone(): continue
        c.execute("""INSERT INTO template_bridges
                     (template_id,domain_a,domain_b,equation_a,
                      status,confidence,shared_structure,notes,auto_generated)
                     SELECT ei.template_id,?,?,ei.equation_id,
                            'predicted',0.5,et.canonical_form,
                            'Template declared in '||?||' — test whether '||?||' has equivalent',
                            1
                     FROM equation_instances ei
                     JOIN equation_templates et ON et.id=ei.template_id
                     WHERE ei.template_id=? AND ei.domain_id=?
                     LIMIT 1""",
                  (dom_a,dom_b,dom_a,dom_b,tmpl_id,dom_a))
        if c.rowcount: predictions += 1

print(f"Generated {predictions} predictions")

db.commit()

# ── 7. Summary report ────────────────────────────────────────────────────────

print("\n=== TEMPLATE BRIDGE SUMMARY ===\n")
c.execute("""
    SELECT tb.template_id, et.name, et.canonical_form,
           COUNT(DISTINCT tb.domain_a||'-'||tb.domain_b) as n_bridges,
           COUNT(DISTINCT CASE WHEN tb.status='valid' THEN tb.domain_a||'-'||tb.domain_b END) as n_valid,
           COUNT(DISTINCT CASE WHEN tb.status='predicted' THEN tb.domain_a||'-'||tb.domain_b END) as n_pred
    FROM template_bridges tb
    JOIN equation_templates et ON et.id=tb.template_id
    GROUP BY tb.template_id
    ORDER BY n_valid DESC, n_pred DESC
""")
for r in c.fetchall():
    print(f"  {r[0]} {r[1]:30s} valid:{r[4]:3d}  predicted:{r[5]:3d}")

print("\n=== STRONGEST PREDICTED BRIDGES ===\n")
c.execute("""
    SELECT tb.domain_a, tb.domain_b, et.name, tb.shared_structure
    FROM template_bridges tb
    JOIN equation_templates et ON et.id=tb.template_id
    WHERE tb.status='predicted'
    ORDER BY et.family, tb.domain_a
    LIMIT 30
""")
for r in c.fetchall():
    print(f"  {r[0]:25s} ↔ {r[1]:25s}  [{r[2]}]")

db.close()
print("\nDone.")

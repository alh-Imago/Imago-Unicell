"""
add_delta_schema.py
Adds nature + base_concept columns to concepts table,
then classifies all existing concepts.

nature values:
  delta    — directed difference between two states of base_concept
  rate     — change of base_concept per unit time (or per unit x)
  ratio    — dimensionless proportion of base_concept to reference
  absolute — standalone quantity, not a difference or rate

base_concept: concept id this is a delta/rate/ratio of, or NULL
"""
import sqlite3

DB = "concept_graph.db"
db = sqlite3.connect(DB)
c = db.cursor()

# ── Add columns ──────────────────────────────────────────────────────────────
for col, default in [("nature","absolute"), ("base_concept", None)]:
    try:
        c.execute(f"ALTER TABLE concepts ADD COLUMN {col} TEXT")
        print(f"Added column: {col}")
    except Exception as e:
        print(f"Column {col} already exists ({e})")

# Set default
c.execute("UPDATE concepts SET nature='absolute' WHERE nature IS NULL")

# ── Classify concepts ────────────────────────────────────────────────────────
# Format: (concept_id, nature, base_concept_id or None)
# Only classify non-absolute ones — absolute is already the default

CLASSIFICATIONS = [

    # ── DELTA concepts (directed differences) ───────────────────────────────
    # Kinematics / geometry
    ("C001","delta",  None),          # displacement Δx — base is position (no concept yet)
    ("C003","rate",   "C002"),        # acceleration = Δvelocity/Δtime
    # Dynamics
    ("C203","delta",  "C013"),        # impulse = Δmomentum
    # Energy
    ("C025","delta",  "C021"),        # work = ΔPE (or force·Δx)
    # Thermodynamics
    ("C062","delta",  None),          # internal energy — ΔU in first law
    ("C210","delta",  None),          # enthalpy ΔH
    ("C212","delta",  None),          # gibbs ΔG
    ("C211","delta",  None),          # helmholtz ΔA
    ("C063","delta",  None),          # entropy ΔS
    ("C067","delta",  None),          # reaction_enthalpy ΔH_rxn
    ("C123","delta",  None),          # gibbs_energy ΔG (thermochem)
    # Thermochem
    ("C318","delta",  None),          # chemical_affinity ΔA
    # Oscillations
    ("C403","delta",  None),          # phase_diff Δφ
    # Waves
    ("C405","delta",  "C041"),        # beat_frequency = Δfrequency
    # Electrostatics
    ("C082","delta",  None),          # electric_potential ΔV (potential difference)
    # Circuits
    ("C438","rate",   None),          # time_const_rc — characteristic Δ time
    ("C439","rate",   None),          # time_const_rl
    # Relativity
    ("C450","delta",  "C004"),        # time_dilation Δt
    ("C451","delta",  "C001"),        # length_contraction Δx
    # Genomics
    ("C141","delta",  None),          # melting_temperature ΔTm
    # Structural geology
    ("C493","delta",  None),          # longitudinal_strain Δl/l
    ("C496","delta",  None),          # shear_strain Δγ
    ("C498","delta",  None),          # natural_strain ln(Δl)
    # Financial math
    ("C528","delta",  "C527"),        # interest = FV - P (delta of principal)
    ("C531","delta",  "C527"),        # future_value - principal is the delta
    # Accounting
    ("C523","delta",  None),          # net_income = revenue - expenses (Δ equity)
    ("C526","delta",  None),          # retained_earnings = NI - dividends (Δ equity)
    # Population dynamics
    ("C508","rate",   "C503"),        # population_change dN/dt
    # Chemistry
    ("C543","delta",  None),          # absorbance = log(I0/I) — ratio of deltas
    ("C350","delta",  "C545"),        # nernst_potential — delta from standard electrode
    # Nuclear
    ("C471","delta",  "C010"),        # mass_defect Δm — delta of mass

    # ── RATE concepts (quantity per unit time or per unit x) ─────────────────
    ("C002","rate",   "C001"),        # velocity = Δx/Δt
    ("C005","rate",   "C007"),        # angular_velocity = Δangle/Δt
    ("C006","rate",   "C005"),        # angular_acceleration = Δω/Δt
    ("C026","rate",   "C025"),        # power = ΔE/Δt (work per time)
    ("C041","rate",   None),          # frequency = cycles/Δt
    ("C042","rate",   None),          # angular_frequency = 2π/period
    ("C084","rate",   "C080"),        # electric_current = Δcharge/Δt
    ("C088","rate",   None),          # magnetic_flux rate (EMF related)
    ("C120","rate",   None),          # activation_energy (rate threshold)
    ("C121","rate",   None),          # reaction_rate Δconcentration/Δt
    ("C253","rate",   "C503"),        # decay_constant λ = -ΔN/NΔt
    ("C470","rate",   "C503"),        # nuclear activity = -dN/dt
    ("C504","rate",   "C503"),        # intrinsic_growth_rate r
    ("C529","rate",   "C527"),        # simple_rate r (interest per year)
    ("C533","rate",   "C527"),        # periodic_rate i per period
    ("C309","rate",   None) if False else None,  # skip — placeholder
    ("C406","rate",   "C041"),        # doppler_freq — shifted rate

    # ── RATIO concepts (dimensionless proportions) ───────────────────────────
    ("C066","ratio",  None),          # thermal_efficiency W/Q_h
    ("C074","ratio",  None),          # refractive_index c/v
    ("C055","ratio",  None),          # reynolds_number ρvL/μ
    ("C056","ratio",  None),          # mach_number v/v_sound
    ("C102","ratio",  None),          # lorentz_factor γ
    ("C142","ratio",  None),          # gc_content — fraction
    ("C301","ratio",  None),          # mole_fraction
    ("C304","ratio",  None),          # activity (thermodynamic)
    ("C306","ratio",  None),          # electronegativity (Pauling scale ratio)
    ("C351","ratio",  None),          # reaction_quotient Q
    ("C312","ratio",  None),          # equilibrium_constant K
    ("C482","ratio",  None),          # magnification
    ("C501","ratio",  None),          # viscosity_ratio μ1/μ2
    ("C513","ratio",  None),          # geometric_ratio λ (finite growth rate)
    ("C516","ratio",  None),          # dhondt_quotient V/(s+1)
    ("C233","ratio",  None),          # froude_number
    ("C497","ratio",  None),          # stretch T_s = lf/lo
    ("C539","ratio",  None),          # equiv_payment_rate
    ("C538","ratio",  None),          # growth_rate k
]

updated = 0
for row in CLASSIFICATIONS:
    if row is None:
        continue
    cid, nature, base = row
    c.execute("UPDATE concepts SET nature=?, base_concept=? WHERE id=?",
              (nature, base, cid))
    updated += c.rowcount

db.commit()

# ── Report ────────────────────────────────────────────────────────────────────
print(f"Classified {updated} concepts")
c.execute("SELECT nature, COUNT(*) FROM concepts GROUP BY nature ORDER BY COUNT(*) DESC")
for r in c.fetchall(): print(f"  {r[0]:12s}: {r[1]}")

# Spot check
print("\nSample deltas:")
c.execute("SELECT id,name,nature,base_concept FROM concepts WHERE nature='delta' ORDER BY domain_id LIMIT 15")
for r in c.fetchall(): print(" ", r)
print("\nSample rates:")
c.execute("SELECT id,name,nature,base_concept FROM concepts WHERE nature='rate' ORDER BY domain_id LIMIT 10")
for r in c.fetchall(): print(" ", r)

db.close()
print("Done.")

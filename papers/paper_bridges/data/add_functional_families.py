"""
add_functional_families.py

Adds functional_family + canonical_form columns to equations table.
Classifies all 192 equations by their stripped mathematical structure.

Functional families:
  linear_flux       y = k·x              (Ohm, Fourier, Fick, Darcy, Beer-Lambert)
  linear_sum        y = a + b + c        (accounting, superposition, series R)
  linear_difference y = a - b            (net income, cell EMF, Lagrangian T-V)
  linear_product    y = a·b·c            (F=ma, momentum, impulse, simple interest)
  inverse_square    y = k/x²             (gravity, Coulomb, radiation intensity)
  inverse_linear    y = k/x              (Ohm rearranged, perpetuity PV, orbital v)
  exponential_decay y = y0·e^(-kx)       (decay law, RC discharge, damped SHM)
  exponential_growth y = y0·e^(kx)       (Malthusian, compound interest base)
  logistic          dy/dx = ky(1-y/K)    (Verhulst, epidemic, market saturation)
  power_law         y = k·xⁿ             (KE=½mv², spring PE, drag, Stefan-Boltzmann T⁴)
  logarithmic       y = k·log(x)         (pH, entropy, decibels, Beer-Lambert A)
  harmonic          y = A·cos(ωt+φ)      (SHM, AC circuits, waves)
  period_sqrt       T = 2π√(x/k)         (pendulum, spring — same form)
  conservation      Σin = Σout           (Kirchhoff, mass conservation, momentum)
  ratio_def         y = a/b              (density, pressure, concentration, efficiency)
  product_sum       y = Σ(aᵢbᵢ)         (dot products, work W=F·Δs cosθ)
  differential_rate dy/dt = f(y)         (all rate equations)
  wave_equation     y = A·sin(kx-ωt)    (wave propagation)
  inverse_sqrt      y = k/√x            (orbital speed, escape velocity)
  quadratic         y = ax² + bx + c    (kinematic EOM, annuity formulas)
  predator_prey     coupled dx/dt,dy/dt  (Lotka-Volterra)
  field_integral    ∮F·dA = source       (Gauss laws, Maxwell)
  other             does not fit cleanly
"""

import sqlite3

DB = "concept_graph.db"
db = sqlite3.connect(DB)
c = db.cursor()

# Add columns
for col in ("functional_family", "canonical_form"):
    try:
        c.execute(f"ALTER TABLE equations ADD COLUMN {col} TEXT")
        print(f"Added column: {col}")
    except:
        print(f"Column {col} exists")

# (eq_id, functional_family, canonical_form)
FAMILIES = [

    # ── linear_flux: flux = conductivity × Δ ────────────────────────────────
    ("EQ081","linear_flux",      "V = k·Δ"),           # Ohm V=IR
    ("EQ340","linear_flux",      "y = k·a·b"),          # Beer-Lambert A=εcl
    ("EQ331","linear_flux",      "Δy = k·x"),           # boiling point elevation
    ("EQ332","linear_flux",      "Δy = k·x"),           # freezing point depression
    ("EQ330","linear_flux",      "y = k·c"),            # osmotic pressure π=cRT

    # ── linear_product: y = a·b·c ────────────────────────────────────────────
    ("EQ010","linear_product",   "y = a·b"),            # F=ma
    ("EQ011","linear_product",   "y = a·b"),            # W=mg
    ("EQ012","linear_product",   "y = a·b"),            # p=mv
    ("EQ203","linear_product",   "y = a·b"),            # J=FΔt
    ("EQ025","linear_product",   "y = Δa/Δb"),          # P=ΔW/Δt
    ("EQ026","linear_product",   "y = a·b·cos"),        # P=Fv cosθ
    ("EQ024","linear_product",   "y = a·b·cos"),        # W=FΔs cosθ
    ("EQ084","linear_product",   "y = -Δa/Δb"),         # Faraday ε=-dΦ/dt
    ("EQ085","linear_product",   "y = a·b·c·sin"),      # FB=qvB sinθ
    ("EQ433","linear_product",   "y = a·b"),            # m=IA
    ("EQ438","linear_product",   "y = a·b"),            # Larmor ω=γB
    ("EQ470","linear_product",   "y = a·b"),            # Activity A=λN
    ("EQ506","linear_product",   "y = a·b·c"),          # simple interest I=Prt
    ("EQ322","linear_product",   "y = a·b·c/d"),        # Faraday electrolysis

    # ── linear_sum / linear_difference ──────────────────────────────────────
    ("EQ502","linear_sum",       "A = B + C"),          # accounting A=L+E
    ("EQ505","linear_sum",       "A = B+C+D-E-F"),      # expanded accounting
    ("EQ503","linear_difference","y = a - b"),          # NI=R-X
    ("EQ504","linear_difference","y = a - b"),          # RE=NI-D
    ("EQ200","linear_difference","y = a - b"),          # Lagrangian L=T-V
    ("EQ321","linear_difference","y = a - b"),          # cell EMF
    ("EQ501","linear_difference","y = a/(b+1)"),        # D'Hondt Q=V/(s+1)
    ("EQ439","linear_sum",       "y = Σaᵢ"),            # resistors series
    ("EQ440","linear_sum",       "1/y = Σ1/aᵢ"),        # resistors parallel
    ("EQ305","linear_sum",       "a + b = const"),      # pH+pOH=14

    # ── inverse_square: y = k/x² ────────────────────────────────────────────
    ("EQ030","inverse_square",   "y = k/x²"),           # Newton gravity
    ("EQ080","inverse_square",   "y = k·a·b/x²"),       # Coulomb
    ("EQ460","inverse_square",   "y = k/n²"),           # hydrogen levels
    ("EQ465","inverse_square",   "y = k(1/n1²-1/n2²)"), # Rydberg

    # ── inverse_linear: y = k/x ──────────────────────────────────────────────
    ("EQ513","inverse_linear",   "y = a/b"),            # perpetuity PV=PMT/i
    ("EQ031","inverse_sqrt",     "y = √(k/x)"),         # orbital speed
    ("EQ032","inverse_sqrt",     "y = √(k/x)"),         # escape speed
    ("EQ420","inverse_linear",   "y = -k/x"),           # grav potential U=-GM/r
    ("EQ421","inverse_linear",   "y = -k/x"),           # orbital energy

    # ── exponential_decay: y = y0·e^(-kx) ───────────────────────────────────
    ("EQ252","exponential_decay","y = y0·e^(-kx)"),     # decay law N=N0·e^-λt
    ("EQ120","exponential_decay","y = A·e^(-k/x)"),     # Arrhenius k=A·e^(-Ea/RT)
    ("EQ206","exponential_decay","y = A·e^(-kx)"),      # damped SHM energy
    ("EQ306","exponential_decay","y = e^(k·Δ)"),        # activity a=e^(μ-μ°)/RT
    ("EQ474","exponential_decay","y = ln(a/b)/k"),      # carbon dating t=ln(N0/N)/λ

    # ── exponential_growth / compound ────────────────────────────────────────
    ("EQ508","exponential_growth","y = a·(1+k)^n"),     # compound FV
    ("EQ509","exponential_growth","y = a·(1+k)^-n"),    # compound PV
    ("EQ496","exponential_growth","dy/dx = k·y"),       # Malthusian dN/dt=rN
    ("EQ500","exponential_growth","y(t+1) = λ·y(t)"),  # discrete geometric

    # ── logistic ─────────────────────────────────────────────────────────────
    ("EQ497","logistic",         "dy/dx = k·y·(1-y/K)"),# Verhulst logistic

    # ── power_law: y = k·xⁿ ─────────────────────────────────────────────────
    ("EQ020","power_law",        "y = k·x²"),           # KE=½mv²
    ("EQ022","power_law",        "y = k·x²"),           # spring PE=½kx²
    ("EQ066","power_law",        "y = k·x⁴"),           # Stefan-Boltzmann T⁴
    ("EQ230","power_law",        "y = k·x²"),           # drag D=½ρCdAv²
    ("EQ021","power_law",        "y = k·x"),            # grav PE=mgh (linear in h)
    ("EQ052","power_law",        "y = k·x"),            # buoyancy B=ρgV
    ("EQ100","power_law",        "y = k·x"),            # E=mc²
    ("EQ205","power_law",        "y = k·x²"),           # SHM energy ½mω²A²
    ("EQ472","power_law",        "y = k·x/n"),          # binding per nucleon

    # ── logarithmic: y = k·log(x) ────────────────────────────────────────────
    ("EQ303","logarithmic",      "y = -log(x)"),        # pH=-log[H+]
    ("EQ304","logarithmic",      "y = -log(x)"),        # pOH=-log[OH-]
    ("EQ320","logarithmic",      "y = a - k·ln(x)"),    # Nernst E=E°-(RT/nF)lnQ

    # ── harmonic / periodic ───────────────────────────────────────────────────
    ("EQ043","harmonic",         "ω = 2π/T"),           # angular frequency
    ("EQ244","harmonic",         "y = 1/(k·x)"),        # capacitive reactance
    ("EQ245","harmonic",         "y = k·x"),            # inductive reactance
    ("EQ436","harmonic",         "τ = a·b"),            # RC time constant
    ("EQ437","harmonic",         "τ = a/b"),            # RL time constant
    ("EQ434","harmonic",         "y = a·√2"),           # AC peak current
    ("EQ435","harmonic",         "y = a·b·cos"),        # AC power

    # ── period_sqrt: T = 2π√(a/b) ────────────────────────────────────────────
    ("EQ041","period_sqrt",      "T = 2π√(a/b)"),       # spring period
    ("EQ042","period_sqrt",      "T = 2π√(a/b)"),       # pendulum period
    ("EQ424","period_sqrt",      "T² = k·a³/b"),        # Kepler 3rd

    # ── conservation: Σin = Σout ─────────────────────────────────────────────
    ("EQ053","conservation",     "Σ(terms) = const"),   # Bernoulli
    ("EQ101","conservation",     "y = k·a·b"),          # relativistic energy γmc²
    ("EQ102","conservation",     "a² = b² + c²"),       # energy-momentum relation
    ("EQ253","conservation",     "y = (Σm_in - Σm_out)·c²"), # binding energy

    # ── ratio_def: y = a/b ───────────────────────────────────────────────────
    ("EQ050","ratio_def",        "y = a/b"),            # density ρ=m/V
    ("EQ051","ratio_def",        "y = a/b"),            # pressure P=F/A
    ("EQ054","ratio_def",        "y = a/b"),            # kinematic viscosity
    ("EQ055","ratio_def",        "y = a·b·c/d"),        # Reynolds number
    ("EQ083","ratio_def",        "y = a/b"),            # capacitance C=Q/V
    ("EQ300","ratio_def",        "y = a/b"),            # mole fraction
    ("EQ301","ratio_def",        "y = a·b"),            # partial pressure
    ("EQ302","ratio_def",        "y = da/db"),          # concentration [X]=dn/dV
    ("EQ482","ratio_def",        "y = -a/b"),           # magnification
    ("EQ516","ratio_def",        "y = a/(b+1)"),        # D'Hondt (same as linear_diff above -- reassign)

    # ── differential_rate: dy/dt = f(y) ─────────────────────────────────────
    ("EQ001","differential_rate","y = Δa/Δb"),          # velocity
    ("EQ002","differential_rate","y = Δa/Δb"),          # acceleration
    ("EQ025","differential_rate","y = Δa/Δb"),          # power P=ΔW/Δt (dup — ok)
    ("EQ508","differential_rate","y = a·(1+k)^n"),      # compound (dup — ok as growth)

    # ── predator_prey ─────────────────────────────────────────────────────────
    ("EQ498","predator_prey",    "dx/dt = ax - bxy"),   # LV prey
    ("EQ499","predator_prey",    "dy/dt = cxy - dy"),   # LV predator

    # ── field_integral: ∮F·dA = source ──────────────────────────────────────
    ("EQ240","field_integral",   "∮F·dA = k·source"),   # Gauss E
    ("EQ241","field_integral",   "∮F·dA = 0"),          # Gauss B
    ("EQ422","field_integral",   "∮F·dA = k·source"),   # grav Gauss
    ("EQ441","field_integral",   "∮F·dl = -dΦ/dt"),     # Maxwell-Faraday
    ("EQ442","field_integral",   "∮F·dl = k·source"),   # Maxwell-Ampere
    ("EQ431","field_integral",   "y = ∫F·dA"),          # current density

    # ── wave_equation ─────────────────────────────────────────────────────────
    ("EQ072","wave_equation",    "n1·sin(a) = n2·sin(b)"), # Snell
    ("EQ481","wave_equation",    "n1·sin(a) = n2·sin(b)"), # Snell (dup)
    ("EQ485","wave_equation",    "d·sin(θ) = m·λ"),     # diffraction
    ("EQ486","wave_equation",    "y = y0·cos²(θ)"),     # Malus law
    ("EQ487","wave_equation",    "θ = k·λ/D"),          # Rayleigh

    # ── inverse_square optics / thin lens ────────────────────────────────────
    ("EQ480","inverse_linear",   "1/a = 1/b + 1/c"),    # thin lens
    ("EQ484","inverse_linear",   "1/a = 1/b + 1/c"),    # mirror formula
    ("EQ483","inverse_linear",   "y = sin⁻¹(a/b)"),     # critical angle

    # ── quadratic / annuity ───────────────────────────────────────────────────
    ("EQ004","quadratic",        "y = a·x + k·x²"),     # EOM displacement
    ("EQ003","quadratic",        "y = a + b·x"),        # EOM velocity (linear in t)
    ("EQ510","quadratic",        "y = a·[(1+k)^n-1]/k"),# annuity FV
    ("EQ511","quadratic",        "y = a·[1-(1+k)^-n]/k"),# annuity PV
    ("EQ507","quadratic",        "y = a·(1+k·n)"),      # simple FV (linear in n)
    ("EQ514","quadratic",        "y = a·[(1+k)^n-(1+j)^n]/(k-j)"), # growing annuity FV
    ("EQ515","quadratic",        "y = a·[1-(1+j)^n(1+k)^-n]/(k-j)"),# growing annuity PV
    ("EQ512","quadratic",        "y = (1+k)^c - 1"),    # equiv payment rate

    # ── mechanics / action ────────────────────────────────────────────────────
    ("EQ201","linear_difference","y = a·b - c"),        # Hamiltonian
    ("EQ202","field_integral",   "y = ∫f dt"),          # action S=∫L dt
    ("EQ204","ratio_def",        "y = a·b/(a+b)"),      # reduced mass

    # ── quantum / special ─────────────────────────────────────────────────────
    ("EQ103","linear_product",   "y = a·b"),            # E=hf
    ("EQ104","inverse_linear",   "y = a/b"),            # de Broglie λ=h/p
    ("EQ106","power_law",        "Δa·Δb ≥ k"),          # uncertainty principle
    ("EQ250","other",            "∂Ψ/∂t = H·Ψ"),        # Schrodinger
    ("EQ251","ratio_def",        "|Ψ|² = prob"),        # Born rule
    ("EQ461","linear_difference","Δy = k·(1-cos)"),     # Compton
    ("EQ462","ratio_def",        "y = a²/b"),           # Bohr radius
    ("EQ463","linear_product",   "y = k·a"),            # zero point E=ℏω/2
    ("EQ464","linear_difference","y = a - b"),          # photoelectric KE=hf-φ

    # ── structural geology ────────────────────────────────────────────────────
    ("EQ488","linear_sum",       "y = k + a·cos(2θ)"),  # Mohr normal stress
    ("EQ489","linear_product",   "y = a·sin(2θ)"),      # Mohr shear
    ("EQ490","linear_flux",      "y = a·tan(φ) + c"),   # Mohr-Coulomb
    ("EQ492","linear_flux",      "y = k·x"),            # Hooke's law rock σ=Eε
    ("EQ493","linear_flux",      "y = k·x"),            # shear stress-strain τ=ηγ
    ("EQ494","logarithmic",      "y = ln(x)"),          # natural strain ln(lf/lo)
    ("EQ491","power_law",        "y² + k·y - c = 0"),   # Griffith criterion
    ("EQ495","power_law",        "y = k·x^(1/3)"),      # Biot-Ramberg

    # ── population dynamics ───────────────────────────────────────────────────
    # already done above (malthusian, logistic, LV, discrete)

    # ── financial additional ──────────────────────────────────────────────────
    ("EQ082","power_law",        "y = a·b = a²·c = b²/c"), # electric power P=VI=I²R
    ("EQ243","linear_sum",       "y = a + j(b-c)"),     # impedance Z=R+j(XL-XC)

    # ── gravitation additional ────────────────────────────────────────────────
    ("EQ105","ratio_def",        "y = k/(a·b)"),        # Hawking temperature
    ("EQ423","ratio_def",        "y = k·a"),            # Schwarzschild radius
    ("EQ425","power_law",        "y = k·a²/b"),         # grav binding energy

    # ── nuclear additional ────────────────────────────────────────────────────
    ("EQ471","linear_difference","y = Σa - b"),         # mass defect
    ("EQ473","linear_difference","y = (a-b)·c²"),       # Q value

    # ── relativity ────────────────────────────────────────────────────────────
    ("EQ100","power_law",        "y = a·b²"),           # E=mc²

    # ── genomics ─────────────────────────────────────────────────────────────
    ("EQ140","logarithmic",      "y = a + k·log(x) + b·z - c/n"), # DNA melting

    # ── fluids additional ─────────────────────────────────────────────────────
    ("EQ231","inverse_sqrt",     "y = a/√(b·c)"),       # Froude number
    ("EQ232","ratio_def",        "y = a/b"),            # surface tension γ=F/L
    ("EQ405","inverse_linear",   "sin(θ) = a/b"),       # Mach angle

    # ── heat transfer ─────────────────────────────────────────────────────────
    # EQ066 stefan-boltzmann already done above

    # ── electrostatics additional ─────────────────────────────────────────────
    ("EQ432","linear_product",   "y = a·b"),            # electric dipole p=qa

    # ── optics additional ─────────────────────────────────────────────────────
    # snell, magnification, etc. already done

    # ── chem_kinetics additional ──────────────────────────────────────────────
    ("EQ310","ratio_def",        "y = Π(prod)/Π(react)"),# equilibrium Kc
    ("EQ311","ratio_def",        "y = Π(prod)/Π(react)"),# reaction quotient Q

    # ── structural geology Biot-Ramberg and natural strain already above
    ("EQ496","exponential_growth","dy/dx = k·y"),       # malthusian (ensure set)
    ("EQ233","ratio_def",        "y = a/√(b·c)"),       # Froude alt

    # ── electromagnetism ─────────────────────────────────────────────────────
    ("EQ246","field_integral",   "F = q(E + v×B)"),     # Lorentz force
    ("EQ247","field_integral",   "S = a×b/k"),          # Poynting vector
    ("EQ430","field_integral",   "y = k·∮dl×r̂/r²"),    # Biot-Savart

    # ── oscillations ─────────────────────────────────────────────────────────
    ("EQ040","linear_product",   "y = -k·x"),           # Hooke's F=-kx

    # ── relativistic energy ───────────────────────────────────────────────────
    ("EQ102","conservation",     "a² = b² + c²"),       # energy-momentum

    # ── mechanics Lagrangian/Hamiltonian already done

    # ── population: discrete geometric already done
]

updated = 0
for row in FAMILIES:
    if row is None: continue
    eq_id, family, canonical = row
    c.execute("UPDATE equations SET functional_family=?, canonical_form=? WHERE id=? AND functional_family IS NULL",
              (family, canonical, eq_id))
    updated += c.rowcount

# Set remaining unclassified to 'other'
c.execute("UPDATE equations SET functional_family='other', canonical_form='see formula' WHERE functional_family IS NULL")
other = c.rowcount
print(f"Classified:   {updated}")
print(f"Set to other: {other}")

db.commit()

# ── Report: family counts and cross-domain spread ─────────────────────────────
print("\nFunctional family counts and domain spread:")
c.execute("""
    SELECT functional_family,
           COUNT(*) as n_eq,
           COUNT(DISTINCT domain_id) as n_domains,
           GROUP_CONCAT(DISTINCT domain_id) as domains
    FROM equations
    GROUP BY functional_family
    ORDER BY n_domains DESC, n_eq DESC
""")
for r in c.fetchall():
    print(f"\n  {r[0]} ({r[1]} eq, {r[2]} domains):")
    print(f"    {r[3]}")

db.close()
print("\nDone.")

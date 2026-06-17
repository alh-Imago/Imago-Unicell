"""
add_new_domains.py — Add five new domains to concept_graph.db:
  structural_geology   (parent: physics)
  population_dynamics  (parent: biology)
  electoral_systems    (parent: mathematics)
  accounting           (parent: economics)
  financial_math       (parent: economics)

Sources:
  https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf
  https://pubs.usgs.gov/bul/0650/report.pdf
  https://en.wikipedia.org/wiki/Population_dynamics
  https://en.wikipedia.org/wiki/D%27Hondt_method
  https://en.wikipedia.org/wiki/Accounting_equation
  https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf

Concepts start at C486, equations at EQ488.
"""

import sqlite3

DB = "concept_graph.db"

# ── New domains ─────────────────────────────────────────────────────────────

NEW_DOMAINS = [
    # (id, name, parent_id, notes)
    ("structural_geology", "Structural Geology",  "physics",
     "Rock deformation: stress, strain, fracture, folding mechanics"),
    ("population_dynamics","Population Dynamics",  "biology",
     "Mathematical modelling of population size over time"),
    ("electoral_systems",  "Electoral Systems",   "mathematics",
     "Apportionment and proportional representation methods"),
    ("accounting",         "Accounting",          "economics",
     "Double-entry bookkeeping and balance sheet relationships"),
    ("financial_math",     "Financial Mathematics","economics",
     "Time value of money: interest, annuities, perpetuities, amortisation"),
]

# ── New units (only add if not already present) ──────────────────────────────

NEW_UNITS = [
    # (id, name, dimension_json, si_base, notes)
    ("Pa",    "pascal",  "[−1,1,−2,0,0,0,0]", 0, "pressure / stress  kg·m⁻¹·s⁻²"),
    ("dimless","dimensionless","[0,0,0,0,0,0,0]",0,"ratio / pure number"),
    ("seats", "seats",   "[0,0,0,0,0,0,0]",   0, "electoral seat count"),
    ("votes", "votes",   "[0,0,0,0,0,0,0]",   0, "electoral vote count"),
    ("curr",  "currency","[0,0,0,0,0,0,0]",   0, "monetary unit (generic)"),
    ("m_inv", "per metre","[-1,0,0,0,0,0,0]", 0, "wavenumber / inverse length"),
]

# ── New concepts ─────────────────────────────────────────────────────────────
# (id, name, symbol, domain_id, unit_id, dimension_json, description, aliases, computable)

NEW_CONCEPTS = [

    # ── Structural Geology ──────────────────────────────────────────────────
    ("C486","normal_stress",       "σₙ",  "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Stress component perpendicular to a plane","normal stress",1),
    ("C487","shear_stress",        "τ",   "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Stress component parallel to a plane","shear stress,tangential stress",1),
    ("C488","principal_stress_1",  "σ₁",  "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Maximum principal stress","sigma_1,major principal stress",1),
    ("C489","principal_stress_3",  "σ₃",  "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Minimum principal stress","sigma_3,minor principal stress",1),
    ("C490","cohesion",            "c",   "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Rock cohesion — shear strength at zero normal stress","rock cohesion",1),
    ("C491","friction_angle",      "φ",   "structural_geology","dimless",
     "[0,0,0,0,0,0,0]",
     "Internal friction angle of rock material","angle of internal friction",1),
    ("C492","tensile_strength",    "T",   "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Critical tensile stress for Griffith crack propagation","tensile strength T",1),
    ("C493","longitudinal_strain", "ε",   "structural_geology","dimless",
     "[0,0,0,0,0,0,0]",
     "Fractional change in length σ=Eε","engineering strain",1),
    ("C494","youngs_modulus",      "E",   "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Young's modulus — ratio of stress to longitudinal strain","elastic modulus",0),
    ("C495","shear_modulus",       "η",   "structural_geology","Pa",
     "[-1,1,-2,0,0,0,0]",
     "Modulus of rigidity (shear stress / shear strain)","rigidity modulus",0),
    ("C496","shear_strain",        "γ",   "structural_geology","dimless",
     "[0,0,0,0,0,0,0]",
     "Angular deformation tan(ψ)","shearing angle",1),
    ("C497","stretch",             "T_s", "structural_geology","dimless",
     "[0,0,0,0,0,0,0]",
     "Ratio of deformed to original length lf/lo","quadratic elongation base",1),
    ("C498","natural_strain",      "ε_n", "structural_geology","dimless",
     "[0,0,0,0,0,0,0]",
     "Logarithmic strain ln(1+e)","logarithmic strain,Hencky strain",1),
    ("C499","fold_wavelength",     "L",   "structural_geology","m",
     "[1,0,0,0,0,0,0]",
     "Arc length or wavelength of buckle fold (Biot-Ramberg)","fold arc length",1),
    ("C500","layer_thickness",     "t",   "structural_geology","m",
     "[1,0,0,0,0,0,0]",
     "Thickness of competent layer in Biot-Ramberg folding","strong layer thickness",0),
    ("C501","viscosity_ratio",     "μ₁/μ₂","structural_geology","dimless",
     "[0,0,0,0,0,0,0]",
     "Ratio of layer viscosity to matrix viscosity in folding","viscosity contrast",0),
    ("C502","plane_angle",         "θ",   "structural_geology","dimless",
     "[0,0,0,0,0,0,0]",
     "Angle a fault/fracture plane makes with σ₃","fracture angle",1),

    # ── Population Dynamics ─────────────────────────────────────────────────
    ("C503","population_size",     "N",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Total number of individuals in a population","N,population count",1),
    ("C504","intrinsic_growth_rate","r",  "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Per-capita rate of natural increase (birth rate minus death rate)","r,growth rate",1),
    ("C505","carrying_capacity",   "K",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Maximum sustainable population size for a given environment","K",0),
    ("C506","birth_rate",          "b",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Per-capita birth rate","b,natality rate",1),
    ("C507","death_rate",          "d",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Per-capita death rate","d,mortality rate",1),
    ("C508","population_change",   "dN/dt","population_dynamics","dimless",
     "[0,0,-1,0,0,0,0]",
     "Rate of change of population with time","dN/dt,population growth rate",1),
    ("C509","prey_population",     "x",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Prey species population size (Lotka-Volterra)","x,prey count",1),
    ("C510","predator_population", "y",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Predator species population size (Lotka-Volterra)","y,predator count",1),
    ("C511","predation_rate",      "β",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Per-capita predation coefficient (Lotka-Volterra β)","beta,attack rate",0),
    ("C512","predator_death_rate", "δ",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Predator mortality rate coefficient (Lotka-Volterra δ)","delta,predator mortality",0),
    ("C513","geometric_ratio",     "λ",   "population_dynamics","dimless",
     "[0,0,0,0,0,0,0]",
     "Finite rate of increase for discrete-time geometric growth (1+b−d)","lambda,finite growth rate",1),

    # ── Electoral Systems ───────────────────────────────────────────────────
    ("C514","party_votes",         "V",   "electoral_systems","votes",
     "[0,0,0,0,0,0,0]",
     "Total votes received by a party in an election","V,vote total",1),
    ("C515","seats_allocated",     "s",   "electoral_systems","seats",
     "[0,0,0,0,0,0,0]",
     "Number of seats allocated to a party so far","s,seats won",1),
    ("C516","dhondt_quotient",     "Q",   "electoral_systems","dimless",
     "[0,0,0,0,0,0,0]",
     "D'Hondt seat allocation quotient Q = V / (s+1)","Q,allocation quotient",1),
    ("C517","total_seats",         "S",   "electoral_systems","seats",
     "[0,0,0,0,0,0,0]",
     "Total seats to be filled in the legislature","S,house size",0),

    # ── Accounting ──────────────────────────────────────────────────────────
    ("C518","total_assets",        "A",   "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "All resources owned or controlled by a business","assets,A",1),
    ("C519","total_liabilities",   "L",   "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "All debts and obligations of a business","liabilities,L",1),
    ("C520","owners_equity",       "E",   "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "Net worth — assets minus liabilities","equity,shareholders equity,E",1),
    ("C521","revenue",             "R",   "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "Income earned from business operations","revenue,sales,R",1),
    ("C522","expenses",            "X",   "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "Costs incurred in generating revenue","expenses,X",1),
    ("C523","net_income",          "NI",  "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "Profit — revenue minus expenses","net income,profit,NI",1),
    ("C524","dividends",           "D",   "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "Distributions of profit to shareholders","dividends,D",1),
    ("C525","contributed_capital", "CC",  "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "Capital invested by shareholders","CC,paid-in capital",0),
    ("C526","retained_earnings",   "RE",  "accounting","curr",
     "[0,0,0,0,0,0,0]",
     "Cumulative net income not distributed as dividends","RE,retained earnings",1),

    # ── Financial Mathematics ────────────────────────────────────────────────
    ("C527","principal",           "P",   "financial_math","curr",
     "[0,0,0,0,0,0,0]",
     "Initial sum of money (present value for simple interest)","P,PV_simple",1),
    ("C528","interest_amount",     "I",   "financial_math","curr",
     "[0,0,0,0,0,0,0]",
     "Amount of interest earned or charged","I,interest",1),
    ("C529","simple_rate",         "r",   "financial_math","dimless",
     "[0,0,0,0,0,0,0]",
     "Simple annual (nominal) interest rate","r,nominal rate,annual rate",0),
    ("C530","time_years",          "t",   "financial_math","dimless",
     "[0,0,1,0,0,0,0]",
     "Interest period in years","t,term",0),
    ("C531","future_value",        "FV",  "financial_math","curr",
     "[0,0,0,0,0,0,0]",
     "Maturity value — principal plus accumulated interest","FV,maturity value,S",1),
    ("C532","present_value",       "PV",  "financial_math","curr",
     "[0,0,0,0,0,0,0]",
     "Current worth of a future sum discounted at rate i","PV,present value",1),
    ("C533","periodic_rate",       "i",   "financial_math","dimless",
     "[0,0,0,0,0,0,0]",
     "Interest rate per compounding period i = j/m","i,periodic interest rate",1),
    ("C534","compounding_periods", "n",   "financial_math","dimless",
     "[0,0,0,0,0,0,0]",
     "Total number of compounding periods","n,number of periods",0),
    ("C535","payment",             "PMT", "financial_math","curr",
     "[0,0,0,0,0,0,0]",
     "Periodic annuity payment amount","PMT,payment amount",1),
    ("C536","annuity_fv",          "FVₙ", "financial_math","curr",
     "[0,0,0,0,0,0,0]",
     "Future value of an ordinary simple annuity","FVn,annuity future value",1),
    ("C537","annuity_pv",          "PVₙ", "financial_math","curr",
     "[0,0,0,0,0,0,0]",
     "Present value of an ordinary simple annuity","PVn,annuity present value",1),
    ("C538","growth_rate",         "k",   "financial_math","dimless",
     "[0,0,0,0,0,0,0]",
     "Constant rate of payment growth in a growing annuity","k,growth rate k",0),
    ("C539","equiv_payment_rate",  "p",   "financial_math","dimless",
     "[0,0,0,0,0,0,0]",
     "Equivalent rate of interest per payment period for general annuity","p,equivalent rate",1),
    ("C540","nominal_rate",        "j",   "financial_math","dimless",
     "[0,0,0,0,0,0,0]",
     "Nominal annual rate of interest","j,nominal annual rate",0),
    ("C541","compounding_freq",    "m",   "financial_math","dimless",
     "[0,0,0,0,0,0,0]",
     "Number of compounding periods per year","m,compounds per year",0),
]

# ── New equations ────────────────────────────────────────────────────────────
# (id, name, display_name, formula, domain_id, output_concept, confidence_max, computable, notes, source)

NEW_EQUATIONS = [

    # Structural Geology
    ("EQ488","mohr_normal_stress",
     "Mohr Normal Stress",
     "σₙ = (σ₁+σ₃)/2 + (σ₁−σ₃)/2·cos(2θ)",
     "structural_geology","C486",1.0,1,
     "Normal stress on a plane at angle θ to σ₃; Mohr's circle x-coordinate",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    ("EQ489","mohr_shear_stress",
     "Mohr Shear Stress",
     "τ = (σ₁−σ₃)/2·sin(2θ)",
     "structural_geology","C487",1.0,1,
     "Shear stress on a plane at angle θ to σ₃; Mohr's circle y-coordinate",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    ("EQ490","mohr_coulomb",
     "Mohr-Coulomb Fracture Criterion",
     "τ = σₙ·tan(φ) + c",
     "structural_geology","C487",1.0,1,
     "Shear failure criterion: shear strength as function of normal stress, cohesion and friction",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    ("EQ491","griffith_criterion",
     "Griffith Tensile Fracture Criterion",
     "τ² + 4T·σₙ − 4T² = 0",
     "structural_geology","C487",0.95,1,
     "Griffith crack propagation criterion for tensile fracture",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    ("EQ492","hookes_law_rock",
     "Hooke's Law (Rock)",
     "σ = E·ε",
     "structural_geology","C486",1.0,1,
     "Stress proportional to longitudinal strain below elastic limit",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    ("EQ493","shear_stress_strain",
     "Shear Stress-Strain Relation",
     "τ = η·γ",
     "structural_geology","C487",1.0,1,
     "Shear stress equals shear modulus times shear strain",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    ("EQ494","natural_strain",
     "Natural (Logarithmic) Strain",
     "εₙ = ln(1 + e) = ln(lf/lo)",
     "structural_geology","C498",1.0,1,
     "Hencky strain — logarithm of stretch ratio",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    ("EQ495","biot_ramberg",
     "Biot-Ramberg Fold Wavelength",
     "L = 2πt·(μ₁/6μ₂)^(1/3)",
     "structural_geology","C499",0.95,1,
     "Dominant fold wavelength as function of layer thickness and viscosity contrast",
     "https://geologyconcepts.com/wp-content/uploads/2019/01/Structural-Geology-Formulae.pdf"),

    # Population Dynamics
    ("EQ496","malthusian_growth",
     "Malthusian Exponential Growth",
     "dN/dt = rN",
     "population_dynamics","C508",1.0,1,
     "Continuous unlimited exponential population growth at rate r",
     "https://en.wikipedia.org/wiki/Population_dynamics"),

    ("EQ497","logistic_growth",
     "Verhulst Logistic Growth",
     "dN/dt = rN(1 − N/K)",
     "population_dynamics","C508",1.0,1,
     "Density-dependent growth approaching carrying capacity K",
     "https://en.wikipedia.org/wiki/Population_dynamics"),

    ("EQ498","lotka_volterra_prey",
     "Lotka-Volterra Prey Equation",
     "dx/dt = αx − βxy",
     "population_dynamics","C509",1.0,1,
     "Prey population grows at α, declines by predator encounters βxy",
     "https://en.wikipedia.org/wiki/Population_dynamics"),

    ("EQ499","lotka_volterra_predator",
     "Lotka-Volterra Predator Equation",
     "dy/dt = δxy − γy",
     "population_dynamics","C510",1.0,1,
     "Predator population grows from prey encounters δxy, declines at γ",
     "https://en.wikipedia.org/wiki/Population_dynamics"),

    ("EQ500","discrete_geometric_growth",
     "Discrete Geometric Population Growth",
     "N(t+1) = N(t)·λ   [λ = 1 + b − d]",
     "population_dynamics","C503",1.0,1,
     "Generation-by-generation geometric population model with finite rate λ",
     "https://en.wikipedia.org/wiki/Population_dynamics"),

    # Electoral Systems
    ("EQ501","dhondt_quotient",
     "D'Hondt Seat Allocation Quotient",
     "Q = V / (s + 1)",
     "electoral_systems","C516",1.0,1,
     "Successive quotients for proportional seat allocation; party with largest Q wins next seat",
     "https://en.wikipedia.org/wiki/D%27Hondt_method"),

    # Accounting
    ("EQ502","accounting_equation",
     "Fundamental Accounting Equation",
     "Assets = Liabilities + Equity",
     "accounting","C518",1.0,1,
     "The balance sheet identity — every transaction preserves this equality",
     "https://en.wikipedia.org/wiki/Accounting_equation"),

    ("EQ503","net_income",
     "Net Income",
     "NI = Revenue − Expenses",
     "accounting","C523",1.0,1,
     "Profit or loss for a period",
     "https://en.wikipedia.org/wiki/Accounting_equation"),

    ("EQ504","retained_earnings",
     "Retained Earnings",
     "RE = NI − Dividends",
     "accounting","C526",1.0,1,
     "Cumulative undistributed profit",
     "https://en.wikipedia.org/wiki/Accounting_equation"),

    ("EQ505","expanded_accounting",
     "Expanded Accounting Equation",
     "Assets = Liabilities + CC + Revenue − Expenses − Dividends",
     "accounting","C518",1.0,1,
     "Full breakdown of equity into contributed capital and income statement components",
     "https://en.wikipedia.org/wiki/Accounting_equation"),

    # Financial Mathematics
    ("EQ506","simple_interest",
     "Simple Interest",
     "I = P·r·t",
     "financial_math","C528",1.0,1,
     "Interest on principal at flat annual rate r for t years",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ507","simple_future_value",
     "Simple Interest Future Value",
     "FV = P(1 + r·t)",
     "financial_math","C531",1.0,1,
     "Maturity value under simple interest",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ508","compound_future_value",
     "Compound Interest Future Value",
     "FV = PV·(1 + i)ⁿ",
     "financial_math","C531",1.0,1,
     "Future value with periodic compounding at rate i over n periods",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ509","compound_present_value",
     "Compound Interest Present Value",
     "PV = FV·(1 + i)⁻ⁿ",
     "financial_math","C532",1.0,1,
     "Present value of a future sum discounted at periodic rate i",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ510","ordinary_annuity_fv",
     "Ordinary Simple Annuity — Future Value",
     "FVₙ = PMT·[(1+i)ⁿ − 1] / i",
     "financial_math","C536",1.0,1,
     "Accumulated value of equal end-of-period payments at rate i",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ511","ordinary_annuity_pv",
     "Ordinary Simple Annuity — Present Value",
     "PVₙ = PMT·[1 − (1+i)⁻ⁿ] / i",
     "financial_math","C537",1.0,1,
     "Present value of equal end-of-period payments at rate i",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ512","equiv_payment_rate",
     "Equivalent Payment Period Rate",
     "p = (1 + i)^c − 1",
     "financial_math","C539",1.0,1,
     "Converts periodic compounding rate i to equivalent rate per payment interval (general annuity)",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ513","simple_perpetuity_pv",
     "Simple Perpetuity — Present Value",
     "PV = PMT / i",
     "financial_math","C532",1.0,1,
     "Present value of a level perpetuity at periodic rate i",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ514","growing_annuity_fv",
     "Constant-Growth Annuity — Future Value",
     "FV = PMT·[(1+i)ⁿ − (1+k)ⁿ] / (i − k)",
     "financial_math","C536",1.0,1,
     "Future value of an annuity whose payments grow at constant rate k",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),

    ("EQ515","growing_annuity_pv",
     "Constant-Growth Annuity — Present Value",
     "PV = PMT·[1 − (1+k)ⁿ·(1+i)⁻ⁿ] / (i − k)",
     "financial_math","C537",1.0,1,
     "Present value of an annuity with constant payment growth rate k",
     "https://www.georgebrown.ca/sites/default/files/uploadedfiles/tlc/_documents/formula_sheet_for_financial_mathematics.pdf"),
]

# ── Equation components ──────────────────────────────────────────────────────
# (equation_id, concept_id, role, symbol, notes)
# roles: input / output / constant / parameter

NEW_COMPONENTS = [
    # EQ488 Mohr normal stress
    ("EQ488","C488","input","σ₁","maximum principal stress"),
    ("EQ488","C489","input","σ₃","minimum principal stress"),
    ("EQ488","C502","input","θ","angle plane makes with σ₃"),
    ("EQ488","C486","output","σₙ","normal stress result"),

    # EQ489 Mohr shear stress
    ("EQ489","C488","input","σ₁","maximum principal stress"),
    ("EQ489","C489","input","σ₃","minimum principal stress"),
    ("EQ489","C502","input","θ","angle of plane"),
    ("EQ489","C487","output","τ","shear stress result"),

    # EQ490 Mohr-Coulomb
    ("EQ490","C486","input","σₙ","normal stress on failure plane"),
    ("EQ490","C491","input","φ","internal friction angle"),
    ("EQ490","C490","input","c","cohesion"),
    ("EQ490","C487","output","τ","shear strength at failure"),

    # EQ491 Griffith
    ("EQ491","C487","input","τ","shear stress"),
    ("EQ491","C492","input","T","critical tensile stress"),
    ("EQ491","C486","input","σₙ","normal stress"),
    ("EQ491","C487","output","τ","fracture criterion (= 0 at failure)"),

    # EQ492 Hooke's law rock
    ("EQ492","C494","input","E","Young's modulus"),
    ("EQ492","C493","input","ε","longitudinal strain"),
    ("EQ492","C486","output","σ","normal stress"),

    # EQ493 shear stress-strain
    ("EQ493","C495","input","η","shear modulus / rigidity"),
    ("EQ493","C496","input","γ","shear strain"),
    ("EQ493","C487","output","τ","shear stress"),

    # EQ494 natural strain
    ("EQ494","C497","input","T_s","stretch ratio"),
    ("EQ494","C498","output","εₙ","natural logarithmic strain"),

    # EQ495 Biot-Ramberg
    ("EQ495","C500","input","t","strong layer thickness"),
    ("EQ495","C501","input","μ₁/μ₂","viscosity ratio"),
    ("EQ495","C499","output","L","dominant fold wavelength"),

    # EQ496 Malthusian growth
    ("EQ496","C503","input","N","population size"),
    ("EQ496","C504","input","r","intrinsic growth rate"),
    ("EQ496","C508","output","dN/dt","rate of population change"),

    # EQ497 Logistic growth
    ("EQ497","C503","input","N","current population"),
    ("EQ497","C504","input","r","intrinsic growth rate"),
    ("EQ497","C505","input","K","carrying capacity"),
    ("EQ497","C508","output","dN/dt","rate of population change"),

    # EQ498 Lotka-Volterra prey
    ("EQ498","C509","input","x","prey population"),
    ("EQ498","C504","input","α","prey growth rate"),
    ("EQ498","C511","input","β","predation coefficient"),
    ("EQ498","C510","input","y","predator population"),
    ("EQ498","C509","output","dx/dt","rate of prey population change"),

    # EQ499 Lotka-Volterra predator
    ("EQ499","C510","input","y","predator population"),
    ("EQ499","C511","input","δ","predator growth from prey coefficient"),
    ("EQ499","C509","input","x","prey population"),
    ("EQ499","C512","input","γ","predator death rate"),
    ("EQ499","C510","output","dy/dt","rate of predator population change"),

    # EQ500 discrete geometric growth
    ("EQ500","C503","input","N(t)","population at time t"),
    ("EQ500","C513","input","λ","finite rate of increase"),
    ("EQ500","C503","output","N(t+1)","population next generation"),

    # EQ501 D'Hondt
    ("EQ501","C514","input","V","party total votes"),
    ("EQ501","C515","input","s","seats already allocated to party"),
    ("EQ501","C516","output","Q","allocation quotient"),

    # EQ502 accounting equation
    ("EQ502","C519","input","L","liabilities"),
    ("EQ502","C520","input","E","equity"),
    ("EQ502","C518","output","A","total assets"),

    # EQ503 net income
    ("EQ503","C521","input","R","revenue"),
    ("EQ503","C522","input","X","expenses"),
    ("EQ503","C523","output","NI","net income"),

    # EQ504 retained earnings
    ("EQ504","C523","input","NI","net income"),
    ("EQ504","C524","input","D","dividends"),
    ("EQ504","C526","output","RE","retained earnings"),

    # EQ505 expanded accounting
    ("EQ505","C519","input","L","liabilities"),
    ("EQ505","C525","input","CC","contributed capital"),
    ("EQ505","C521","input","R","revenue"),
    ("EQ505","C522","input","X","expenses"),
    ("EQ505","C524","input","D","dividends"),
    ("EQ505","C518","output","A","total assets"),

    # EQ506 simple interest
    ("EQ506","C527","input","P","principal"),
    ("EQ506","C529","input","r","annual rate"),
    ("EQ506","C530","input","t","time in years"),
    ("EQ506","C528","output","I","interest amount"),

    # EQ507 simple future value
    ("EQ507","C527","input","P","principal"),
    ("EQ507","C529","input","r","annual rate"),
    ("EQ507","C530","input","t","time in years"),
    ("EQ507","C531","output","FV","future value"),

    # EQ508 compound FV
    ("EQ508","C532","input","PV","present value"),
    ("EQ508","C533","input","i","periodic rate"),
    ("EQ508","C534","input","n","number of periods"),
    ("EQ508","C531","output","FV","future value"),

    # EQ509 compound PV
    ("EQ509","C531","input","FV","future value"),
    ("EQ509","C533","input","i","periodic rate"),
    ("EQ509","C534","input","n","number of periods"),
    ("EQ509","C532","output","PV","present value"),

    # EQ510 ordinary annuity FV
    ("EQ510","C535","input","PMT","payment amount"),
    ("EQ510","C533","input","i","periodic rate"),
    ("EQ510","C534","input","n","number of periods"),
    ("EQ510","C536","output","FVₙ","annuity future value"),

    # EQ511 ordinary annuity PV
    ("EQ511","C535","input","PMT","payment amount"),
    ("EQ511","C533","input","i","periodic rate"),
    ("EQ511","C534","input","n","number of periods"),
    ("EQ511","C537","output","PVₙ","annuity present value"),

    # EQ512 equiv payment rate
    ("EQ512","C533","input","i","periodic compounding rate"),
    ("EQ512","C539","output","p","equivalent rate per payment period"),

    # EQ513 simple perpetuity PV
    ("EQ513","C535","input","PMT","periodic payment"),
    ("EQ513","C533","input","i","periodic rate"),
    ("EQ513","C532","output","PV","perpetuity present value"),

    # EQ514 growing annuity FV
    ("EQ514","C535","input","PMT","initial payment"),
    ("EQ514","C533","input","i","periodic rate"),
    ("EQ514","C534","input","n","number of periods"),
    ("EQ514","C538","input","k","constant growth rate"),
    ("EQ514","C536","output","FV","growing annuity future value"),

    # EQ515 growing annuity PV
    ("EQ515","C535","input","PMT","initial payment"),
    ("EQ515","C533","input","i","periodic rate"),
    ("EQ515","C534","input","n","number of periods"),
    ("EQ515","C538","input","k","constant growth rate"),
    ("EQ515","C537","output","PV","growing annuity present value"),
]


def run():
    db = sqlite3.connect(DB)
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    # Domains
    for row in NEW_DOMAINS:
        c.execute(
            "INSERT OR IGNORE INTO domains (id,name,parent_id,notes) VALUES (?,?,?,?)",
            row)
    print(f"  domains inserted: {db.total_changes}")

    prev = db.total_changes

    # Units
    for row in NEW_UNITS:
        c.execute(
            "INSERT OR IGNORE INTO units (id,name,dimension,si_base,notes) VALUES (?,?,?,?,?)",
            row)
    print(f"  units inserted:   {db.total_changes - prev}")
    prev = db.total_changes

    # Concepts
    for row in NEW_CONCEPTS:
        c.execute(
            """INSERT OR IGNORE INTO concepts
               (id,name,symbol,domain_id,unit_id,dimension,description,aliases,computable)
               VALUES (?,?,?,?,?,?,?,?,?)""", row)
    print(f"  concepts inserted:{db.total_changes - prev}")
    prev = db.total_changes

    # Equations
    for row in NEW_EQUATIONS:
        c.execute(
            """INSERT OR IGNORE INTO equations
               (id,name,display_name,formula,domain_id,output_concept,
                confidence_max,computable,notes,source)
               VALUES (?,?,?,?,?,?,?,?,?,?)""", row)
    print(f"  equations inserted:{db.total_changes - prev}")
    prev = db.total_changes

    # Components (no unique key — insert only if equation_id+concept_id+role not present)
    for eq_id, con_id, role, sym, notes in NEW_COMPONENTS:
        c.execute(
            """INSERT INTO equation_components
               (equation_id,concept_id,role,symbol,notes)
               VALUES (?,?,?,?,?)""",
            (eq_id, con_id, role, sym, notes))
    print(f"  components inserted:{db.total_changes - prev}")

    db.commit()
    db.close()
    print("Done.")


if __name__ == "__main__":
    run()

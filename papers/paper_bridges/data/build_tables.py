"""
build_tables.py — Build the Imago ConceptGraph base tables from physics equation sources.

Tables:
  domains            — knowledge domains
  concepts           — every discrete physical quantity / concept
  units              — SI and derived units
  equations          — named equations / mechanisms
  equation_components — join: equation ↔ concepts with roles
  constants          — physical constants used in equations
"""

import sqlite3
import json

DB = "concept_graph.db"

# ── Schema ─────────────────────────────────────────────────────────────────

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS domains (
    id          TEXT PRIMARY KEY,   -- e.g. "mechanics"
    name        TEXT NOT NULL,      -- display name
    parent_id   TEXT,               -- e.g. "physics" → "mechanics" 
    notes       TEXT,
    FOREIGN KEY (parent_id) REFERENCES domains(id)
);

CREATE TABLE IF NOT EXISTS units (
    id          TEXT PRIMARY KEY,   -- e.g. "J"
    name        TEXT NOT NULL,      -- "joule"
    dimension   TEXT NOT NULL,      -- JSON [m,kg,s,A,K,mol,cd]
    si_base     INTEGER DEFAULT 0,  -- 1 if base SI unit
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS concepts (
    id          TEXT PRIMARY KEY,   -- e.g. "C001"
    name        TEXT NOT NULL,      -- canonical name e.g. "kinetic_energy"
    symbol      TEXT,               -- e.g. "KE" or "½mv²"
    domain_id   TEXT NOT NULL,
    unit_id     TEXT,               -- SI unit for this concept
    dimension   TEXT NOT NULL,      -- JSON [m,kg,s,A,K,mol,cd]
    description TEXT,
    aliases     TEXT,               -- JSON list of alternative names
    computable  INTEGER DEFAULT 1,  -- 1 = can be computed on fabric
    FOREIGN KEY (domain_id) REFERENCES domains(id),
    FOREIGN KEY (unit_id)   REFERENCES units(id)
);

CREATE TABLE IF NOT EXISTS equations (
    id              TEXT PRIMARY KEY,   -- e.g. "EQ001"
    name            TEXT NOT NULL,      -- e.g. "kinetic_energy"
    display_name    TEXT,               -- e.g. "Kinetic Energy"
    formula         TEXT NOT NULL,      -- e.g. "KE = ½mv²"
    domain_id       TEXT NOT NULL,
    output_concept  TEXT NOT NULL,      -- concept this equation produces
    confidence_max  REAL DEFAULT 1.0,   -- 1.0 = derived; <1.0 = empirical
    computable      INTEGER DEFAULT 1,  -- 1 = can run on UniCell fabric
    notes           TEXT,
    source          TEXT,               -- citation
    FOREIGN KEY (domain_id)      REFERENCES domains(id),
    FOREIGN KEY (output_concept) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS equation_components (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    equation_id TEXT NOT NULL,
    concept_id  TEXT NOT NULL,
    role        TEXT NOT NULL,   -- "input", "output", "constant", "parameter"
    symbol      TEXT,            -- symbol used in this equation for this concept
    notes       TEXT,
    FOREIGN KEY (equation_id) REFERENCES equations(id),
    FOREIGN KEY (concept_id)  REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS constants (
    id          TEXT PRIMARY KEY,   -- e.g. "CONST_c"
    name        TEXT NOT NULL,      -- "speed of light"
    symbol      TEXT NOT NULL,      -- "c"
    value       REAL,               -- numerical value
    unit_id     TEXT,
    dimension   TEXT,               -- JSON [m,kg,s,A,K,mol,cd]
    exact        INTEGER DEFAULT 0, -- 1 if exact by definition
    source      TEXT,               -- e.g. "CODATA 2018"
    notes       TEXT,
    FOREIGN KEY (unit_id) REFERENCES units(id)
);

-- Search indices
CREATE INDEX IF NOT EXISTS idx_concepts_domain  ON concepts(domain_id);
CREATE INDEX IF NOT EXISTS idx_concepts_unit    ON concepts(unit_id);
CREATE INDEX IF NOT EXISTS idx_eq_domain        ON equations(domain_id);
CREATE INDEX IF NOT EXISTS idx_eq_output        ON equations(output_concept);
CREATE INDEX IF NOT EXISTS idx_eqcomp_eq        ON equation_components(equation_id);
CREATE INDEX IF NOT EXISTS idx_eqcomp_concept   ON equation_components(concept_id);
CREATE INDEX IF NOT EXISTS idx_eqcomp_role      ON equation_components(role);
"""

# ── Seed data ──────────────────────────────────────────────────────────────

DOMAINS = [
    # Top level
    ("physics",          "Physics",              None),
    ("mathematics",      "Mathematics",          None),
    ("chemistry",        "Chemistry",            None),
    ("biology",          "Biology",              None),
    ("economics",        "Economics",            None),
    # Physics subdomains
    ("mechanics",        "Mechanics",            "physics"),
    ("kinematics",       "Kinematics",           "mechanics"),
    ("dynamics",         "Dynamics",             "mechanics"),
    ("energy_domain",    "Energy",               "mechanics"),
    ("momentum_domain",  "Momentum",             "mechanics"),
    ("rotation",         "Rotational Motion",    "mechanics"),
    ("gravitation",      "Gravitation",          "mechanics"),
    ("oscillations",     "Oscillations",         "mechanics"),
    ("fluids",           "Fluid Mechanics",      "mechanics"),
    ("thermodynamics",   "Thermodynamics",       "physics"),
    ("heat_transfer",    "Heat Transfer",        "thermodynamics"),
    ("waves",            "Waves & Optics",       "physics"),
    ("optics",           "Optics",               "waves"),
    ("electromagnetism", "Electromagnetism",     "physics"),
    ("electrostatics",   "Electrostatics",       "electromagnetism"),
    ("circuits",         "Electric Circuits",    "electromagnetism"),
    ("magnetism",        "Magnetism",            "electromagnetism"),
    ("modern_physics",   "Modern Physics",       "physics"),
    ("relativity",       "Relativity",           "modern_physics"),
    ("quantum",          "Quantum Mechanics",    "modern_physics"),
    ("nuclear",          "Nuclear Physics",      "modern_physics"),
    # Chemistry subdomains
    ("chem_kinetics",    "Chemical Kinetics",    "chemistry"),
    ("thermochem",       "Thermochemistry",      "chemistry"),
    # Biology subdomains
    ("genomics",         "Genomics",             "biology"),
    ("biochemistry",     "Biochemistry",         "biology"),
]

# SI base and common derived units
# dimension: [m, kg, s, A, K, mol, cd]
UNITS = [
    # Base SI
    ("m",    "metre",          [1,0,0,0,0,0,0],  1),
    ("kg",   "kilogram",       [0,1,0,0,0,0,0],  1),
    ("s",    "second",         [0,0,1,0,0,0,0],  1),
    ("A",    "ampere",         [0,0,0,1,0,0,0],  1),
    ("K",    "kelvin",         [0,0,0,0,1,0,0],  1),
    ("mol",  "mole",           [0,0,0,0,0,1,0],  1),
    ("cd",   "candela",        [0,0,0,0,0,0,1],  1),
    # Derived
    ("J",    "joule",          [2,1,-2,0,0,0,0], 0),
    ("N",    "newton",         [1,1,-2,0,0,0,0], 0),
    ("W",    "watt",           [2,1,-3,0,0,0,0], 0),
    ("Pa",   "pascal",         [-1,1,-2,0,0,0,0],0),
    ("Hz",   "hertz",          [0,0,-1,0,0,0,0], 0),
    ("V",    "volt",           [2,1,-3,-1,0,0,0],0),
    ("C",    "coulomb",        [0,0,1,1,0,0,0],  0),
    ("F",    "farad",          [-2,-1,4,2,0,0,0],0),
    ("Ω",    "ohm",            [2,1,-3,-2,0,0,0],0),
    ("T",    "tesla",          [0,1,-2,-1,0,0,0],0),
    ("H",    "henry",          [2,1,-2,-2,0,0,0],0),
    ("Wb",   "weber",          [2,1,-2,-1,0,0,0],0),
    ("eV",   "electronvolt",   [2,1,-2,0,0,0,0], 0),
    ("rad",  "radian",         [0,0,0,0,0,0,0],  0),
    ("sr",   "steradian",      [0,0,0,0,0,0,0],  0),
    ("J/K",  "joule per kelvin",[2,1,-2,0,-1,0,0],0),
    ("J/mol","joule per mole", [2,1,-2,0,0,-1,0],0),
    ("m/s",  "metre per second",[1,0,-1,0,0,0,0],0),
    ("m/s2", "metre per second squared",[1,0,-2,0,0,0,0],0),
    ("kg/m3","kilogram per cubic metre",[-3,1,0,0,0,0,0],0),
    ("m2/s", "metre squared per second",[2,0,-1,0,0,0,0],0),
    ("Pa.s", "pascal second",  [-1,1,-1,0,0,0,0],0),
    ("dimless","dimensionless",[0,0,0,0,0,0,0],  0),
    ("J/kg", "joule per kilogram",[2,0,-2,0,0,0,0],0),
]

# Concepts — (id, name, symbol, domain_id, unit_id, dimension, description, aliases)
CONCEPTS = [
    # ── Kinematics ────────────────────────────────────────────────────────
    ("C001","displacement",         "s",    "kinematics",    "m",    [1,0,0,0,0,0,0],
     "Change in position",                              ["position_change","delta_s"]),
    ("C002","velocity",             "v",    "kinematics",    "m/s",  [1,0,-1,0,0,0,0],
     "Rate of change of displacement",                 ["speed"]),
    ("C003","acceleration",         "a",    "kinematics",    "m/s2", [1,0,-2,0,0,0,0],
     "Rate of change of velocity",                     []),
    ("C004","time",                 "t",    "kinematics",    "s",    [0,0,1,0,0,0,0],
     "Duration",                                       []),
    ("C005","angular_velocity",     "ω",    "rotation",      "Hz",   [0,0,-1,0,0,0,0],
     "Rate of change of angle",                        ["omega"]),
    ("C006","angular_acceleration", "α",    "rotation",      "Hz",   [0,0,-2,0,0,0,0],
     "Rate of change of angular velocity",             ["alpha"]),
    ("C007","angle",                "θ",    "rotation",      "rad",  [0,0,0,0,0,0,0],
     "Angular displacement",                           ["theta"]),

    # ── Dynamics ──────────────────────────────────────────────────────────
    ("C010","mass",                 "m",    "dynamics",      "kg",   [0,1,0,0,0,0,0],
     "Amount of matter",                               ["inertial_mass"]),
    ("C011","force",                "F",    "dynamics",      "N",    [1,1,-2,0,0,0,0],
     "Push or pull on an object",                      []),
    ("C012","weight",               "W",    "dynamics",      "N",    [1,1,-2,0,0,0,0],
     "Gravitational force on a mass",                  []),
    ("C013","momentum",             "p",    "dynamics",      "kg/m3","" ,
     "Mass in motion",                                 []),
    ("C014","torque",               "τ",    "rotation",      "N",    [2,1,-2,0,0,0,0],
     "Rotational force",                               ["tau","moment_of_force"]),
    ("C015","moment_of_inertia",    "I",    "rotation",      "kg",   [2,1,0,0,0,0,0],
     "Rotational analogue of mass",                    []),
    ("C016","angular_momentum",     "L",    "rotation",      "kg",   [2,1,-1,0,0,0,0],
     "Rotational analogue of momentum",                []),
    ("C017","friction_force",       "f",    "dynamics",      "N",    [1,1,-2,0,0,0,0],
     "Resistive contact force",                        []),

    # ── Energy ────────────────────────────────────────────────────────────
    ("C020","kinetic_energy",       "KE",   "energy_domain", "J",    [2,1,-2,0,0,0,0],
     "Energy of motion: ½mv²",                         ["KE","translational_ke"]),
    ("C021","potential_energy",     "PE",   "energy_domain", "J",    [2,1,-2,0,0,0,0],
     "Stored energy due to position or configuration", ["PE"]),
    ("C022","gravitational_pe",     "Ug",   "gravitation",   "J",    [2,1,-2,0,0,0,0],
     "Gravitational potential energy: mgh",            ["Ug"]),
    ("C023","spring_pe",            "Us",   "oscillations",  "J",    [2,1,-2,0,0,0,0],
     "Elastic potential energy: ½kx²",                 ["elastic_pe"]),
    ("C024","rotational_ke",        "Kr",   "rotation",      "J",    [2,1,-2,0,0,0,0],
     "Rotational kinetic energy: ½Iω²",                []),
    ("C025","work",                 "W",    "energy_domain", "J",    [2,1,-2,0,0,0,0],
     "Energy transferred by a force over a distance",  []),
    ("C026","power",                "P",    "energy_domain", "W",    [2,1,-3,0,0,0,0],
     "Rate of energy transfer",                        []),
    ("C027","mechanical_energy",    "E",    "energy_domain", "J",    [2,1,-2,0,0,0,0],
     "Sum of kinetic and potential energy",            []),

    # ── Gravitation ───────────────────────────────────────────────────────
    ("C030","gravitational_mass",   "M",    "gravitation",   "kg",   [0,1,0,0,0,0,0],
     "Mass as source of gravitational field",          ["source_mass"]),
    ("C031","gravitational_force",  "Fg",   "gravitation",   "N",    [1,1,-2,0,0,0,0],
     "Attractive force between masses",                []),
    ("C032","gravitational_field",  "g",    "gravitation",   "m/s2", [1,0,-2,0,0,0,0],
     "Gravitational field strength",                   ["g","grav_acceleration"]),
    ("C033","orbital_velocity",     "v_o",  "gravitation",   "m/s",  [1,0,-1,0,0,0,0],
     "Velocity for circular orbit",                    []),
    ("C034","escape_velocity",      "v_e",  "gravitation",   "m/s",  [1,0,-1,0,0,0,0],
     "Minimum velocity to escape gravitational field", []),

    # ── Oscillations ──────────────────────────────────────────────────────
    ("C040","period",               "T",    "oscillations",  "s",    [0,0,1,0,0,0,0],
     "Time for one complete oscillation",              []),
    ("C041","frequency",            "f",    "oscillations",  "Hz",   [0,0,-1,0,0,0,0],
     "Oscillations per second",                        []),
    ("C042","angular_frequency",    "ω",    "oscillations",  "Hz",   [0,0,-1,0,0,0,0],
     "Angular rate of oscillation: 2πf",               []),
    ("C043","spring_constant",      "k",    "oscillations",  "N",    [0,1,-2,0,0,0,0],
     "Stiffness of a spring: F = kx",                  ["stiffness"]),
    ("C044","amplitude",            "A",    "oscillations",  "m",    [1,0,0,0,0,0,0],
     "Maximum displacement from equilibrium",          []),

    # ── Fluids ────────────────────────────────────────────────────────────
    ("C050","density",              "ρ",    "fluids",        "kg/m3",[-3,1,0,0,0,0,0],
     "Mass per unit volume",                           ["rho"]),
    ("C051","pressure",             "P",    "fluids",        "Pa",   [-1,1,-2,0,0,0,0],
     "Force per unit area",                            []),
    ("C052","dynamic_viscosity",    "η",    "fluids",        "Pa.s", [-1,1,-1,0,0,0,0],
     "Fluid resistance to shear: F/A = η(dv/dy)",      ["eta","absolute_viscosity"]),
    ("C053","kinematic_viscosity",  "ν",    "fluids",        "m2/s", [2,0,-1,0,0,0,0],
     "Dynamic viscosity / density: ν = η/ρ",           ["nu"]),
    ("C054","volume_flow_rate",     "Q",    "fluids",        "m2/s", [3,0,-1,0,0,0,0],
     "Volume of fluid passing a point per second",     []),
    ("C055","reynolds_number",      "Re",   "fluids",        "dimless",[0,0,0,0,0,0,0],
     "Ratio of inertial to viscous forces: ρvD/η",    []),
    ("C056","mach_number",          "Ma",   "fluids",        "dimless",[0,0,0,0,0,0,0],
     "Ratio of flow speed to speed of sound: v/c",    []),
    ("C057","buoyancy_force",       "B",    "fluids",        "N",    [1,1,-2,0,0,0,0],
     "Upward force on submerged object: ρgV",          ["buoyant_force"]),

    # ── Thermodynamics ────────────────────────────────────────────────────
    ("C060","temperature",          "T",    "thermodynamics","K",    [0,0,0,0,1,0,0],
     "Measure of thermal energy per degree of freedom",[]),
    ("C061","thermal_energy",       "Q",    "thermodynamics","J",    [2,1,-2,0,0,0,0],
     "Heat transferred between systems",               ["heat","Q"]),
    ("C062","internal_energy",      "U",    "thermodynamics","J",    [2,1,-2,0,0,0,0],
     "Total microscopic energy of a system",           []),
    ("C063","entropy",              "S",    "thermodynamics","J/K",  [2,1,-2,0,-1,0,0],
     "Measure of disorder / unavailable energy",       []),
    ("C064","specific_heat",        "c",    "thermodynamics","J/kg", [2,0,-2,0,-1,0,0],
     "Heat required to raise 1kg by 1K",               ["specific_heat_capacity"]),
    ("C065","latent_heat",          "L",    "thermodynamics","J/kg", [2,0,-2,0,0,0,0],
     "Heat for phase change at constant temperature",  []),
    ("C066","thermal_efficiency",   "η",    "thermodynamics","dimless",[0,0,0,0,0,0,0],
     "Ratio of useful work output to heat input",      ["carnot_efficiency"]),
    ("C067","reaction_enthalpy",    "ΔH",   "thermochem",    "J/mol",[2,1,-2,0,0,-1,0],
     "Enthalpy change of reaction at standard conditions",["heat_of_reaction","delta_H"]),

    # ── Waves ─────────────────────────────────────────────────────────────
    ("C070","wavelength",           "λ",    "waves",         "m",    [1,0,0,0,0,0,0],
     "Distance between successive wave crests",        ["lambda"]),
    ("C071","wave_speed",           "v",    "waves",         "m/s",  [1,0,-1,0,0,0,0],
     "Speed of wave propagation",                      []),
    ("C072","wave_intensity",       "I",    "waves",         "W",    [0,1,-3,0,0,0,0],
     "Power per unit area",                            []),
    ("C073","sound_level",          "L",    "waves",         "dimless",[0,0,0,0,0,0,0],
     "Logarithmic measure of sound intensity: 10log(I/I₀)",["decibels","dB"]),
    ("C074","refractive_index",     "n",    "optics",        "dimless",[0,0,0,0,0,0,0],
     "Ratio of speed of light in vacuum to medium: c/v",["index_of_refraction"]),

    # ── Electromagnetism ──────────────────────────────────────────────────
    ("C080","electric_charge",      "q",    "electrostatics","C",    [0,0,1,1,0,0,0],
     "Fundamental property of matter",                 []),
    ("C081","electric_field",       "E",    "electrostatics","V",    [1,1,-3,-1,0,0,0],
     "Force per unit charge",                          []),
    ("C082","electric_potential",   "V",    "electrostatics","V",    [2,1,-3,-1,0,0,0],
     "Potential energy per unit charge",               ["voltage"]),
    ("C083","capacitance",          "C",    "circuits",      "F",    [-2,-1,4,2,0,0,0],
     "Charge stored per unit voltage: Q/V",            []),
    ("C084","electric_current",     "I",    "circuits",      "A",    [0,0,0,1,0,0,0],
     "Rate of charge flow",                            ["current"]),
    ("C085","resistance",           "R",    "circuits",      "Ω",    [2,1,-3,-2,0,0,0],
     "Opposition to current flow: V/I",                []),
    ("C086","electric_power",       "P_e",  "circuits",      "W",    [2,1,-3,0,0,0,0],
     "Rate of electrical energy dissipation: VI",      []),
    ("C087","magnetic_field",       "B",    "magnetism",     "T",    [0,1,-2,-1,0,0,0],
     "Magnetic flux density",                          []),
    ("C088","magnetic_flux",        "Φ",    "magnetism",     "Wb",   [2,1,-2,-1,0,0,0],
     "Magnetic field integrated over area",            ["Phi_B"]),
    ("C089","inductance",           "L",    "magnetism",     "H",    [2,1,-2,-2,0,0,0],
     "EMF induced per unit rate of current change",   []),
    ("C090","emf",                  "ε",    "magnetism",     "V",    [2,1,-3,-1,0,0,0],
     "Electromotive force — work per unit charge",     ["electromotive_force"]),

    # ── Modern Physics ────────────────────────────────────────────────────
    ("C100","rest_energy",          "E₀",   "relativity",    "J",    [2,1,-2,0,0,0,0],
     "Mass-energy equivalence: E=mc²",                 ["rest_mass_energy"]),
    ("C101","relativistic_energy",  "E",    "relativity",    "J",    [2,1,-2,0,0,0,0],
     "Total relativistic energy: γmc²",                []),
    ("C102","lorentz_factor",       "γ",    "relativity",    "dimless",[0,0,0,0,0,0,0],
     "γ = 1/√(1-v²/c²)",                              ["gamma","lorentz_gamma"]),
    ("C103","photon_energy",        "E_ph", "quantum",       "J",    [2,1,-2,0,0,0,0],
     "Energy of a photon: E=hf",                       []),
    ("C104","photon_momentum",      "p_ph", "quantum",       "kg",   [1,1,-1,0,0,0,0],
     "Momentum of a photon: p=h/λ",                   []),
    ("C105","de_broglie_wavelength","λ_dB", "quantum",       "m",    [1,0,0,0,0,0,0],
     "Matter wave wavelength: λ=h/p",                  []),
    ("C106","binding_energy",       "E_b",  "nuclear",       "J",    [2,1,-2,0,0,0,0],
     "Energy needed to disassemble a nucleus",         []),
    ("C107","half_life",            "t½",   "nuclear",       "s",    [0,0,1,0,0,0,0],
     "Time for half of radioactive sample to decay",  []),
    ("C108","hawking_temperature",  "T_H",  "gravitation",   "K",    [0,0,0,0,1,0,0],
     "T = ℏc³/(8πGMk_B) — temperature of Hawking radiation",
     ["black_hole_temperature"]),

    # ── Chemistry ─────────────────────────────────────────────────────────
    ("C120","activation_energy",    "Ea",   "chem_kinetics", "J/mol",[2,1,-2,0,0,-1,0],
     "Energy barrier for a chemical reaction",         ["arrhenius_energy"]),
    ("C121","reaction_rate",        "k",    "chem_kinetics", "Hz",   [0,0,-1,0,0,0,0],
     "First-order rate constant",                      ["rate_constant"]),
    ("C122","molar_concentration",  "c",    "chemistry",     "mol",  [-3,0,0,0,0,1,0],
     "Amount of substance per unit volume",            ["concentration"]),
    ("C123","gibbs_energy",         "G",    "thermochem",    "J/mol",[2,1,-2,0,0,-1,0],
     "ΔG = ΔH - TΔS — free energy of reaction",       ["free_energy","delta_G"]),

    # ── Biology / Genomics ────────────────────────────────────────────────
    ("C140","base_count",           "n",    "genomics",      "dimless",[0,0,0,0,0,0,0],
     "Number of nucleotide bases in a DNA sequence",  []),
    ("C141","melting_temperature",  "Tm",   "genomics",      "K",    [0,0,0,0,1,0,0],
     "Temperature at which 50% of DNA duplex is denatured",["dna_tm"]),
    ("C142","gc_content",           "%GC",  "genomics",      "dimless",[0,0,0,0,0,0,0],
     "Fraction of bases that are G or C",             ["gc_fraction"]),
]

# Physical constants
CONSTANTS = [
    ("CONST_c",   "speed of light",            "c",   2.99792458e8,  "m/s",   [1,0,-1,0,0,0,0], 1, "SI 2019"),
    ("CONST_G",   "gravitational constant",    "G",   6.67430e-11,   "m/s2",  [3,-1,-2,0,0,0,0], 0, "CODATA 2018"),
    ("CONST_h",   "Planck constant",           "h",   6.62607015e-34,"J",     [2,1,-1,0,0,0,0],  1, "SI 2019"),
    ("CONST_hbar","reduced Planck constant",   "ℏ",   1.054571817e-34,"J",    [2,1,-1,0,0,0,0],  1, "SI 2019"),
    ("CONST_kB",  "Boltzmann constant",        "k_B", 1.380649e-23,  "J/K",   [2,1,-2,0,-1,0,0], 1, "SI 2019"),
    ("CONST_NA",  "Avogadro constant",         "Nₐ",  6.02214076e23, "mol",   [0,0,0,0,0,-1,0],  1, "SI 2019"),
    ("CONST_R",   "gas constant",              "R",   8.314462618,   "J/K",   [2,1,-2,0,-1,-1,0],1, "SI 2019"),
    ("CONST_e",   "elementary charge",         "e",   1.602176634e-19,"C",    [0,0,1,1,0,0,0],   1, "SI 2019"),
    ("CONST_me",  "electron mass",             "mₑ",  9.1093837015e-31,"kg",  [0,1,0,0,0,0,0],   0, "CODATA 2018"),
    ("CONST_mp",  "proton mass",               "mₚ",  1.67262192369e-27,"kg", [0,1,0,0,0,0,0],   0, "CODATA 2018"),
    ("CONST_eps0","permittivity of free space","ε₀",  8.8541878128e-12,"F",   [-3,-1,4,2,0,0,0],  1, "SI 2019"),
    ("CONST_mu0", "permeability of free space","μ₀",  1.25663706212e-6,"H",   [1,1,-2,-2,0,0,0],  0, "CODATA 2018"),
    ("CONST_sigma","Stefan-Boltzmann constant","σ",   5.670374419e-8, "W",    [0,1,-3,0,-4,0,0],  1, "CODATA 2018"),
    ("CONST_g",   "standard gravity",          "g",   9.80665,        "m/s2", [1,0,-2,0,0,0,0],   1, "SI"),
]

# Equations — (id, name, display_name, formula, domain, output_concept, confidence_max, computable, notes, source)
EQUATIONS = [
    # ── Kinematics ────────────────────────────────────────────────────────
    ("EQ001","velocity_def",        "Velocity",              "v = Δs/Δt",          "kinematics",    "C002", 1.0, 1, "Definition",          "physics.info"),
    ("EQ002","acceleration_def",    "Acceleration",          "a = Δv/Δt",          "kinematics",    "C003", 1.0, 1, "Definition",          "physics.info"),
    ("EQ003","eom_velocity",        "Equation of Motion v",  "v = v₀ + at",        "kinematics",    "C002", 1.0, 1, "Kinematic equation",  "physics.info"),
    ("EQ004","eom_displacement",    "Equation of Motion s",  "s = v₀t + ½at²",    "kinematics",    "C001", 1.0, 1, "Kinematic equation",  "physics.info"),

    # ── Dynamics ──────────────────────────────────────────────────────────
    ("EQ010","newton_2nd",          "Newton's 2nd Law",      "F = ma",             "dynamics",      "C011", 1.0, 1, "Fundamental law",     "physics.info"),
    ("EQ011","weight",              "Weight",                "W = mg",             "dynamics",      "C012", 1.0, 1, "Gravitational force on mass", "physics.info"),
    ("EQ012","momentum_def",        "Momentum",              "p = mv",             "dynamics",      "C013", 1.0, 1, "Definition",          "physics.info"),
    ("EQ013","torque_def",          "Torque",                "τ = rF sinθ",        "rotation",      "C014", 1.0, 1, "Definition",          "physics.info"),
    ("EQ014","newton_2nd_rotation", "Newton 2nd (Rotation)", "τ = Iα",            "rotation",      "C014", 1.0, 1, "Rotational analogue", "physics.info"),

    # ── Energy ────────────────────────────────────────────────────────────
    ("EQ020","kinetic_energy",      "Kinetic Energy",        "KE = ½mv²",          "energy_domain", "C020", 1.0, 1, "Definition",          "physics.info"),
    ("EQ021","gravitational_pe",    "Gravitational PE",      "Ug = mgh",           "gravitation",   "C022", 1.0, 1, "Near-surface approx", "physics.info"),
    ("EQ022","spring_pe",           "Spring PE",             "Us = ½kx²",          "oscillations",  "C023", 1.0, 1, "Hooke's law energy",  "physics.info"),
    ("EQ023","rotational_ke",       "Rotational KE",         "Kr = ½Iω²",         "rotation",      "C024", 1.0, 1, "Rotational analogue", "physics.info"),
    ("EQ024","work_def",            "Work",                  "W = F·Δs cosθ",      "energy_domain", "C025", 1.0, 1, "Definition",          "physics.info"),
    ("EQ025","power_def",           "Power",                 "P = ΔW/Δt",          "energy_domain", "C026", 1.0, 1, "Definition",          "physics.info"),
    ("EQ026","power_velocity",      "Power-Velocity",        "P = Fv cosθ",        "energy_domain", "C026", 1.0, 1, "Derived",             "physics.info"),

    # ── Gravitation ───────────────────────────────────────────────────────
    ("EQ030","universal_grav",      "Universal Gravitation", "Fg = Gm₁m₂/r²",     "gravitation",   "C031", 1.0, 1, "Newton's law",        "physics.info"),
    ("EQ031","orbital_speed",       "Orbital Speed",         "v = √(GM/r)",        "gravitation",   "C033", 1.0, 1, "Circular orbit",      "physics.info"),
    ("EQ032","escape_speed",        "Escape Speed",          "v = √(2GM/r)",       "gravitation",   "C034", 1.0, 1, "Derived",             "physics.info"),

    # ── Oscillations ──────────────────────────────────────────────────────
    ("EQ040","hookes_law",          "Hooke's Law",           "F = -kx",            "oscillations",  "C011", 1.0, 1, "Linear restoring force","physics.info"),
    ("EQ041","sho_period",          "SHO Period",            "T = 2π√(m/k)",       "oscillations",  "C040", 1.0, 1, "Simple harmonic oscillator","physics.info"),
    ("EQ042","pendulum_period",     "Pendulum Period",       "T = 2π√(ℓ/g)",      "oscillations",  "C040", 1.0, 1, "Simple pendulum",     "physics.info"),
    ("EQ043","angular_frequency",   "Angular Frequency",     "ω = 2πf",            "oscillations",  "C042", 1.0, 1, "Definition",          "physics.info"),

    # ── Fluids ────────────────────────────────────────────────────────────
    ("EQ050","density_def",         "Density",               "ρ = m/V",            "fluids",        "C050", 1.0, 1, "Definition",          "physics.info"),
    ("EQ051","pressure_def",        "Pressure",              "P = F/A",            "fluids",        "C051", 1.0, 1, "Definition",          "physics.info"),
    ("EQ052","buoyancy",            "Buoyancy",              "B = ρgV",            "fluids",        "C057", 1.0, 1, "Archimedes' principle","physics.info"),
    ("EQ053","bernoulli",           "Bernoulli's Equation",  "P + ρgy + ½ρv² = const","fluids",    "C051", 1.0, 1, "Energy conservation in fluids","physics.info"),
    ("EQ054","kinematic_viscosity", "Kinematic Viscosity",   "ν = η/ρ",            "fluids",        "C053", 1.0, 1, "Definition",          "physics.info"),
    ("EQ055","reynolds_number",     "Reynolds Number",       "Re = ρvD/η",         "fluids",        "C055", 1.0, 1, "Flow regime classifier","physics.info"),

    # ── Thermodynamics ────────────────────────────────────────────────────
    ("EQ060","sensible_heat",       "Sensible Heat",         "Q = mcΔT",           "thermodynamics","C061", 1.0, 1, "Heat without phase change","physics.info"),
    ("EQ061","latent_heat",         "Latent Heat",           "Q = mL",             "thermodynamics","C061", 1.0, 1, "Heat for phase change","physics.info"),
    ("EQ062","ideal_gas",           "Ideal Gas Law",         "PV = nRT",           "thermodynamics","C051", 1.0, 1, "Ideal gas approximation","physics.info"),
    ("EQ063","first_law_thermo",    "First Law of Thermo",   "ΔU = Q + W",         "thermodynamics","C062", 1.0, 1, "Energy conservation",  "physics.info"),
    ("EQ064","entropy_def",         "Entropy",               "ΔS = ΔQ/T",          "thermodynamics","C063", 1.0, 1, "Clausius definition",  "physics.info"),
    ("EQ065","carnot_efficiency",   "Carnot Efficiency",     "η = 1 - Tc/Th",      "thermodynamics","C066", 1.0, 1, "Maximum efficiency",   "physics.info"),
    ("EQ066","stefan_boltzmann",    "Stefan-Boltzmann Law",  "P = εσA(T⁴-T₀⁴)",   "heat_transfer", "C026", 1.0, 1, "Radiation heat transfer","physics.info"),
    ("EQ067","molecular_ke",        "Molecular KE",          "⟨KE⟩ = 3/2 kT",      "thermodynamics","C020", 1.0, 1, "Kinetic theory",       "physics.info"),

    # ── Waves ─────────────────────────────────────────────────────────────
    ("EQ070","wave_speed",          "Wave Speed",            "v = fλ",             "waves",         "C071", 1.0, 1, "Definition",           "physics.info"),
    ("EQ071","frequency_period",    "Frequency-Period",      "f = 1/T",            "waves",         "C041", 1.0, 1, "Definition",           "physics.info"),
    ("EQ072","snell_law",           "Snell's Law",           "n₁sinθ₁ = n₂sinθ₂", "optics",        "C074", 1.0, 1, "Refraction law",       "physics.info"),
    ("EQ073","sound_level",         "Sound Level",           "L = 10log(I/I₀)",    "waves",         "C073", 1.0, 1, "Logarithmic intensity", "physics.info"),

    # ── Electromagnetism ──────────────────────────────────────────────────
    ("EQ080","coulombs_law",        "Coulomb's Law",         "F = kq₁q₂/r²",      "electrostatics","C011", 1.0, 1, "Electrostatic force",  "physics.info"),
    ("EQ081","ohms_law",            "Ohm's Law",             "V = IR",             "circuits",      "C082", 1.0, 1, "Circuit law",          "physics.info"),
    ("EQ082","electric_power",      "Electric Power",        "P = VI = I²R = V²/R","circuits",     "C086", 1.0, 1, "Power dissipation",    "physics.info"),
    ("EQ083","capacitance_def",     "Capacitance",           "C = Q/V",            "circuits",      "C083", 1.0, 1, "Definition",           "physics.info"),
    ("EQ084","faradays_law",        "Faraday's Law",         "ε = -dΦB/dt",        "magnetism",     "C090", 1.0, 1, "Electromagnetic induction","physics.info"),
    ("EQ085","magnetic_force",      "Magnetic Force",        "FB = qvB sinθ",      "magnetism",     "C011", 1.0, 1, "Lorentz force",        "physics.info"),

    # ── Modern Physics ────────────────────────────────────────────────────
    ("EQ100","mass_energy",         "Mass-Energy",           "E = mc²",            "relativity",    "C100", 1.0, 1, "Rest mass equivalence","physics.info"),
    ("EQ101","relativistic_energy", "Relativistic Energy",   "E = γmc²",           "relativity",    "C101", 1.0, 1, "Total relativistic energy","physics.info"),
    ("EQ102","energy_momentum_rel", "Energy-Momentum",       "E² = p²c² + m²c⁴",  "relativity",    "C101", 1.0, 1, "Relativistic relation","physics.info"),
    ("EQ103","photon_energy",       "Photon Energy",         "E = hf",             "quantum",       "C103", 1.0, 1, "Planck relation",      "physics.info"),
    ("EQ104","de_broglie",          "De Broglie Wavelength", "λ = h/p",            "quantum",       "C105", 1.0, 1, "Matter wave relation", "physics.info"),
    ("EQ105","hawking_temperature", "Hawking Temperature",   "T = ℏc³/(8πGMkB)",  "gravitation",   "C108", 1.0, 1, "Hawking radiation",    "hawking1974"),
    ("EQ106","uncertainty_principle","Uncertainty Principle","ΔpΔx ≥ ℏ/2",        "quantum",       "C104", 1.0, 1, "Heisenberg",           "physics.info"),

    # ── Chemistry ─────────────────────────────────────────────────────────
    ("EQ120","arrhenius",           "Arrhenius Equation",    "k = A·exp(-Ea/RT)",  "chem_kinetics", "C121", 1.0, 1, "Rate constant vs temperature","arrhenius1889"),
    ("EQ121","gibbs_energy",        "Gibbs Free Energy",     "ΔG = ΔH - TΔS",     "thermochem",    "C123", 1.0, 1, "Spontaneity criterion","physics.info"),

    # ── Genomics ──────────────────────────────────────────────────────────
    ("EQ140","dna_melting_temp",    "DNA Melting Temperature","Tm = 81.5 + 16.6log[Na⁺] + 0.41(%GC) - 675/n",
     "genomics", "C141", 0.90, 1, "Wallace rule — approximate, salt dependent","wallace1979"),
]

# equation_components — (equation_id, concept_id, role, symbol)
# role: "input" = required variable, "output" = what it calculates,
#       "constant" = physical constant used, "parameter" = optional/contextual
EQ_COMPONENTS = [
    # EQ001 velocity = Δs/Δt
    ("EQ001","C001","input",   "Δs"),
    ("EQ001","C004","input",   "Δt"),
    ("EQ001","C002","output",  "v"),
    # EQ002 acceleration = Δv/Δt
    ("EQ002","C002","input",   "Δv"),
    ("EQ002","C004","input",   "Δt"),
    ("EQ002","C003","output",  "a"),
    # EQ003 v = v₀ + at
    ("EQ003","C002","input",   "v₀"),
    ("EQ003","C003","input",   "a"),
    ("EQ003","C004","input",   "t"),
    ("EQ003","C002","output",  "v"),
    # EQ004 s = v₀t + ½at²
    ("EQ004","C002","input",   "v₀"),
    ("EQ004","C003","input",   "a"),
    ("EQ004","C004","input",   "t"),
    ("EQ004","C001","output",  "s"),
    # EQ010 F = ma
    ("EQ010","C010","input",   "m"),
    ("EQ010","C003","input",   "a"),
    ("EQ010","C011","output",  "F"),
    # EQ011 W = mg
    ("EQ011","C010","input",   "m"),
    ("EQ011","C012","output",  "W"),
    # EQ012 p = mv
    ("EQ012","C010","input",   "m"),
    ("EQ012","C002","input",   "v"),
    ("EQ012","C013","output",  "p"),
    # EQ013 τ = rF sinθ
    ("EQ013","C001","input",   "r"),
    ("EQ013","C011","input",   "F"),
    ("EQ013","C014","output",  "τ"),
    # EQ014 τ = Iα
    ("EQ014","C015","input",   "I"),
    ("EQ014","C006","input",   "α"),
    ("EQ014","C014","output",  "τ"),
    # EQ020 KE = ½mv²
    ("EQ020","C010","input",   "m"),
    ("EQ020","C002","input",   "v"),
    ("EQ020","C020","output",  "KE"),
    # EQ021 Ug = mgh
    ("EQ021","C010","input",   "m"),
    ("EQ021","C001","input",   "h"),
    ("EQ021","C022","output",  "Ug"),
    # EQ022 Us = ½kx²
    ("EQ022","C043","input",   "k"),
    ("EQ022","C001","input",   "x"),
    ("EQ022","C023","output",  "Us"),
    # EQ023 Kr = ½Iω²
    ("EQ023","C015","input",   "I"),
    ("EQ023","C005","input",   "ω"),
    ("EQ023","C024","output",  "Kr"),
    # EQ024 W = F·Δs cosθ
    ("EQ024","C011","input",   "F"),
    ("EQ024","C001","input",   "Δs"),
    ("EQ024","C025","output",  "W"),
    # EQ025 P = ΔW/Δt
    ("EQ025","C025","input",   "ΔW"),
    ("EQ025","C004","input",   "Δt"),
    ("EQ025","C026","output",  "P"),
    # EQ026 P = Fv cosθ
    ("EQ026","C011","input",   "F"),
    ("EQ026","C002","input",   "v"),
    ("EQ026","C026","output",  "P"),
    # EQ030 Fg = Gm₁m₂/r²
    ("EQ030","C030","input",   "m₁"),
    ("EQ030","C010","input",   "m₂"),
    ("EQ030","C001","input",   "r"),
    ("EQ030","C031","output",  "Fg"),
    # EQ031 orbital speed
    ("EQ031","C030","input",   "M"),
    ("EQ031","C001","input",   "r"),
    ("EQ031","C033","output",  "v"),
    # EQ032 escape speed
    ("EQ032","C030","input",   "M"),
    ("EQ032","C001","input",   "r"),
    ("EQ032","C034","output",  "v"),
    # EQ040 F = -kx
    ("EQ040","C043","input",   "k"),
    ("EQ040","C001","input",   "x"),
    ("EQ040","C011","output",  "F"),
    # EQ041 T = 2π√(m/k)
    ("EQ041","C010","input",   "m"),
    ("EQ041","C043","input",   "k"),
    ("EQ041","C040","output",  "T"),
    # EQ042 T = 2π√(ℓ/g)
    ("EQ042","C001","input",   "ℓ"),
    ("EQ042","C032","input",   "g"),
    ("EQ042","C040","output",  "T"),
    # EQ043 ω = 2πf
    ("EQ043","C041","input",   "f"),
    ("EQ043","C042","output",  "ω"),
    # EQ050 ρ = m/V
    ("EQ050","C010","input",   "m"),
    ("EQ050","C050","output",  "ρ"),
    # EQ051 P = F/A
    ("EQ051","C011","input",   "F"),
    ("EQ051","C051","output",  "P"),
    # EQ052 B = ρgV
    ("EQ052","C050","input",   "ρ"),
    ("EQ052","C057","output",  "B"),
    # EQ053 Bernoulli
    ("EQ053","C051","input",   "P"),
    ("EQ053","C050","input",   "ρ"),
    ("EQ053","C002","input",   "v"),
    ("EQ053","C001","input",   "y"),
    ("EQ053","C051","output",  "P"),
    # EQ054 ν = η/ρ
    ("EQ054","C052","input",   "η"),
    ("EQ054","C050","input",   "ρ"),
    ("EQ054","C053","output",  "ν"),
    # EQ055 Re = ρvD/η
    ("EQ055","C050","input",   "ρ"),
    ("EQ055","C002","input",   "v"),
    ("EQ055","C052","input",   "η"),
    ("EQ055","C055","output",  "Re"),
    # EQ060 Q = mcΔT
    ("EQ060","C010","input",   "m"),
    ("EQ060","C064","input",   "c"),
    ("EQ060","C060","input",   "ΔT"),
    ("EQ060","C061","output",  "Q"),
    # EQ061 Q = mL
    ("EQ061","C010","input",   "m"),
    ("EQ061","C065","input",   "L"),
    ("EQ061","C061","output",  "Q"),
    # EQ062 PV = nRT
    ("EQ062","C051","input",   "P"),
    ("EQ062","C060","input",   "T"),
    ("EQ062","C051","output",  "P"),
    # EQ063 ΔU = Q + W
    ("EQ063","C061","input",   "Q"),
    ("EQ063","C025","input",   "W"),
    ("EQ063","C062","output",  "ΔU"),
    # EQ064 ΔS = ΔQ/T
    ("EQ064","C061","input",   "ΔQ"),
    ("EQ064","C060","input",   "T"),
    ("EQ064","C063","output",  "ΔS"),
    # EQ065 η = 1 - Tc/Th
    ("EQ065","C060","input",   "Tc"),
    ("EQ065","C060","input",   "Th"),
    ("EQ065","C066","output",  "η"),
    # EQ066 P = εσAT⁴
    ("EQ066","C060","input",   "T"),
    ("EQ066","C026","output",  "P"),
    # EQ067 ⟨KE⟩ = 3/2 kT
    ("EQ067","C060","input",   "T"),
    ("EQ067","C020","output",  "KE"),
    # EQ070 v = fλ
    ("EQ070","C041","input",   "f"),
    ("EQ070","C070","input",   "λ"),
    ("EQ070","C071","output",  "v"),
    # EQ071 f = 1/T
    ("EQ071","C040","input",   "T"),
    ("EQ071","C041","output",  "f"),
    # EQ072 Snell's law
    ("EQ072","C074","input",   "n₁"),
    ("EQ072","C074","input",   "n₂"),
    ("EQ072","C074","output",  "n"),
    # EQ080 Coulomb's law
    ("EQ080","C080","input",   "q₁"),
    ("EQ080","C080","input",   "q₂"),
    ("EQ080","C001","input",   "r"),
    ("EQ080","C011","output",  "F"),
    # EQ081 V = IR
    ("EQ081","C084","input",   "I"),
    ("EQ081","C085","input",   "R"),
    ("EQ081","C082","output",  "V"),
    # EQ082 P = VI
    ("EQ082","C082","input",   "V"),
    ("EQ082","C084","input",   "I"),
    ("EQ082","C086","output",  "P"),
    # EQ083 C = Q/V
    ("EQ083","C080","input",   "Q"),
    ("EQ083","C082","input",   "V"),
    ("EQ083","C083","output",  "C"),
    # EQ084 ε = -dΦB/dt
    ("EQ084","C088","input",   "ΦB"),
    ("EQ084","C004","input",   "t"),
    ("EQ084","C090","output",  "ε"),
    # EQ085 FB = qvB sinθ
    ("EQ085","C080","input",   "q"),
    ("EQ085","C002","input",   "v"),
    ("EQ085","C087","input",   "B"),
    ("EQ085","C011","output",  "F"),
    # EQ100 E = mc²
    ("EQ100","C010","input",   "m"),
    ("EQ100","C100","output",  "E₀"),
    # EQ101 E = γmc²
    ("EQ101","C102","input",   "γ"),
    ("EQ101","C010","input",   "m"),
    ("EQ101","C101","output",  "E"),
    # EQ102 E² = p²c² + m²c⁴
    ("EQ102","C013","input",   "p"),
    ("EQ102","C010","input",   "m"),
    ("EQ102","C101","output",  "E"),
    # EQ103 E = hf
    ("EQ103","C041","input",   "f"),
    ("EQ103","C103","output",  "E_ph"),
    # EQ104 λ = h/p
    ("EQ104","C013","input",   "p"),
    ("EQ104","C105","output",  "λ"),
    # EQ105 Hawking temperature
    ("EQ105","C030","input",   "M"),
    ("EQ105","C108","output",  "T_H"),
    # EQ106 Uncertainty principle
    ("EQ106","C013","input",   "p"),
    ("EQ106","C001","input",   "x"),
    # EQ120 Arrhenius k = A·exp(-Ea/RT)
    ("EQ120","C120","input",   "Ea"),
    ("EQ120","C060","input",   "T"),
    ("EQ120","C121","output",  "k"),
    # EQ121 ΔG = ΔH - TΔS
    ("EQ121","C067","input",   "ΔH"),
    ("EQ121","C060","input",   "T"),
    ("EQ121","C063","input",   "ΔS"),
    ("EQ121","C123","output",  "ΔG"),
    # EQ140 DNA Tm
    ("EQ140","C142","input",   "%GC"),
    ("EQ140","C140","input",   "n"),
    ("EQ140","C141","output",  "Tm"),
]

# ── Build ──────────────────────────────────────────────────────────────────

def build():
    conn = sqlite3.connect(DB)
    cur  = conn.cursor()
    cur.executescript(SCHEMA)

    # Domains
    cur.executemany(
        "INSERT OR REPLACE INTO domains(id,name,parent_id) VALUES(?,?,?)",
        [(d[0],d[1],d[2]) for d in DOMAINS]
    )

    # Units
    cur.executemany(
        "INSERT OR REPLACE INTO units(id,name,dimension,si_base) VALUES(?,?,?,?)",
        [(u[0],u[1],json.dumps(u[2]),u[3]) for u in UNITS]
    )

    # Concepts (fix momentum unit placeholder)
    for c in CONCEPTS:
        cid,name,sym,dom,unit,dim,desc,aliases = c
        unit = unit if unit and unit != "" else None
        cur.execute(
            "INSERT OR REPLACE INTO concepts"
            "(id,name,symbol,domain_id,unit_id,dimension,description,aliases) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cid,name,sym,dom,unit,json.dumps(dim),desc,json.dumps(aliases))
        )

    # Constants
    cur.executemany(
        "INSERT OR REPLACE INTO constants(id,name,symbol,value,unit_id,dimension,exact,source) "
        "VALUES(?,?,?,?,?,?,?,?)",
        [(c[0],c[1],c[2],c[3],c[4],json.dumps(c[5]),c[6],c[7]) for c in CONSTANTS]
    )

    # Equations
    cur.executemany(
        "INSERT OR REPLACE INTO equations"
        "(id,name,display_name,formula,domain_id,output_concept,confidence_max,computable,notes,source) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        EQUATIONS
    )

    # Components
    cur.executemany(
        "INSERT INTO equation_components(equation_id,concept_id,role,symbol) "
        "VALUES(?,?,?,?)",
        EQ_COMPONENTS
    )

    conn.commit()

    # Summary
    print("=== ConceptGraph DB built ===")
    for table in ["domains","units","concepts","constants","equations","equation_components"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:25s}: {n:4d} rows")

    # Quick connectivity check — concepts appearing in most equations
    print("\nTop 10 hub concepts (most equation appearances):")
    rows = cur.execute("""
        SELECT c.name, COUNT(*) as n
        FROM equation_components ec
        JOIN concepts c ON ec.concept_id = c.id
        GROUP BY ec.concept_id
        ORDER BY n DESC
        LIMIT 10
    """).fetchall()
    for name, n in rows:
        print(f"  {name:30s}: {n} equations")

    conn.close()
    print(f"\nWritten to {DB}")

if __name__ == "__main__":
    build()

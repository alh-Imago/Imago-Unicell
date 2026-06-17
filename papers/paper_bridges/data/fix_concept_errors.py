"""
fix_concept_errors.py
Fixes 6 confirmed concept misassignment errors found during paper audit.

Errors found:
  EQ340 beer_lambert:  path length l -> C001 (displacement) WRONG
                       absorbance A  -> C073 (sound_level)  WRONG
  EQ322 faraday_electrolysis: molar mass M -> C010 (mass) WRONG (M != m)
  EQ320 nernst_equation: electrode potential E° -> C090 (emf/magnetism) WRONG
  EQ460 hydrogen_levels: quantum number n -> C041 (frequency) WRONG
  EQ465 rydberg: quantum numbers n1,n2 -> C001 (displacement) WRONG
  EQ433 magnetic_moment: area A -> C001 (displacement) WRONG
  EQ408 sound_intensity: area A -> C001 (displacement) WRONG

Fix: add 5 new concepts, reassign the bad component rows.
New concepts start at C542.
"""

import sqlite3

DB = "concept_graph.db"

NEW_CONCEPTS = [
    # (id, name, symbol, domain_id, unit_id, dimension, description, aliases, computable)
    ("C542", "path_length",         "l",   "chemistry",   "m",
     "[1,0,0,0,0,0,0]",
     "Optical path length through a sample (Beer-Lambert law)",
     "optical path length,sample length,l",1),

    ("C543", "absorbance",          "A",   "chemistry",   "dimless",
     "[0,0,0,0,0,0,0]",
     "Optical absorbance — log10(I0/I) — dimensionless (Beer-Lambert law)",
     "optical absorbance,Beer-Lambert A",1),

    ("C544", "molar_mass",          "M",   "chemistry",   "kg",
     "[0,1,0,0,0,-1,0]",
     "Molar mass — mass per mole of substance (kg/mol)",
     "molecular weight,M,molar mass",0),

    ("C545", "electrode_potential", "E°",  "chemistry",   "V",
     "[2,1,-3,-1,0,0,0]",
     "Standard electrode (reduction) potential vs SHE",
     "standard electrode potential,reduction potential,E0,E°",0),

    ("C546", "quantum_number",      "n",   "quantum",     "dimless",
     "[0,0,0,0,0,0,0]",
     "Principal quantum number — integer labelling atomic energy levels",
     "principal quantum number,n,quantum number",0),

    ("C547", "area",                "A",   "mechanics",   "m",
     "[2,0,0,0,0,0,0]",
     "Cross-sectional or surface area (m²)",
     "cross-sectional area,surface area,A",1),
]

# Component row edits: (component_row_id, new_concept_id, new_symbol)
# component_row_id from the audit query above
COMPONENT_FIXES = [
    # EQ340 beer_lambert A = εcl
    (460, "C542", "l",  "path length through sample"),      # was C001 displacement
    (461, "C543", "A",  "optical absorbance"),              # was C073 sound_level

    # EQ322 faraday_electrolysis m = MIt/nF
    # row 444: M (molar mass input) -> C544
    # row 447: m (deposited mass output) -> keep C010, CORRECT
    (444, "C544", "M",  "molar mass of deposited element"), # was C010 mass

    # EQ320 nernst_equation E = E° - (RT/nF)lnQ
    (437, "C545", "E°", "standard electrode potential"),    # was C090 emf/magnetism

    # EQ460 hydrogen_levels En = -13.6eV/n²
    (1217,"C546", "n",  "principal quantum number"),        # was C041 frequency

    # EQ465 rydberg 1/λ = R∞(1/n1²-1/n2²)
    # Only one row returned (n1); n2 may share same component row - check
    (1226,"C546", "n1", "lower principal quantum number"),  # was C001 displacement

    # EQ433 magnetic_moment m = IA
    (1177,"C547", "A",  "loop area"),                       # was C001 displacement

    # EQ408 sound_intensity I = P/A
    (1150,"C547", "A",  "area through which power passes"), # was C001 displacement
]


def run():
    db = sqlite3.connect(DB)
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")

    # 1. Insert new concepts
    inserted = 0
    for row in NEW_CONCEPTS:
        c.execute("""INSERT OR IGNORE INTO concepts
                     (id,name,symbol,domain_id,unit_id,dimension,description,aliases,computable)
                     VALUES (?,?,?,?,?,?,?,?,?)""", row)
        inserted += c.rowcount
    print(f"New concepts inserted: {inserted}")

    # 2. Check if EQ465 rydberg has a second quantum number row (n2)
    c.execute("SELECT id,concept_id,symbol FROM equation_components WHERE equation_id='EQ465'")
    rydberg_rows = c.fetchall()
    print(f"\nRydberg EQ465 components: {rydberg_rows}")

    # 3. Apply component fixes
    fixed = 0
    for row_id, new_concept, new_sym, new_notes in COMPONENT_FIXES:
        c.execute("""UPDATE equation_components
                     SET concept_id=?, symbol=?, notes=?
                     WHERE id=?""", (new_concept, new_sym, new_notes, row_id))
        if c.rowcount:
            print(f"  Fixed row {row_id}: -> {new_concept} ({new_sym})")
            fixed += c.rowcount
        else:
            print(f"  WARNING: row {row_id} not found")

    # 4. Fix any remaining rydberg n2 row pointing to C001
    c.execute("""SELECT id FROM equation_components
                 WHERE equation_id='EQ465' AND concept_id='C001'""")
    remaining = c.fetchall()
    for (rid,) in remaining:
        c.execute("""UPDATE equation_components
                     SET concept_id='C546', symbol='n2', notes='upper principal quantum number'
                     WHERE id=?""", (rid,))
        print(f"  Fixed rydberg n2 row {rid}: -> C546")
        fixed += c.rowcount

    print(f"\nTotal component rows fixed: {fixed}")

    # 5. Verify - show the corrected equations
    print("\nVerification:")
    for eq in ('EQ340','EQ322','EQ320','EQ460','EQ465','EQ433','EQ408'):
        c.execute("""SELECT ec.id, ec.concept_id, con.name, con.domain_id, ec.symbol, ec.role
                     FROM equation_components ec
                     JOIN concepts con ON con.id=ec.concept_id
                     WHERE ec.equation_id=?""", (eq,))
        rows = c.fetchall()
        domains = {r[3] for r in rows}
        print(f"\n  {eq} (domains: {domains}):")
        for r in rows:
            print(f"    {r}")

    db.commit()
    db.close()
    print("\nDone.")


if __name__ == "__main__":
    run()

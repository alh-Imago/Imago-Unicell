# Equation Sources for Concept Graph Seed Data
*Ready to process — do this when rested*

## Sources identified

1. **The Physics Hypertextbook** — https://physics.info/equations/
   - 5 domains: Mechanics, Thermal Physics, Waves & Optics, 
     Electricity & Magnetism, Modern Physics
   - ~80 equations, well structured, clean variable names
   - Includes: kinematics, dynamics, energy, thermodynamics,
     Maxwell's equations, relativity, quantum mechanics
   - Good first pass — secondary school to undergraduate level

2. **Wikipedia: Lists of physics equations**
   - https://en.wikipedia.org/wiki/Lists_of_physics_equations
   - Higher level — graduate and research physics
   - Good for filling gaps after #1

3. **Wikipedia: List of equations**  
   - https://en.wikipedia.org/wiki/List_of_equations
   - Cross-domain — chemistry, biology, economics, engineering
   - The cross-domain entries are the most valuable for the graph

## Processing plan (when ready)

For each equation extract:
- Concept name (canonical)
- Symbol
- Domain
- SI dimension vector [m,kg,s,A,K,mol,cd]
- Units
- Variables (what the equation connects)
- Mechanism name (the equation itself as a ConversionMechanism)
- confidence_max (1.0 for derived/fundamental, lower for empirical)
- Source citation

## Scale estimate

Physics alone: ~80 equations × ~3 variables each = ~240 concepts minimum
With chemistry, biology, economics: likely 500-1000 concepts
Mechanism count: roughly equal to equation count ~200-400 initially

This confirms the separate repo decision. Too large for UniCell repo.
Proposed: github.com/alh-Imago/Imago-ConceptGraph

## Note on E=mc²

Just from the physics.info source:
  E = γmc²  (relativistic energy)
  E = mc²   (rest mass energy)  
  E = hf    (photon energy)
  E = pc    (photon momentum-energy)
  E² = p²c² + m²c⁴  (energy-momentum relation)

Five equations, all containing E. Each connects energy to different
concepts. E is already a hub node visible from this one source alone.
Temperature, mass, frequency, momentum, speed of light all connect
through it. The density around energy in the graph will be very high.

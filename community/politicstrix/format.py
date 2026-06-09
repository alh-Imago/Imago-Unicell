"""
PoliticsTrix format definition — political actors as a formal domain.

This is a demonstration that the UniCell format system works for any
domain that can be symbolically described — not just physics and biology.

The key requirement: be clear and upfront about what you are claiming.
semantic_confidence declares how well-established each connection is.
A confidence of 0.5 is a model. A confidence of 1.0 is a discovery.
There is no hiding behind notation here.

See: docs/PAPER_DRAFT.md § Universal Symbolic Substrate
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatDefinition, FormatRegistry


class PoliticsTrix_Format(FormatDefinition):
    """
    Political actor format.

    8-bit actor codes, 4 per 32-bit cell word.
    Actor types, influence levels, and coalition structures
    are declared explicitly — not assumed.

    semantic_confidence for bridges to physical domains:
      → MathTrix pagerank:    0.6  (influence as graph diffusion — a model)
      → MathTrix laplacian:   0.5  (influence as diffusion — an analogy)
      → SI_Physics:           0.0  (no declared physical connection)

    You cannot bridge PoliticsTrix to SI_Physics without declaring
    what physical quantity political influence corresponds to.
    The system enforces this. It is not a bug.
    """
    name             = "Political_Actor"
    description      = "Political actors, influence, and coalition dynamics"
    domain           = "PoliticsTrix"
    bits_per_symbol  = 8
    symbols_per_word = 4
    cell_words       = 2    # actor_type cell + influence_value cell
    boundary_in      = "POL_PACK"
    boundary_out     = "POL_UNPACK"
    valid_tiles      = [
        "POL_INFLUENCE_CALC",   # compute actor influence score
        "POL_VOTE_MODEL",       # probability of voting for candidate
        "POL_COALITION_FORM",   # can these actors form a coalition?
        "POL_POLICY_MATCH",     # does policy match actor preferences?
        "POL_MEDIA_AMPLIFY",    # media amplification of message
        "POL_DIFFUSE",          # influence spreading through network
    ]
    symbol_lut = {
        # Actor types
        "VOTER":      1,
        "CANDIDATE":  2,
        "PARTY":      3,
        "POLICY":     4,
        "MEDIA":      5,
        "LOBBY":      6,
        "INSTITUTION":7,
        # Influence directions
        "LEFT":       16,
        "CENTRE":     17,
        "RIGHT":      18,
        "POPULIST":   19,
        # Coalition types
        "MAJORITY":   32,
        "MINORITY":   33,
        "COALITION":  34,
        "OPPOSITION": 35,
    }
    CONSTANTS = {
        "electoral_threshold": 0.05,   # 5% to enter parliament
        "majority_threshold":  0.50,   # >50% for majority
        "coalition_threshold": 0.33,   # minimum for meaningful coalition
        "media_amplification": 2.5,    # typical media reach multiplier
        "voter_turnout":       0.65,   # baseline turnout
        "term_length_years":   4,
    }
    produces = {
        "influence":     ["POL_INFLUENCE_CALC", "POL_MEDIA_AMPLIFY"],
        "vote_prob":     ["POL_VOTE_MODEL"],
        "coalition":     ["POL_COALITION_FORM"],
        "diffusion":     ["POL_DIFFUSE"],
    }
    consumes = {
        "influence":     ["POL_POLICY_MATCH", "POL_COALITION_FORM",
                          "POL_VOTE_MODEL", "POL_DIFFUSE"],
        "diffusion":     ["POL_DIFFUSE"],
    }
    constraints = {
        "symbol_range": (1, 127),
        "byte_aligned": True,
    }
    notes = (
        "Bridge to MathTrix pagerank: confidence 0.6 — influence as "
        "graph diffusion is a model, not discovered physics. "
        "Bridge to SI_Physics: confidence 0.0 — no declared physical "
        "connection. The system will correctly reject this bridge unless "
        "you declare what physical quantity political influence represents "
        "and add it to produces/consumes. "
        "This is not a limitation. It is the system being honest."
    )


FormatRegistry.get_default().register_class(PoliticsTrix_Format)

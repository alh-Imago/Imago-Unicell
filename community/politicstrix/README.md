# PoliticsTrix

Political actors, influence dynamics, and coalition structures as a
formal UniCell compute domain.

## What This Is

A demonstration that the UniCell format system works for any domain
that can be symbolically described — not just physics and biology.

Political systems have:
- A finite set of actor types (voters, candidates, parties, media...)
- Influence values that can be computed and compared
- Coalition structures that form according to declared rules
- Constants (electoral thresholds, turnout rates, term lengths)

These can all be declared in a format definition. The cells don't know
they're computing politics. They fire when their inputs arrive.

## The Critical Requirement

**Be clear and upfront about what you are actually claiming.**

The `semantic_confidence` field in every bridge contract is not optional.
It is your formal statement of how well-established the connection is:

- `0.6` — influence as graph diffusion (PageRank) is a **model**,
  not discovered physics. It may be useful. It is not a law.
- `0.5` — influence spreading like heat is an **analogy**. Interesting
  but not validated.
- `0.0` — no connection to SI_Physics. Political influence is not
  temperature. The system will correctly reject this bridge.

You cannot bridge PoliticsTrix to SI_Physics without declaring what
physical quantity political influence corresponds to. The validator
checks this against the format definitions. It is not a bug.

## Included Models

- `influence_diffusion.json` — PageRank-style influence propagation
  through a political network (bridge to MathTrix pagerank, conf=0.6)

## What You Can Build With This

- Election outcome models (vote probability diffusion)
- Coalition formation analysis
- Media amplification effects
- Policy adoption dynamics
- Influence network analysis

## What You Cannot Claim

- That political influence **is** temperature (no physical basis)
- That electoral outcomes follow thermodynamic laws (not declared)
- That any of these models are more than models (confidence < 0.8)

The system enforces honesty about the difference.

## Author

Imago UniCell Project — demonstration domain

## License

MIT

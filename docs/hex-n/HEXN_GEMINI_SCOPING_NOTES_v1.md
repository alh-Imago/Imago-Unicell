# Hex-N: ideas from a Gemini scoping chat, and where the build touches them (v1, 6 Nov 2026)

A record of a list of ideas, not a design. Source: Alan pasted a seven-step summary of a scoping chat he had with Gemini (6 Nov, 09:44) and said it is "a list of ideas more than anything", and that a lot of what has been built can be applied to this thought train. Claude has NOT seen the Gemini chat itself; the list below is the summary exactly as Alan gave it. The right-hand column is Claude's reading of the repository, tagged [file] (read in a file), [open] (no counterpart found or undecided). It is an interpretation to be corrected by Alan.

| # | The idea (as given) | Where the work touches it |
|---|---|---|
| 1 | A basic McCulloch-Pitts neuron: a rigid, blind logic gate. | The Hex-N cell sums its inputs and compares with a threshold (`HEXN_DESIGN.md` section 2) [file]. The work cells of the Kintex arrays are fixed-function word cores, closer to this "blind gate" than to a learning neuron [file]. |
| 2 | Modernised with backpropagation so it learns local associations. | Hex-N does not use backpropagation: training is keep-or-undo mutation search, and the counted detector learns by counting, with a local rule in layer 1 [file]. The neural judge (`rtl/hexn_neural_v1.v`, simulated only) learns online [file]. |
| 3 | Too localised, so a Global Map built on past experiences. | Layer 2 and 3 history stores (store v5 ran on the Tang; the memory tier ran on the Kintex card) [file]. The weight store with a cross-index to program slots is the base's own "saved experience" (simulation only) [file]. |
| 4 | A Predictive Engine using fuzzy matching to look ahead. | Layer 2 predicts the next event, layer 3 ranks possible next moments; recall from a partial cue exists as a concept model (22 Oct) [file]. Layer 3 is a Python model only [file]. |
| 5 | A Reward Vector comparing prediction with ground reality to self-correct. | Layer 2 gives a verdict (ok, contradiction, novel, start) and takes reward values into its store; layer 3 reward [file: `LAYER_INTERFACES_v4.md`]. A vector of several reward terms is not defined anywhere [open]. |
| 6 | Focus via Immediacy and Necessity to resolve conflicting goals. | Layer 4 sets goals and the choice engine steers the output (path 2 in the direction note) [file]. "Immediacy" and "Necessity" as named quantities have no counterpart in the files [open]. The batch judge picking a program is a simple form of resolving between options [file]. |
| 7 | A Priority Interrupt Stack to manage cognitive cycles without dying in a crisis. | Not built [open]. Points to check against UniCell's "no interrupts, steady timing" principle (stated in the UniCell README work): a stack of interrupts may need to be a flag-and-poll scheme instead. Nearest existing pieces: the priority work cell (PR) and stop-and-flag with the refusal `F` in the results RAM [file]. |

## Reading, for discussion
- Steps 1 to 3 are largely covered by what exists (detector, stores, weight store). Steps 4 and 5 exist as models and layer-2 hardware but not on the Kintex. Steps 6 and 7 are the least built.
- The auto picker (the judge selecting a program from the data) is the first working piece of step 6, and stop-and-flag is a first piece of step 7.
- No decision is recorded here. Next: Alan to say which steps matter first and whether the interrupt idea fits the no-interrupt principle.

## Alan's rulings on this list (6 Nov, 09:49)
- It is a forward list of ideas; the current v9 detector tests and the work built so far still stand and are not changed by it.
- Much of it is close to what already exists and can be applied almost directly; it will expand when the neural cell design is reached.
- The interrupt part of the focus system needs careful handling: Alan dislikes interrupts (consistent with UniCell's no-interrupt principle). Treat step 7 as a design to be reworked without true interrupts (flag and poll, or scheduled checks), not built as the idea is worded.

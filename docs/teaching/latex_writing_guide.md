# Writing a formula for UniCell: the LaTeX input and the reduction advisory

You can hand the compiler a formula the way you would write it in a maths book (LaTeX), and it gives you back a design made of cells, **after checking that the design gives the same answers as a plain Python evaluation of your formula**. If the check fails you get an error and no design. This page says how to write each kind of input, what the compiler will say no to, and how to write a formula so that it comes out small.

Every cell count below comes from a real run of `nano/latex_cli_v1.py` (12 October 2026). Counts are cells, not speeds: nothing here is a clock-rate claim. The designs were checked in the VM; the matrix, polynomial and division forms were also run as generated Verilog (flex family, and for some sub family) in earlier checks, listed in the ledger (`#1066` to `#1083`).

## 1. How to run it

```
python3 nano/latex_cli_v1.py "y = (a + b)^2 - 3c" --set a=2 --set b=3 --set c=4 -o poly.icm
```

Quote the formula. `--set` also runs the finished design on the values you give and prints the answer next to Python's. In code, the same thing is `compile_latex(...)` and, for matrices, `compile_matrix_latex(...)` in `nano/latex_frontend_v1.py`.

## 2. How to write each kind of input

**Numbers and names.** Whole numbers only. One letter is one variable (`x`). Two letters side by side are a **product**, as in maths: `xy` is x times y. For a longer name write `\mathrm{rate}`. Subscripts work: `x_1`, `x_{12}`. Greek letters work. The inputs of the design are the names in the formula, in the order they first appear; the CLI prints that order.

**Arithmetic.** `+  -  *  \cdot  \times`, unary minus, and writing things side by side (`2x`, `3(a+b)`). Brackets `( ) [ ] { }` and `\left( \right)`.

**Powers.** Whole numbers 0 to 64. LaTeX takes only one digit after `^` unless you use braces, so write `x^{23}`, not `x^23` (the compiler refuses the second, because in LaTeX it means x squared followed by a 3).

**Numbers wrap around.** Arithmetic is on 32-bit whole numbers that wrap, exactly like the cells: `2^31 + 2^31` is 0. There are no fractions.

**Division and remainder.** `a / b`, `a \div b`, `\frac{a}{b}` give the whole-number quotient (rounded down); `a \bmod b` gives the remainder. They work on **unsigned** words, so `-x / 2` is not minus half of x. Dividing by zero gives all ones, and the remainder by zero is the dividend. By default one division is **one cell** (the division core); `a / 7` and `a \bmod 7` each came out at 8 cells in all. A divisor that is a power of two is a shift or a mask and costs a cell or two. The old written-out form (about 23,000 cells for one division) is still available as `--division unrolled`. Speed against size of the division cell is `--div-steps K` (K quotient bits per clock). K changes how big the cell physically is, so it is chosen when the design is built, not changed afterwards.

**Sums and products over a range.** `\sum_{i=1}^{4} i x` and `\prod_{i=1}^{3} (x+i)`. The first and last values must be **whole numbers written out** (at most 64 terms); `\sum_{i=1}^{n}` is refused because a range that depends on a run-time value needs a loop, which is not built. The index `i` can stand alone, be a subscript (`a_i`) or be an exponent (`x^i`). The body is the multiplicative term that follows, so `\sum_{i=1}^{3} i x + 1` means `(1+2+3)x + 1`; put brackets round the body to include several terms.

**Dot products.** Write the sum with subscripts: `\sum_{i=1}^{3} a_i b_i`. The inputs are named `a_1, b_1, a_2, b_2, a_3, b_3`. A dot product of n terms is placed as a stored block (section 4) and is exactly `7n - 1` cells: 3 terms came out at 20.

**Matrices.** Give a **rule** for the entries and a **size**, counting rows and columns from 1:

```
python3 nano/latex_cli_v1.py "A_{ij} = i j" --matrix 3x3
```

This builds `y = A x`: the inputs are `x_1 ... x_n`, the results are `y_1 ... y_m`. The rule is an ordinary formula in the two index letters, so `i + j`, `i j`, `i^2 j^2`, division and remainder all work. The entries are worked out when the design is built and become constant cells, so **the rule may use only the two index letters**. The 3 by 3 above came out at 68 cells and gave 14, 28, 42 for x = 1, 2, 3, as Python does. Sizes are 1 to 16 rows and 2 to 16 columns.

- **Run-time matrix:** leave the rule off and every entry is an input: `"A_{ij}" --matrix 2x3` gives inputs `A_1_1 ... A_2_3` as well as `x_1 ... x_3` (44 cells). Use this when the matrix itself is the result of another design.
- **Chaining, `y = B (A x)`:** add `--then "B_{ij} = i j @ 2x2"` (repeatable). Each next matrix needs as many columns as the one before has rows. A 2 by 3 followed by a 2 by 2 came out at 73 cells.
- **Matrix times matrix:** done by streaming. The columns of the second matrix are fed one after another through one block of the first, so the hardware is one block, not one copy per column. For 16 by 16 that is about 2,000 cells against about 32,000 for a copy per column (worked out from the cell-count formula, not built).
- **Not built yet:** the looped small form (one block reused by feeding its results back in), matrix entries that depend on a run-time value, matrices written out number by number, and a matrix with a single column.

## 3. What it refuses, and what the refusal looks like

The compiler never guesses. It points at the character and says why:

| You wrote | What it says |
|---|---|
| `y = x^23` | write x^{23} with braces: in LaTeX x^23 means x^2 followed by 3 |
| `y = \sqrt{x}` | square roots are not supported (no fractions or irrational results; only whole numbers) |
| `y = a / b c` | a number or name straight after a division or remainder is ambiguous (is it multiplied before or after?): add brackets |
| `y = \sum_{i=1}^{n} i` | the last value of a sum or product must be a whole number written out (a run-time range needs a loop, which is not built) |
| `y = x^{-1}` | negative powers mean division, which is not supported |

Also refused: functions (sin, log), integrals, decimals, variable exponents, absolute value, comparisons, shifts, and anything it does not recognise.

## 4. The reduction advisory: write the smaller formula yourself

**The system does not reduce your formula for you.** It does only small clean-ups: constants are folded, `x + 0` and `x * 1` are removed, a one-variable polynomial is expanded and rebuilt as the cheaper of two shapes (below), and a pure dot product is placed as a stored block. Anything bigger, such as factoring, pulling a constant out of a sum, or noticing that two terms are the same, is up to whoever writes the formula. This follows Alan's reading: the user supplies the reduced formula, or a reduction step runs first, and that second route may be too much of an extension of the LaTeX input, so it is not built. The pairs below show how much a hand reduction gains.

The advice below is each time a measured pair. The only thing that changed between the two is how the formula is written.

**Pull constants and common factors out.**

| Written | Cells |
|---|---|
| `\sum_{i=1}^{8} i x` | 284 |
| `36 x` (the same value) | 8 |
| `a b + a c + a d + a e` | 89 |
| `a (b + c + d + e)` | 26 |

The reason is the cost of **reading the same input more than once**. Every extra read of an input needs a split, and the general placer pays for the wires with relay cells (a relay is a cell that only carries a value). A formula that uses one input many times is expensive, and the cost grows faster than the number of terms. Factor first.

**Polynomials: the compiler tries two shapes and keeps the smaller.** A polynomial in one variable is built as written ("direct") and as **Horner** (`((c3 x + c2) x + c1) x + c0`, one multiply-add stage per degree), and the one with fewer cells is kept. You can force one with `--polynomial horner` or `direct`. Measured: `3x^2 + 2x + 1` is 26 cells (44 direct); `x^7` is 38 (61 direct); but `(x+1)^3` is 23 direct and 32 by Horner, so direct is kept. A dense polynomial costs exactly 12 cells per degree plus 2. The choice is made on compiled cells, not on counting multiplies, because fewer multiplies did not always mean fewer cells (`x^7` needs more multiplies by Horner and still comes out smaller). Two ways of writing the same polynomial can land on the same size: `x^2 (x+1)^2` and `x^4 + 2x^3 + x^2` both came out at 32 cells.

**A sum is a chain, not a tree.** Adding n things one after another costs 6 cells per term; a balanced tree of adds, which looks better on paper, was far larger (8 terms: 101 cells against 44). The compiler writes ranges out as a chain, so you do not need to arrange this yourself. The cause of the tree being worse has not been found.

**Dot products and matrices go to a stored block.** The general placer routes a dot product badly: 2 to 9 terms cost 29, 53, 89, 137, 188, 260, 326, 413 cells, mostly relay cells. The stored multiply-accumulate block is written directly and is exactly `7n - 1` cells (8 terms: 55). A matrix times a vector is the same idea laid side by side, with `8n(m-1) + 7n - 1` cells for m rows and n columns (2 by 2: 29, 3 by 3: 68, 4 by 4: 123). So: write a dot product as a bare `\sum_{i=1}^{n} a_i b_i` and a matrix as a rule plus a size, and the compiler uses the block. Add a coefficient, repeat a variable or use a subtraction inside the dot product and it quietly falls back to the general placer and the larger design (`--blocks off` forces that on purpose).

**Check the count, then decide.** The CLI prints `compiled: N cells`. Rewriting a formula and running it again takes seconds, and the count is the measurement. A card limits how many cells fit, and the card-fit check refuses a design that is too big.

## 5. How far it goes, and what has and has not been checked

- **Checked:** every compile compares the design with Python on corner values (0, 1, the sign boundary, all ones) and random values, once on the generated operations and once in the VM. Division, polynomials, sums, products, dot products and matrices were also run as generated flex Verilog in iverilog; division, a dot product and a 1 by 3 matrix were run as sub Verilog.
- **Not checked:** the LaTeX designs on the older v4/v4c carrier cells; anything on a physical card; throughput when items are fed close together (the streaming helper uses a deliberately generous gap, a rule of thumb and not a measured limit); sizes of matrices beyond the small ones in RTL.
- **Not built:** loops (sums or matrix products over a run-time range), signed division, fractions and fixed point, comparisons and choices, shifts written in LaTeX.

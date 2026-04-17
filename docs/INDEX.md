# Imago UniCell — Documentation Index
## Claudette v1.1

| File | Contents |
|------|----------|
| `00_PRIMER.md` | Quick start, installation, worked examples, command reference |
| `01_Architecture_Overview.md` | Design philosophy, cell layout, key concepts, scaling |
| `02_Core_Architecture.md` | Cell register detail, tile library, compiler, command bus |
| `03_Security_Model.md` | 9-layer security model, mask primitive, conditional ponds |
| `04_OS_and_Runtime.md` | Claudette OS, Ponds, Ward, Shore, migration, VM images |
| `05_Hardware_and_Scaling.md` | MIDAS chip, BGA package, PCIe card, chipIgnite tape-out |
| `06_Testing_and_Validation.md` | Test suites, results, coverage by layer |
| `07_CLI_and_User_Guide.md` | Workbench commands, Ward monitoring, Cast/discovery |

## Key corrections vs earlier versions

- **Cell size**: 192-bit register file (32 gate_state + 64 input_address + 64 output_address + 32 data) plus 1-bit dedicated start flag hardware line. Not 161 bits.
- **Wired-OR**: Two NOT cells sharing an output address produce NAND (NOT(a) OR NOT(b) = NAND(a,b)). True NOR uses the GS_NOR internal topology flag within a single cell.
- **64-bit addressing (v1.1)**: Both address registers are natively 64-bit. Bridge cells carry full 64-bit destination addresses without Shore involvement. Shore V2 is a directory and fallback, not a routing component.
- **Test count**: 2,409 passing tests across 43 suites (updated from earlier 2,586 / 45 figures).

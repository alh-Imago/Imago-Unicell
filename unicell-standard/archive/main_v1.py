from dataclasses import dataclass
import sys

VAR_FALSE = 0
VAR_TRUE = 1
VAR_UNDEF = 2

def new_vars(n):
    return [VAR_UNDEF for i in range(n)]

VarIdx = (int, int)
def var_idx(var_name) -> VarIdx:
    match var_name[0]:
        case 'x':
            i = 0
        case 'y':
            i = 1
        case 'z':
            i = 2
    j = int(var_name[1:])
    return i, j

@dataclass
class Instruction:
    inputs: list
    operation: str
    outputs: list

    def parse(s):
        sp = s.split("=")
        lhs = sp[0].strip()
        rhs = sp[1].strip()
        outputs = [ var_idx(var.strip()) for var in lhs.split(",") ]
        i = rhs.index(' ')
        name = rhs[:i]
        inputs = [ var_idx(var.strip()) for var in rhs[i+1:].split(",") ]
        return Instruction(inputs, name, outputs)
        

@dataclass
class Block:
    num_inputs: int
    num_intermediates: int
    num_outputs: int
    instructions: list

    def parse(s):
        lines = list(s.split("\n"))
        name = lines[0][:-1]
        [nx, ny, nz] = list(map(int, lines[1].strip().split(", ")))
        instructions = [ Instruction.parse(l) for l in lines[2:] ]
        return name, Block(nx, ny, nz, instructions)

    def apply(self, inputs: list, operations) -> list:
        assert(len(inputs)==self.num_inputs)
        for i in inputs:
            assert(i==VAR_TRUE or i==VAR_FALSE)

        intermediates = new_vars(self.num_intermediates)
        outputs = new_vars(self.num_outputs)
        vars = [inputs, intermediates, outputs]

        for inst in self.instructions:
            match inst.operation:
                case "nor":
                    x0i, x0j = inst.inputs[0]
                    x1i, x1j = inst.inputs[1]
                    z0i, z0j = inst.outputs[0]
                    vars[z0i][z0j] = not (vars[x0i][x0j]==VAR_TRUE or vars[x1i][x1j]==VAR_TRUE)
                case str(op):
                    block = operations[op]
                    ins = [vars[i][j] for i, j in inst.inputs]
                    outs = block.apply(ins, operations)
                    for (i,j), o in zip(inst.outputs, outs):
                        vars[i][j] = o

        return vars[2]


# parsing block definitions
blocks = {}
with open("block_defs", "r") as f:
    block_defs = f.read()
    for block_str in block_defs.strip().split("\n\n"):
        name, b = Block.parse(block_str)
        blocks[name] = b

if len(sys.argv)<2:
    print("expected a block names as first argument")
else:
    name = sys.argv[1]
    if name not in blocks.keys():
        print(f"block name \"{name}\" is not defined in block_defs file")
    else:
        block = blocks[name]
        inputs = sys.argv[2:]
        if len(inputs)!=block.num_inputs:
            print(f"expected {block.num_inputs} inputs for an \"{name}\" block, but got {len(inputs)}")
        else:
            print(block.apply([int(i) for i in inputs], blocks))

```mermaid
flowchart TD
    SRC([\"📄 Source\"])

    SRC --> SPLIT{\"Input type?\"}

    SPLIT -->|\"Python function\"| PY
    SPLIT -->|\"LLVM IR (.ll)\"| LLVM

    subgraph PY[\"Python Compiler Path\"]
        direction TB
        AST[\"Python AST parse\"]
        OPS[\"Operation stream\\n(arithmetic, branch,\\nloop, select)\"]
        AST --> OPS
    end

    subgraph LLVM[\"LLVM Frontend Path\"]
        direction TB
        LP[\"llvm_frontend.py\\nparse .ll file\"]
        LF[\"LLVMFunction\\nparse tree\"]
        LM[\"llvm_ir_mapper.py\\nLLVM → tile ops\"]
        LP --> LF --> LM
    end

    OPS --> TILE
    LM --> TILE

    subgraph TILE[\"Tile Library Resolution\"]
        direction TB
        TL[\"Tile name lookup\\n(user tiles override core)\"]
        TN[\"40+ named tiles\\nINT32_ADD_CLA depth=58\\nFP32_MUL, INT32_NOT, ...)\"]
        TL --> TN
    end

    subgraph NB[\"NOR Builder\"]
        direction TB
        NOR1[\"Compose NOR primitives\"]
        DEPTH[\"Automatic depth tracking\\npad_to_depth (PASS cells)\\non shorter wired-OR paths\"]
        NOR1 --> DEPTH
    end

    TILE --> NB

    subgraph CM[\"Cell Map\"]
        direction TB
        CMR[\"Flat list of CellMapRecords\\naddress · gate_state\\ninput_address · output_address\"]
    end

    NB --> CM

    subgraph PI[\"ProgramImage\"]
        direction TB
        HDR[\"Header:\\nMODELS NEEDED\\nDEPTH · ENTRY POINT\"]
        CELLS[\"Cell records\"]
        ADDR[\"Global address map\"]
        HDR --- CELLS --- ADDR
    end

    CM --> PI

    subgraph LOAD[\"Load into Pond\"]
        direction TB
        CTRL[\"controller.py\\ncell map loader\"]
        PTT[\"PTT registers\\nabsolute addresses\"]
        START[\"Assert start flags\"]
        CTRL --> PTT --> START
    end

    PI --> LOAD

    subgraph RUN[\"Runtime Execution\"]
        direction LR
        DATA[\"Data arrives at\\ninput_address\"]
        FIRE[\"All armed cells\\nevaluate simultaneously\"]
        OUT[\"Result at\\noutput_address\\nafter N ticks (= depth)\"]
        DATA --> FIRE --> OUT
    end

    LOAD --> RUN

    NOTE[\"Pipeline depth is a\\nstructural property of the wiring.\\nKnown at compile time.\\nInvariant across runs.\"]
    RUN -.-> NOTE

    style SRC fill:#2E75B6,color:#fff
    style SPLIT fill:#D6DCE4
    style PY fill:#FFF2CC
    style LLVM fill:#FFF2CC
    style TILE fill:#FCE4D6
    style NB fill:#FCE4D6
    style CM fill:#E2F0D9
    style PI fill:#E2F0D9
    style LOAD fill:#DAE3F3
    style RUN fill:#DAE3F3
    style NOTE fill:#F2F2F2
```

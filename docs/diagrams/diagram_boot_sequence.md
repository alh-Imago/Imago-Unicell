```mermaid
flowchart TD
    PWR([\"⚡ Power-On\"])

    PWR --> S1

    subgraph S1[\"Step 1 — Generate Secrets\"]
        direction LR
        RNG[\"Hardware RNG\"]
        AT[\"Auth Token\\n12-bit\"]
        SK[\"Salt Key\\n64-bit\"]
        RNG --> AT
        RNG --> SK
    end

    S1 --> S2

    subgraph S2[\"Step 2 — Dead Cell Survey\"]
        direction LR
        SCAN[\"Scan full array\"]
        DMAP[\"Defect Map\\n(excluded addresses)\"]
        SCAN --> DMAP
    end

    S2 --> S3

    subgraph S3[\"Step 3 — Allocate Address Space\"]
        direction LR
        AMAP[\"Assign addresses\\naround dead cells\"]
        LIVE[\"Live address map\"]
        AMAP --> LIVE
    end

    S3 --> S4

    subgraph S4[\"Step 4 — Distribute Auth Token\"]
        direction LR
        DIST[\"CMD_RECONFIGURE\\nto every live cell\"]
        LOCK[\"Config registers\\nlocked (token embedded)\"]
        DIST --> LOCK
    end

    S4 --> S5

    subgraph S5[\"Step 5 — Load & Verify Tier 2\"]
        direction TB
        T2[\"COMPANION\\nShore V2\\nShoreKeeper\"]
        V2[\"ECC verify\\nauth-token check\"]
        T2 --> V2
    end

    S5 --> S6

    subgraph S6[\"Step 6 — Load & Verify Tier 3\"]
        direction TB
        T3[\"Core Ponds\\n(CompilerPond, tile library,\\ndevice bridges)\"]
        V3[\"ECC verify\\nauth-token check\"]
        T3 --> V3
    end

    S6 --> S7

    subgraph S7[\"Step 7 — Hand Off\"]
        direction LR
        SF[\"Assert start flags\"]
        RUN([\"🟢 System Running\"])
        SF --> RUN
    end

    AT -.->|\"distributed in Step 4\"| DIST
    SK -.->|\"HIDDEN Pond encryption\\nnever leaves BIOS chip\"| LOCK

    style PWR fill:#C00000,color:#fff
    style RUN fill:#375623,color:#fff
    style S1 fill:#FFF2CC
    style S2 fill:#FFF2CC
    style S3 fill:#FFF2CC
    style S4 fill:#FCE4D6
    style S5 fill:#E2F0D9
    style S6 fill:#E2F0D9
    style S7 fill:#DAE3F3
    style AT fill:#C00000,color:#fff
    style SK fill:#2E75B6,color:#fff
```

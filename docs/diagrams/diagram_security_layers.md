```mermaid
flowchart TB
    PRIM[\"🔑 One Primitive\\n(process_mask AND resource_mask) ≠ 0\\nFail → resource is ABSENT (not denied)\"]

    PRIM --> L1

    subgraph L1[\"Layer 1 — Hardware: Cell Auth Token\"]
        L1D[\"12-bit token in every CMD_RECONFIGURE\\nCell silently rejects wrong token\\nToken never leaves BIOS-Plus in plaintext\"]
    end

    subgraph L2[\"Layer 2 — Data: Salt Key Encryption\"]
        L2D[\"64-bit salt key for HIDDEN Pond encryption\\nNever distributed to cells\\nDestroyed on physical tamper\"]
    end

    subgraph L3[\"Layer 3 — Addressing: PTT Hidden Process Mask\"]
        L3D[\"32-bit process_mask in PTT — never readable by process\\nAll user addresses are PTT-relative offsets\\nUser cannot construct an absolute address outside its Pond\"]
    end

    subgraph L4[\"Layer 4 — Discovery: Mask-Filtered Cast/Ripple\"]
        L4D[\"(process_mask AND bridge.access_mask) ≠ 0\\nFailing Pond is ABSENT from results\\nQuerying process cannot learn protected resource exists\"]
    end

    subgraph L5[\"Layer 5 — Bridge Access: Bidirectional Mask Check\"]
        L5D[\"Inbound:  (process_mask AND access_mask) ≠ 0\\nOutbound: (process_mask AND access_mask) ≠ 0\\nFail → no log entry, no acknowledgement\"]
    end

    subgraph L6[\"Layer 6 — Identity Inheritance: Mask Lineage\"]
        L6D[\"User → Session → COMPANION → Pond → Bridge → FS Pond → File\\nMonotonically non-increasing: child mask ⊆ parent mask\\nNo escalation path exists\"]
    end

    subgraph L7[\"Layer 7 — Session Provisioning: Template Pond Cloning\"]
        L7D[\"COMPANION clones Template Pond matched to user mask\\nEach user: private namespace, separate address spaces\\nUser A's Ponds never visible to User B\"]
    end

    subgraph L8[\"Layer 8 — Filesystem: Mask-Shaped Views\"]
        L8D[\"Each FS path entry is a bridge\\nDirectory listing filtered by caller mask\\nFailing path is ABSENT from listing\"]
    end

    subgraph L9[\"Layer 9 — Card Boundary: ShoreKeeper Validation\"]
        L9D[\"Cross-card packets: token check + mask check + whitelist check\\nShoreKeeper is single authority at card boundary\\nRaw cell states never cross card boundary\"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7 --> L8 --> L9

    COST[\"Cost per check:\\nL1: 1 comparison per command\\nL3: 1 lookup per operation\\nL4: 1 AND per discovered item\\nL5: 1 AND per bridge transit\\nL6: 0 cost (mask copied at creation)\\nL9: 1 AND per hop\"]

    L9 --> COST

    style PRIM fill:#C00000,color:#fff
    style L1 fill:#FCE4D6
    style L2 fill:#FCE4D6
    style L3 fill:#FFF2CC
    style L4 fill:#FFF2CC
    style L5 fill:#E2F0D9
    style L6 fill:#E2F0D9
    style L7 fill:#DAE3F3
    style L8 fill:#DAE3F3
    style L9 fill:#D6DCE4
    style COST fill:#F2F2F2
```

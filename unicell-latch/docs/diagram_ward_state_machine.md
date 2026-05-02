```mermaid
stateDiagram-v2
    [*] --> IDLE : Pond created

    IDLE --> HEALTHY : first emission detected

    HEALTHY --> DEGRADED : emission rate drops\nbelow threshold
    HEALTHY --> SILENT : no data at bridge\n(device disconnect)

    DEGRADED --> HEALTHY : emission resumes\nnormally
    DEGRADED --> STALLED : silence for N ticks

    STALLED --> HEALTHY : emission resumes
    STALLED --> ISOLATED : COMPANION decision\n(restart failed)

    SILENT --> ISOLATED : COMPANION decision\n(log + ACTION_ISOLATE)
    SILENT --> HEALTHY : device reconnects

    ISOLATED --> IDLE : ACTION_MIGRATE\n(move to cooler / healthy card)
    ISOLATED --> ISOLATED : migrate failed\n(stay isolated)

    note right of HEALTHY
        Thermal sub-states (parallel):
        NOMINAL → THROTTLE → FREEZE
        sustained FREEZE → MIGRATE escalation
        to ShoreKeeper
    end note

    note right of COMPANION_RULES : Rule engine priority order:\n1. STALLED → RESTART → (fail) → ISOLATE\n2. ISOLATED → MIGRATE → (fail) → stay\n3. SILENT → log + ISOLATE\n4. THERMAL → MIGRATE
```

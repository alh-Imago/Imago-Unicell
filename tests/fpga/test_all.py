"""
test_all.py — Run all iCEBreaker silicon validation tests

Usage: python test_all.py COM4 0x2A5
"""
import subprocess, sys

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = sys.argv[2] if len(sys.argv) > 2 else '0x2A5'

suites = [
    ('test_sync_wait.py',   'Core two-arrival latch + chain'),
    ('test_new_opcodes.py', 'New opcodes: LATCH_IN, REARM, MEM_CALL, SET_LOGICAL'),
]

total_pass = 0
total_fail = 0

for script, desc in suites:
    print(f"\n{'='*60}")
    print(f"Suite: {desc}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, script, PORT, AUTH],
        capture_output=False
    )
    # Parse results from stdout would need piping — just run sequentially

print(f"\n{'='*60}")
print("All suites complete — check above for PASS/FAIL counts")
print(f"{'='*60}")

#!/bin/bash
# update_claudette_v1.2.sh
# Applies Claudette v1.2 changes to your local Imago-Unicell repo
# Run from inside the repo directory: bash update_claudette_v1.2.sh

set -e

echo "Claudette v1.2 — edge separation update"
echo "========================================"
echo ""

# Safety check — make sure we're in the right place
if [ ! -f "gate_states.py" ] || [ ! -f "unicell.py" ]; then
    echo "ERROR: Run this script from inside your Imago-Unicell repo directory"
    exit 1
fi

echo "Applying patch..."
patch -p1 < claudette_v1.2.patch

echo ""
echo "Running test suite to verify..."
echo ""

pass=0
fail=0
for t in test_array.py test_compiler.py test_gate_state_32.py test_vm_image.py \
          test_fp_tiles.py test_pond.py test_ward.py test_freeze.py \
          test_migration.py test_pond_ptt.py test_program_image.py; do
    result=$(timeout 60 python3 $t 2>&1 | grep "Results:")
    if echo "$result" | grep -q "0 failed"; then
        echo "  PASS $t"
        pass=$((pass + 1))
    else
        echo "  FAIL $t: $result"
        fail=$((fail + 1))
    fi
done

echo ""
echo "========================================"
echo "Verification: $pass passed, $fail failed"

if [ $fail -eq 0 ]; then
    echo "All good — Claudette v1.2 applied cleanly"
else
    echo "Some tests failed — check above for details"
fi

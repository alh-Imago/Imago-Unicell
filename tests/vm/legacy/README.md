# Legacy Tests

These tests were archived because they reference APIs removed in the v2.2 migration.

| File | Reason |
|------|--------|
| test_freeze.py | `UniCell.tick()` removed — use `array.tick()` |
| test_while.py | Same |
| test_migration.py | Tests internal `_stored_value` attribute (removed) |
| test_vm_image.py | Same |
| test_select.py | `output_address_alt` retired in format v2 |

If this functionality needs test coverage again, rewrite against the current API.

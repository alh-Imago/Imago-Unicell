// stdin: lines "c <cfgword hex>" or "w <a hex> <b hex>"; prints the result of every w line. Built by tests/vm/test_hexn_unit_model_v1.py.
#include <cstdio>
#include "../tools/esp32/hexn_save_restore/hexn_unit_model.h"
int main() { UnitModel m; char t; unsigned x, y; while (scanf(" %c", &t) == 1) { if (t == 'c') { scanf("%x", &x); m.config(x); } else { scanf("%x %x", &x, &y); printf("%u\n", m.word(x, y)); } } return 0; }

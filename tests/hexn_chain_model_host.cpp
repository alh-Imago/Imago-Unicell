// stdin: lines "c <unit> <cfgword hex>" or "w <a hex> <x hex>"; prints the chain result of every w line. Built by tests/vm/test_hexn_chain_model_v1.py.
#include <cstdio>
#include "../tools/esp32/hexn_save_restore/hexn_unit_model.h"
int main() { ChainModel m; char t; unsigned i, x, y; while (scanf(" %c", &t) == 1) { if (t == 'c') { scanf("%u %x", &i, &x); m.config(i, x); } else { scanf("%x %x", &x, &y); printf("%u\n", m.word(x, y)); } } return 0; }

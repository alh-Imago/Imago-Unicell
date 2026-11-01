// reads a record (hex words, one per line) from argv[1], argv[2] = want_kind, argv[3] = structure id; prints the hr_verify code. Built by tests/vm/test_hexn_record_v1.py.
#include <cstdio>
#include <cstdlib>
#include "../tools/esp32/hexn_save_restore/hexn_record.h"
int main(int argc, char** argv) { static uint32_t w[2048]; int n = 0; FILE* f = fopen(argv[1], "r"); unsigned v; while (fscanf(f, "%x", &v) == 1 && n < 2048) w[n++] = v; fclose(f);
  printf("%d\n", hr_verify(w, n, atoi(argv[2]), (uint32_t)strtoul(argv[3], 0, 0))); return 0; }

"""hexn_tier7_host_v2: host side of the Kintex tier command set with CLEAR (0x47). Extends tools/hexn_tier7_host_v1.py (untouched): everything of v1 plus cmd_clear() and Tier7Dev.clear(). CLEAR resets the tier (tables, presence counters, written bits, line buffer, the 17 counters, the sticky DDR3 error) without reloading the bitstream; the answer arrives when the tier is ready again, so the link must wait for it (about 1.6 ms at the Kintex sizes)."""
from hexn_tier7_host_v1 import *
import hexn_tier7_host_v1 as _v1
OP_CLEAR = 0x47
_v1.REPLY_LEN[OP_CLEAR] = 1
def cmd_clear(): return bytes([OP_CLEAR])
class Tier7Dev(_v1.Tier7Dev):
    def clear(self): return status(self._do(cmd_clear())[0])

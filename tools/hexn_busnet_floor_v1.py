"""hexn_busnet_floor_v1 (8 Nov 2026): does it matter that the hardware accumulator is bounded? The Python model lets the accumulator fall without limit (seen down to -86 in hexn_busnet_cost_sim_v1); the synthesised module saturates at -32. Here the model gets a floor (applied after every clock) and the pruning experiment of hexn_busnet_homeoprune_v1 is rerun (start threshold 5, 5 seeds, network trained with the floor in place).
Usage: python3 tools/hexn_busnet_floor_v1.py FLOOR     (e.g. -32, -8, -4)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_homeo_v1 as H, hexn_busnet_homeoprune_v1 as HP


class ClampNet(H.AdaptNet):
    def __init__(self, *a, floor=-32, **kw):
        super().__init__(*a, **kw); self.floor = floor

    def step(self, t, inputs=()):
        f = super().step(t, inputs)
        for g in self.acc:
            if self.acc[g] < self.floor: self.acc[g] = self.floor
        return f


if __name__ == "__main__":
    fl = int(sys.argv[1]); H.AdaptNet = lambda seed, **kw: ClampNet(seed, floor=fl, **kw); print("accumulator floor", fl); HP.main(5)

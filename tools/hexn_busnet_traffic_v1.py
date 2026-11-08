"""hexn_busnet_traffic_v1 (8 Nov 2026): lower the layer 1 target firing rate of the self-adjusting threshold to cut the traffic (and the dropped packets at the layer 2 buses). Alan 20:42. Wrapper of hexn_busnet_homeoprune_v1 with the layer 1 target rate set from the command line (earlier value 0.40). Simulation only.
Usage: python3 tools/hexn_busnet_traffic_v1.py L1_RATE START_TH"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_homeo_v1 as H, hexn_busnet_homeoprune_v1 as HP

if __name__ == "__main__":
    H.TARGET[1] = float(sys.argv[1]); print("layer 1 target rate %.2f" % H.TARGET[1]); HP.main(int(sys.argv[2]))

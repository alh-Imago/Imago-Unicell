"""hexn_busnet_traffic_thmax_v1 (8 Nov 2026): as hexn_busnet_traffic_v1 but also raises the threshold cap (TH_MAX) from 9 to a given value. Usage: python3 tools/hexn_busnet_traffic_thmax_v1.py L1_RATE TH_MAX"""
import sys; sys.path.insert(0,'tools')
import hexn_busnet_homeo_v1 as H, hexn_busnet_homeoprune_v1 as HP
H.TARGET[1]=float(sys.argv[1]); H.TH_MAX=int(sys.argv[2]); print("L1 rate",sys.argv[1],"TH_MAX",sys.argv[2]); HP.main(5)

"""hexn_busnet_traffic_queue_v1 (8 Nov 2026): the pruning experiment of hexn_busnet_homeoprune_v1 with a given queue depth per bus. Usage: python3 tools/hexn_busnet_traffic_queue_v1.py DEPTH"""
import sys; sys.path.insert(0,'tools')
import hexn_busnet_homeo_v1 as H, hexn_busnet_homeoprune_v1 as HP
orig=H.make; qd=int(sys.argv[1])
H.make=lambda seed,fb_inhib=0.5,**kw: orig(seed,fb_inhib,qdepth=qd,**kw)
print("queue depth",qd); HP.main(5)

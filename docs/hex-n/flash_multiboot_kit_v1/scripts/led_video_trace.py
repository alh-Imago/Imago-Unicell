"""Trace the LED brightness of a phone video and measure reload gaps.
usage: led_video_trace.py video.mp4 (writes vals.npy/ts.npy, prints gaps)"""
import cv2, numpy as np, sys
import sys
cap=cv2.VideoCapture(sys.argv[1])        # your slow-motion video, shrunk with ffmpeg if needed
vals=[];ts=[]
while True:
    ok,f=cap.read()
    if not ok: break
    roi=f[330:560,150:600]    # box around the LEDs: adjust to your framing
    g=cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY)
    vals.append(float((g>200).sum())); ts.append(cap.get(cv2.CAP_PROP_POS_MSEC))
np.save('vals.npy',np.array(vals)); np.save('ts.npy',np.array(ts))
print(len(vals), ts[:5], ts[-3:])

# ---- second step: turn the trace into reload gaps (all-LED-dark runs) ----
# usage: python3 led_video_trace.py   (edit the path above), then:
#   python3 -c "import led_video_trace_gaps" is not needed; the gap code is below.
import numpy as np
FPS = 120            # capture rate you filmed at (slow motion). Check it: it scales every result.
v = np.load('vals.npy'); dark = v < 150; runs = []; s = None
for i, dk in enumerate(dark):
    if dk and s is None: s = i
    if not dk and s is not None: runs.append((s, i - s)); s = None
print('all-LED-dark runs of 12 frames or more (taps), start frame: ms at %d fps' % FPS)
for st, ln in runs:
    if ln >= 12: print(st, ln, round(1000 * ln / FPS))

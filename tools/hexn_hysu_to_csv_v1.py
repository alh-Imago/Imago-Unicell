#!/usr/bin/env python3
"""hexn_hysu_to_csv_v1 (new file 1 Nov 2026): DLR HySU hyperspectral benchmark -> CSV files the front end can read (ONE file, hysu_pixels.csv.gz).
Cerra et al., DLR HySU, Remote Sens. 13, 2559 (2021); free to use with credit (see the dataset README).
Each ROW is one PIXEL of the 86 x 123 'full' HySpex VNIR image; the 135 band columns (named nm417 ... nm903) are its surface reflectance (the file stores integers scaled by 10,000; written here as the plain fraction).
The last column, 'material', names the pixel's target ROI (redMetal, bitumen, blueFabric, redFabric, greenFabric) or 'background' (everything else: edges, ground, anything not in an ROI). For the front end pick the task as a RULE, e.g. --rule "material == 'redMetal'" (or "material != 'background'" for any target).
AMBIGUOUS PIXELS LEFT OUT: 60 of the 10,578 pixels lie in the ROI of two or more materials (46 in two, 7 in three, 5 in four, 2 in all five), so a yes/no label for one material would be unclear; those pixels are dropped (10,518 rows are written).
HONEST SCOPE: the ROI pixels are the dataset's own target locations; every other pixel is called 'no', including pixels next to a target that may contain some of it (mixed pixels), so the 'no' class is not guaranteed pure. Position (row, column) is NOT written, so the front end cannot learn the answer from where a pixel is.
Usage: python3 tools/hexn_hysu_to_csv_v1.py DLR_HySU_folder OUT_DIR      (needs numpy and tifffile)"""
import sys, os, gzip
import numpy as np
MATERIALS = ["redMetal", "bitumen", "blueFabric", "redFabric", "greenFabric"]
def wavelengths(hdr_path):
    t = open(hdr_path, errors="replace").read(); i = t.index("wavelength = {"); j = t.index("}", i)
    w = [float(x) for x in t[i + len("wavelength = {"):j].replace("\n", " ").split(",") if x.strip()]; return w
def main(root, out):
    import tifffile
    hs = os.path.join(root, "HySpex"); img = tifffile.imread(os.path.join(hs, "full", "DLR_HySU_HS_full.tif")).astype(np.float64) / 10000.0
    H, W, B = img.shape; wl = wavelengths(os.path.join(hs, "full", "DLR_HySU_HS_full.hdr")); assert len(wl) == B, (len(wl), B)
    names = ["nm%d" % round(x * 1000) for x in wl]; X = img.reshape(H * W, B); os.makedirs(out, exist_ok=True); masks = {}
    for m in MATERIALS:
        r = np.fromfile(os.path.join(hs, "all_targets", "TargetsROIs", "ENVI", m), dtype=np.uint8); assert r.size == H * W, (m, r.size); masks[m] = r
    keep = np.where(sum(masks[m].astype(int) for m in MATERIALS) < 2)[0]                        # drop pixels in two or more material ROIs
    lab = np.array(["background"] * (H * W), dtype=object)
    for m in MATERIALS: lab[masks[m].astype(bool)] = m
    p = os.path.join(out, "hysu_pixels.csv.gz")
    with gzip.open(p, "wt", newline="") as f:
        f.write(",".join(names + ["material"]) + "\n")
        for i in keep: f.write(",".join("%.4f" % v for v in X[i]) + ",%s\n" % lab[i])
    u, c = np.unique(lab[keep], return_counts=True); print("%s: %d rows (pixels), %d band columns, material counts %s" % (os.path.basename(p), len(keep), B, dict(zip(u.tolist(), c.tolist()))))
if __name__ == "__main__":
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])

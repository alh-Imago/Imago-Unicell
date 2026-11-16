#!/usr/bin/env python3
"""make_telemetry.py - writes jobs_telemetry.json (24 jobs) and jobs_telemetry_small.json (5 jobs, for the simulation): a made-up telemetry workload that uses the
whole pipeline and leans on the board's limits.  Data is seeded random, so the files are always the same.
  crc32   standard CRC-32 of a data block (checked against zlib): bit-by-bit, so long blocks take a while; one block fills the window exactly (247 words)
  vgain   calibration: sample * gain / 256 by shift-and-add (no multiply on the core)
  vprefix running totals          vmax   peak value          vsum  total"""
import json, random, os
HERE = os.path.dirname(os.path.abspath(__file__))
PROGS = [{"name": "crc32",  "source": "programs/crc32.s",  "expect": "programs.examples:crc32_ref",  "out": 1},
         {"name": "vgain",  "source": "programs/vgain.s",  "expect": "programs.examples:vgain_ref",  "out": "same"},
         {"name": "vmax",   "source": "programs/vmax.s",   "expect": "programs.examples:vmax_ref",   "out": 1},
         {"name": "vprefix", "source": "programs/vprefix.s", "expect": "programs.examples:vprefix_ref", "out": "same"}]
def make(r, crc_sizes, gain_jobs, prefix_sizes, max_sizes, sum_sizes):
    jobs = []
    for n in crc_sizes: jobs.append({"kind": "crc32", "inputs": [r.randrange(1 << 32) for _ in range(n)]})
    for n, g in gain_jobs: jobs.append({"kind": "vgain", "arg": g, "inputs": [r.randrange(1 << 24) for _ in range(n)]})
    for n in prefix_sizes: jobs.append({"kind": "vprefix", "inputs": [r.randrange(1000) for _ in range(n)]})
    for n in max_sizes: jobs.append({"kind": "vmax", "inputs": [r.randrange(1 << 32) for _ in range(n)]})
    for n in sum_sizes: jobs.append({"kind": "vsum", "inputs": [r.randrange(1 << 32) for _ in range(n)]})
    r.shuffle(jobs); return {"programs": PROGS, "jobs": jobs}
if __name__ == '__main__':
    full = make(random.Random(2026), [6, 12, 24, 40, 60, 100, 200, 247], [(10, 64), (30, 128), (50, 200), (100, 255), (100, 1), (20, 0), (60, 77), (120, 192)], [16, 40, 80, 120], [30, 90], [50, 150])
    small = make(random.Random(7), [6, 20], [(12, 128), (30, 200)], [24], [], [])
    for name, d in (('jobs_telemetry.json', full), ('jobs_telemetry_small.json', small)):
        json.dump(d, open(os.path.join(HERE, name), 'w')); print(name, len(d['jobs']), 'jobs')

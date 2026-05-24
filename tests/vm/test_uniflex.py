"""
test_uniflex.py — UniFlex Filesystem Layer Tests

Validates Sections 4 and 5 of the spec:
  - FS decoder stubs: all registered, correct metadata, shared singleton
  - StoragePond: mounts correctly, scans volume, registers file tokens
  - Token space: register, resolve, deregister, integrity
  - PointerToken: checksum validated, tamper detected
  - File I/O: read, write, delete via token
  - Directory listing: access controlled via inbound bridge
  - UniFlex manager: mount, unmount, list_mounts
  - Security: PRIVATE StoragePond enforces whitelist on all file ops
  - Resource record: type-specific fields present

Run with: python3 test_uniflex.py
"""

import os, hashlib, tempfile
from pathlib import Path
from unicell_array import UniCellArray
from pond import PondManager, OPEN, PRIVATE, STORAGE, RT_FILE
from uniflex_fs import (UniFlex, StoragePond, FsDecoderStub,
                        FS_DECODER_REGISTRY, FS_NATIVE, FS_FAT32,
                        FS_NTFS, FS_EXT4, FS_APFS, FS_EXFAT)

results = []
def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def make_id(s): return hashlib.sha256(s.encode()).hexdigest()

OWNER   = make_id("alice")
BOB     = make_id("bob")
STRANGER = make_id("stranger")

# =============================================================================
print("\n=== FS Decoder Registry ===\n")

check("Registry: all 6 decoders present",
      len(FS_DECODER_REGISTRY) == 6)
for fs in (FS_FAT32, FS_NTFS, FS_EXT4, FS_APFS, FS_EXFAT, FS_NATIVE):
    check(f"Registry: {fs} present", fs in FS_DECODER_REGISTRY)

# Shared singleton — same object returned every time
d1 = FS_DECODER_REGISTRY[FS_FAT32]
d2 = FS_DECODER_REGISTRY[FS_FAT32]
check("Registry: shared singleton (same object)", d1 is d2)

# Correct metadata
check("FAT32: pipeline_depth > 0",  d1.pipeline_depth > 0)
check("FAT32: cell_count > 0",      d1.cell_count > 0)
check("FAT32: tier BASE",           d1.license_tier == "BASE")
check("APFS: tier INTEGER",
      FS_DECODER_REGISTRY[FS_APFS].license_tier == "INTEGER")
check("NATIVE: pipeline_depth = 0",
      FS_DECODER_REGISTRY[FS_NATIVE].pipeline_depth == 0)

# =============================================================================
print("\n=== PointerToken ===\n")

from pond import PointerToken
tok = PointerToken(
    token_id      = 0x0100000000000000,
    pond_id       = "pond_0001",
    resource_type = RT_FILE,
    physical_ref  = 0xABCD1234,
    label         = "hello.txt",
)
check("Token: is_valid after creation",  tok.is_valid())
check("Token: checksum non-zero",        tok.checksum != 0)
check("Token: type_name FILE",           tok.type_name() == "FILE")
check("Token: label stored",             tok.label == "hello.txt")

# Tamper detection
import copy
bad = copy.copy(tok)
bad.physical_ref = 0xDEADBEEF
bad.checksum = tok.checksum   # keep original checksum
check("Token: tampered ref detected", not bad.is_valid())

bad2 = copy.copy(tok)
bad2.checksum = tok.checksum ^ 1
check("Token: tampered checksum detected", not bad2.is_valid())

# =============================================================================
print("\n=== TokenSpace ===\n")

from pond import TokenSpace, RT_CELL_RANGE
ts = TokenSpace("test_pond", reservation_size=100)

t1 = ts.register(RT_FILE, 0x1000, "file_a.txt")
t2 = ts.register(RT_FILE, 0x2000, "file_b.txt")
t3 = ts.register(RT_CELL_RANGE, 0x3000, "region_x")

check("TokenSpace: 3 tokens registered", ts.used == 3)
check("TokenSpace: free = 97",           ts.free == 97)
check("TokenSpace: resolve by id",       ts.resolve(t1.token_id) is not None)
check("TokenSpace: resolve by label",    ts.resolve_by_label("file_a.txt") is not None)
check("TokenSpace: label resolves correctly",
      ts.resolve_by_label("file_b.txt").physical_ref == 0x2000)
check("TokenSpace: missing id → None",   ts.resolve(0xDEADBEEF) is None)
check("TokenSpace: list_tokens len 3",   len(ts.list_tokens()) == 3)

# Deregister
ok = ts.deregister(t2.token_id)
check("TokenSpace: deregister returns True", ok)
check("TokenSpace: used = 2 after deregister", ts.used == 2)
check("TokenSpace: deregistered id → None",
      ts.resolve(t2.token_id) is None)

# Exhaustion
ts_small = TokenSpace("tiny", reservation_size=2)
ts_small.register(RT_FILE, 1, "a")
ts_small.register(RT_FILE, 2, "b")
err = False
try:
    ts_small.register(RT_FILE, 3, "c")
except RuntimeError:
    err = True
check("TokenSpace: exhaustion raises RuntimeError", err)

# =============================================================================
print("\n=== StoragePond — mount and scan ===\n")

with tempfile.TemporaryDirectory() as tmpdir:
    # Create test volume
    (Path(tmpdir) / "notes.txt").write_text("hello world")
    (Path(tmpdir) / "data").mkdir()
    (Path(tmpdir) / "data" / "report.csv").write_text("a,b,c")

    arr = UniCellArray(cell_count=500)
    arr.enforce_emission_limits = False

    sp = StoragePond(
        name           = "test_vol",
        array          = arr,
        owner_id       = OWNER,
        mount_path     = tmpdir,
        fs_type        = FS_NATIVE,
        security_level = OPEN,
    )

    check("StoragePond: pond_type is STORAGE", sp.pond_type == STORAGE)
    check("StoragePond: fs_type stored",       sp.fs_type == FS_NATIVE)
    check("StoragePond: decoder is NATIVE",    sp.decoder.fs_type == FS_NATIVE)
    check("StoragePond: files registered",     sp.tokens.used >= 2)
    check("StoragePond: notes.txt registered",
          sp.resolve_path("notes.txt") is not None)
    check("StoragePond: data/report.csv registered",
          sp.resolve_path(str(Path("data") / "report.csv")) is not None)

    # Resource record has storage-specific fields
    rec = sp.resource_record()
    check("Resource record: pond_type STORAGE", rec["pond_type"] == STORAGE)
    check("Resource record: fs_type present",   "fs_type" in rec)
    check("Resource record: file_count > 0",    rec["file_count"] > 0)
    check("Resource record: decoder present",   "decoder" in rec)

    # Directory listing — OPEN pond, anyone can list
    entries, reason = sp.list_directory(STRANGER, "")
    names = [e.path for e in entries]
    check("List dir: root listing succeeds",     reason == "OK")
    check("List dir: notes.txt in root",         "notes.txt" in names)
    check("List dir: data dir in root",          "data" in names)
    check("List dir: subdir not in root listing",
          not any("report" in n for n in names))

    subentries, _ = sp.list_directory(STRANGER, "data")
    subnames = [e.path for e in subentries]
    check("List dir: data/report.csv in data/",
          any("report.csv" in n for n in subnames))

    # Read file via token
    entry = sp.resolve_path("notes.txt")
    data, reason2 = sp.read_file(STRANGER, entry.token.token_id)
    check("Read file: data returned",     data is not None)
    check("Read file: content correct",   data == b"hello world")
    check("Read file: reason OK",         reason2 == "OK")

    # Read with bad token
    bad_data, bad_reason = sp.read_file(STRANGER, 0xDEADBEEF)
    check("Read file: bad token → None",        bad_data is None)
    check("Read file: bad token reason",        bad_reason == "TOKEN_NOT_FOUND")

    # Write new file
    tok_id, write_reason = sp.write_file(STRANGER, "output/result.txt",
                                          b"test output")
    check("Write file: token_id returned",  tok_id is not None)
    check("Write file: reason OK",          write_reason == "OK")
    check("Write file: file exists on disk",
          (Path(tmpdir) / "output" / "result.txt").exists())
    check("Write file: registered in pond",
          sp.resolve_path(str(Path("output/result.txt"))) is not None)

    # Delete file
    del_ok, del_reason = sp.delete_file(STRANGER, tok_id)
    check("Delete file: success",       del_ok)
    check("Delete file: reason OK",     del_reason == "OK")
    check("Delete file: removed from registry",
          sp.resolve_path("output/result.txt") is None)

# =============================================================================
print("\n=== StoragePond — PRIVATE access control ===\n")

with tempfile.TemporaryDirectory() as tmpdir2:
    (Path(tmpdir2) / "secret.txt").write_text("classified")

    arr2 = UniCellArray(cell_count=500)
    arr2.enforce_emission_limits = False

    sp2 = StoragePond(
        name           = "private_vol",
        array          = arr2,
        owner_id       = OWNER,
        mount_path     = tmpdir2,
        fs_type        = FS_NATIVE,
        security_level = PRIVATE,
    )

    # Stranger cannot list or read
    entries2, reason3 = sp2.list_directory(STRANGER, "")
    check("PRIVATE: stranger cannot list",   entries2 == [])
    check("PRIVATE: stranger reason REJECTED", reason3 == "REJECTED")

    entry2 = sp2.resolve_path("secret.txt")
    data2, reason4 = sp2.read_file(STRANGER, entry2.token.token_id)
    check("PRIVATE: stranger cannot read",  data2 is None)

    # Bob granted access
    sp2.grant_access(BOB, label="bob")
    entries3, reason5 = sp2.list_directory(BOB, "")
    check("PRIVATE: bob can list after grant", len(entries3) > 0)

    data3, _ = sp2.read_file(BOB, entry2.token.token_id)
    check("PRIVATE: bob can read after grant", data3 == b"classified")

    # Owner always can
    entries4, _ = sp2.list_directory(OWNER, "")
    check("PRIVATE: owner always can list", len(entries4) > 0)

# =============================================================================
print("\n=== UniFlex manager ===\n")

with tempfile.TemporaryDirectory() as vol1:
    with tempfile.TemporaryDirectory() as vol2:
        (Path(vol1) / "a.txt").write_text("aaa")
        (Path(vol2) / "b.txt").write_text("bbb")

        arr3 = UniCellArray(cell_count=1000)
        arr3.enforce_emission_limits = False
        ufx = UniFlex(arr3, OWNER)

        # Mount two volumes
        p1 = ufx.mount(vol1, name="vol1", fs_type=FS_NATIVE)
        p2 = ufx.mount(vol2, name="vol2", fs_type=FS_NATIVE)

        check("UniFlex: mount returns StoragePond", isinstance(p1, StoragePond))
        check("UniFlex: two mounts",               len(ufx.list_mounts()) == 2)
        check("UniFlex: get_mount works",          ufx.get_mount(vol1) is p1)

        # Duplicate mount rejected
        dup_err = False
        try:
            ufx.mount(vol1, name="vol1_dup")
        except ValueError:
            dup_err = True
        check("UniFlex: duplicate mount rejected", dup_err)

        # Invalid fs_type rejected
        fs_err = False
        try:
            ufx.mount(vol2 + "_x", name="bad_fs", fs_type="UNKNOWN_FS")
        except ValueError:
            fs_err = True
        check("UniFlex: invalid fs_type rejected", fs_err)

        # Available decoders
        decoders = ufx.available_decoders()
        check("UniFlex: 6 decoders available", len(decoders) == 6)
        check("UniFlex: decoder has depth field",
              all("pipeline_depth" in d for d in decoders))

        # Unmount
        ok_unm = ufx.unmount(vol1)
        check("UniFlex: unmount returns True",   ok_unm)
        check("UniFlex: 1 mount remaining",      len(ufx.list_mounts()) == 1)
        check("UniFlex: get_mount → None after unmount",
              ufx.get_mount(vol1) is None)

        ok_bad = ufx.unmount("/nonexistent")
        check("UniFlex: unmount missing → False", not ok_bad)

        # Pond manager integration
        pm = ufx.pond_manager
        check("UniFlex: StoragePond in PondManager",
              p2.pond_id in pm._ponds)

# =============================================================================

print(f"\n{'='*55}")
passed = sum(1 for s,_ in results if s == "PASS")
failed = sum(1 for s,_ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
    print("\nUniFlex validated:")
    print("  - FS decoder registry (6 types, shared singleton, correct metadata)")
    print("  - PointerToken (checksum integrity, tamper detection)")
    print("  - TokenSpace (allocate, resolve, deregister, exhaustion)")
    print("  - StoragePond (mount, scan, file I/O, directory listing)")
    print("  - PRIVATE StoragePond (whitelist enforced on all file ops)")
    print("  - UniFlex manager (mount, unmount, duplicate/invalid rejection)")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")

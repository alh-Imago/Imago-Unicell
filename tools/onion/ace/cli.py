"""
cli.py — Onion Compression Engine CLI
───────────────────────────────────────
Usage:
  onion -c <path> [options]           compress file(s) or directory
  onion -d <file.onion> [options]     decompress / extract
  onion -i <file.onion>               inspect archive
  onion --set-meta <file.onion> ...   update metadata without recompressing
  onion --verify <file.onion>         verify HMAC signature

Compress options:
  -o <path>                 output path (default: <name>.onion)
  -e                        encrypt with AES-256-GCM
  -p <password>             password (else prompts)
  --exclude <pattern>       exclude glob pattern (repeatable)
  --no-default-ignores      disable built-in ignore list
  --no-audit                omit audit block
  --meta key=value          add metadata (repeatable)
                            tags=a,b,c  →  list
                            age=42      →  integer
  --sign-key <key>          HMAC-sign the archive with this key

Decompress options:
  -o <path>                 output path (default: auto)
  -p <password>             password for encrypted archives

set-meta options:
  --meta key=value          metadata to set/merge (repeatable)
  --replace                 replace all metadata instead of merging
  --sign-key <key>          re-sign after update
  -p <password>             alias for --sign-key (convenience)

verify options:
  --sign-key <key>          key to verify against
  -p <password>             alias for --sign-key
"""

import argparse
import getpass
import os
import sys


def _compress(args):
    from .analyser    import analyse
    from .transformer import compress_files
    from .manifest    import collect
    from .ignore      import build_matcher
    from .meta        import parse_pairs

    paths = args.compress_files
    for p in paths:
        if not os.path.exists(p):
            print(f"Error: path not found: {p}", file=sys.stderr); sys.exit(1)

    base_dir = paths[0] if (len(paths) == 1 and os.path.isdir(paths[0])) else ""
    matcher  = build_matcher(
        extra_patterns      = args.exclude or [],
        base_dir            = base_dir,
        use_default_ignores = not args.no_default_ignores,
    )

    try:
        files, label = collect(paths, matcher=matcher)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)

    if not files:
        print("Error: no files to compress after applying ignore patterns.", file=sys.stderr)
        sys.exit(1)

    # Password
    password = ""
    if args.encrypt:
        if args.password:
            password = args.password
        else:
            password = getpass.getpass("Enter encryption password: ")
            confirm  = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Error: passwords do not match.", file=sys.stderr); sys.exit(1)
        if not password:
            print("Error: password cannot be empty.", file=sys.stderr); sys.exit(1)

    # Metadata
    meta_pairs = None
    if args.meta:
        try:
            meta_pairs = parse_pairs(args.meta)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr); sys.exit(1)

    sign_key = args.sign_key or None

    dest      = args.output or (label + ".onion")
    total_raw = sum(len(d) for _, d in files)

    print(f"\nOnion Compression Engine v0.1")
    print(f"─────────────────────────────")
    if len(files) == 1:
        print(f"Source : {files[0][0]}  ({total_raw:,} bytes)")
    else:
        print(f"Source : {len(files)} files  ({total_raw:,} bytes total)")
        for rel, data in files[:8]:
            print(f"         {rel}  ({len(data):,} bytes)")
        if len(files) > 8:
            print(f"         ... and {len(files)-8} more")
    print(f"Dest   : {dest}")
    enc_label = "compress + AES-256-GCM" if args.encrypt else "compress"
    if sign_key: enc_label += " + HMAC-signed"
    print(f"Mode   : {enc_label}")
    if meta_pairs:
        print(f"Meta   : {list(meta_pairs.keys())}")

    total_data = b"".join(d for _, d in files)
    print(f"\n[Phase 1 — Strategist]")
    encrypt_only = getattr(args, 'encrypt_only', False)
    if encrypt_only: args.encrypt = True
    if encrypt_only and not args.encrypt:
        args.encrypt = True
    iset = analyse(total_data, encrypt=args.encrypt,
                   fast=getattr(args,'fast',False),
                   encrypt_only=encrypt_only)

    print(f"\n[Phase 2 — Transformer]")
    compress_files(files, iset, dest,
                   password=password,
                   audit=not args.no_audit,
                   meta_pairs=meta_pairs,
                   sign_key=sign_key)
    print(f"\nDone.\n")


def _decompress(args):
    from .transformer import decompress
    from .header      import unpack_header

    src = args.decompress_file
    if not os.path.isfile(src):
        print(f"Error: file not found: {src}", file=sys.stderr); sys.exit(1)

    with open(src, "rb") as f: raw = f.read()
    iset, _, _ = unpack_header(raw)

    password = ""
    if iset.encrypt:
        if args.password:
            password = args.password
        else:
            password = getpass.getpass("Enter decryption password: ")
        if not password:
            print("Error: archive is encrypted but no password supplied.",
                  file=sys.stderr); sys.exit(1)

    if args.output:
        dest = args.output
    elif src.endswith(".onion"):
        dest = src[:-6] or "extracted"
    else:
        dest = src + ".extracted"

    print(f"\nOnion Compression Engine v0.1")
    print(f"─────────────────────────────")
    print(f"Source : {src}  ({os.path.getsize(src):,} bytes)")
    print(f"Dest   : {dest}")
    if iset.encrypt: print(f"Mode   : decrypt + decompress")

    written = decompress(src, dest, password=password)
    print(f"\nExtracted {len(written)} file(s).\n")


def _inspect(args):
    from .header      import unpack_header, unpack_audit, AUDIT_MAGIC
    from .instruction import AlgoID
    from .transformer import _DECOMPRESS
    from .manifest    import is_manifest, unpack as manifest_unpack
    from .meta        import unpack as meta_unpack, is_meta, block_size
    import json, struct

    src = args.inspect_file
    if not os.path.isfile(src):
        print(f"Error: file not found: {src}", file=sys.stderr); sys.exit(1)

    with open(src, "rb") as f:
        data = f.read()

    iset, payload_offset, has_audit = unpack_header(data)
    total_payload = iset.layers[-1].compressed_size if iset.layers else 0

    print(f"\nOnion Archive Inspector")
    print(f"───────────────────────")
    print(f"File            : {src}  ({os.path.getsize(src):,} bytes)")
    print(f"Original size   : {iset.original_size:,} bytes")
    print(f"Original CRC32  : 0x{iset.original_crc:08X}")
    print(f"Encrypted       : {'Yes' if iset.encrypt else 'No'}")
    print(f"Layers          : {len(iset.layers)}")
    print()
    for i, layer in enumerate(iset.layers):
        print(f"  Layer {i+1}: {AlgoID.name(layer.algo_id)}")
        print(f"    Compressed size : {layer.compressed_size:,} bytes")
        print(f"    Checksum CRC32  : 0x{layer.checksum:08X}")

    # File listing (unencrypted only)
    if not iset.encrypt:
        try:
            payload = data[payload_offset: payload_offset + total_payload]
            current = payload
            for layer in reversed(iset.layers):
                current = _DECOMPRESS[layer.algo_id](current, "")
            if is_manifest(current):
                files     = manifest_unpack(current)
                total_raw = sum(len(d) for _, d in files)
                print(f"\nContents ({len(files)} file(s), {total_raw:,} bytes uncompressed):")
                for rel, fdata in files:
                    print(f"  {len(fdata):>10,}  {rel}")
        except Exception:
            pass
    else:
        print(f"\n  (File listing not available for encrypted archives)")

    # Trailing blocks
    trail = payload_offset + total_payload
    if has_audit:
        audit_recipe = unpack_audit(data, trail)
        if audit_recipe:
            aj_len = struct.unpack_from(">H", data, trail + 4)[0]
            trail += 4 + 2 + aj_len
            print(f"\nAudit Block:")
            print(json.dumps(audit_recipe, indent=2))

    if is_meta(data, trail):
        meta = meta_unpack(data, trail)
        if meta:
            print(f"\nMetadata:")
            for k, v in meta.items():
                if k == 'hmac_sha256':
                    print(f"  hmac_sha256    : {v[:24]}...  (use --verify to check)")
                else:
                    print(f"  {k:<16} : {v}")
    print()


def _set_meta(args):
    from .transformer import set_meta
    from .meta        import parse_pairs

    src = args.set_meta_file
    if not os.path.isfile(src):
        print(f"Error: file not found: {src}", file=sys.stderr); sys.exit(1)

    if not args.meta:
        print("Error: --meta key=value required.", file=sys.stderr); sys.exit(1)

    try:
        pairs = parse_pairs(args.meta)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)

    sign_key = args.sign_key or args.password or None
    merge    = not args.replace

    print(f"\nOnion — updating metadata: {src}")
    set_meta(src, pairs, sign_key=sign_key, merge=merge)
    print(f"Done.\n")


def _verify(args):
    from .transformer import verify

    src = args.verify_file
    if not os.path.isfile(src):
        print(f"Error: file not found: {src}", file=sys.stderr); sys.exit(1)

    sign_key = args.sign_key or args.password
    if not sign_key:
        sign_key = getpass.getpass("Enter signing key: ")

    print(f"\nOnion — verifying: {src}")
    try:
        ok = verify(src, sign_key)
        if ok:
            print(f"  ✓ HMAC-SHA256 signature VALID — archive is authentic and unmodified.\n")
        else:
            print(f"  ✗ HMAC-SHA256 signature INVALID — archive may have been tampered with.\n")
            sys.exit(2)
    except ValueError as e:
        print(f"  Error: {e}\n", file=sys.stderr); sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="onion",
        description="Onion \U0001f9c5 — Adaptive Layered Compression Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("-c",  dest="compress_files",  metavar="PATH", nargs="+",
                        help="compress file(s) or directory")
    parser.add_argument("-d",  dest="decompress_file", metavar="FILE",
                        help="decompress/extract FILE.onion")
    parser.add_argument("-i",  dest="inspect_file",    metavar="FILE",
                        help="inspect archive")
    parser.add_argument("--set-meta", dest="set_meta_file", metavar="FILE",
                        help="update metadata block without recompressing")
    parser.add_argument("--verify",   dest="verify_file",   metavar="FILE",
                        help="verify HMAC-SHA256 signature")

    parser.add_argument("-o",  dest="output",   metavar="OUTPUT", help="output path")
    parser.add_argument("-e",  dest="encrypt",  action="store_true",
                        help="encrypt with AES-256-GCM")
    parser.add_argument("-p",  "--password", dest="password", metavar="PASSWORD",
                        help="password for encryption/decryption/signing")
    parser.add_argument("--sign-key", dest="sign_key", metavar="KEY",
                        help="HMAC signing/verification key")

    parser.add_argument("--meta", dest="meta", metavar="KEY=VALUE",
                        action="append", default=[],
                        help="metadata key=value pair (repeatable)")
    parser.add_argument("--replace", dest="replace", action="store_true",
                        help="replace metadata instead of merging (set-meta only)")

    parser.add_argument("--exclude", dest="exclude", metavar="PATTERN",
                        action="append", default=[],
                        help="exclude glob pattern (repeatable)")
    parser.add_argument("--no-default-ignores", dest="no_default_ignores",
                        action="store_true",
                        help="disable built-in ignore list")
    parser.add_argument("--no-audit", dest="no_audit", action="store_true",
                        help="omit audit block")
    parser.add_argument("--fast", dest="fast", action="store_true",
                        help="fast mode: use LZ4 instead of LZ77+Huffman/LZMA (requires pip install lz4)")
    parser.add_argument("--encrypt-only", dest="encrypt_only", action="store_true",
                        help="skip compression entirely, encrypt only (implies -e)")

    args = parser.parse_args()

    if args.compress_files:   _compress(args)
    elif args.decompress_file: _decompress(args)
    elif args.inspect_file:    _inspect(args)
    elif args.set_meta_file:   _set_meta(args)
    elif args.verify_file:     _verify(args)
    else:
        parser.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Read-only reconnaissance for a Uconnect `swdl.upd` firmware update file.

We don't have a real .upd sample to develop against yet, so this makes no
assumptions about the container format — it just reports what's actually
there (magic bytes, embedded filesystem signatures, printable strings) so we
can figure out the format from real data instead of guessing.

Usage:
    python3 inspect_upd.py /path/to/swdl.upd

Never writes anywhere outside --out-dir, and never executes anything found
inside the file.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

# (offset, magic bytes, description) — common embedded-filesystem/container
# signatures worth flagging so we know what to try extracting with next.
KNOWN_SIGNATURES = [
    (0, b"PK\x03\x04", "ZIP"),
    (0, b"\x1f\x8b", "gzip"),
    (0, b"hsqs", "squashfs (little-endian)"),
    (0, b"sqsh", "squashfs (big-endian)"),
    (0, b"UBI#", "UBI image"),
    (0, b"\x55\x42\x49\x23", "UBI image (alt magic read)"),
    (1080, b"\x53\xef", "ext2/3/4 superblock magic (at offset 1080)"),
    (0, b"ANDROID!", "Android boot image"),
    (0, b"CrAU", "Android A/B (chromeos-style) OTA payload"),
    (0, b"\x7fELF", "ELF binary"),
    (0, b"ustar", "tar (POSIX)"),
    (257, b"ustar", "tar (POSIX, magic at offset 257)"),
]

INTERESTING_STRING_PATTERNS = [
    re.compile(rb"carplay", re.I),
    re.compile(rb"iap2", re.I),
    re.compile(rb"projection", re.I),
    re.compile(rb"safearea|safe_area|inset", re.I),
    re.compile(rb"climate.?bar", re.I),
    re.compile(rb"statusbar|status_bar", re.I),
    re.compile(rb"com\.harman\.[a-z0-9_.]+", re.I),
    re.compile(rb"com\.fca[a-z0-9_.]*", re.I),
    re.compile(rb"com\.apple\.carplay", re.I),
]


def scan_signatures(data: bytes):
    hits = []
    for offset, magic, desc in KNOWN_SIGNATURES:
        if data[offset : offset + len(magic)] == magic:
            hits.append((offset, desc))
    return hits


def find_all(data: bytes, magic: bytes, limit=20):
    """Find every occurrence of a magic sequence anywhere in the file (not just at a fixed offset) — containers are often concatenated or wrapped in a header."""
    offsets = []
    start = 0
    while len(offsets) < limit:
        idx = data.find(magic, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + 1
    return offsets


def extract_strings(data: bytes, min_len=6):
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    return pattern.findall(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("upd_file", type=Path)
    ap.add_argument(
        "--full-strings-out",
        type=Path,
        default=None,
        help="Optional path to dump ALL printable strings found (can be large).",
    )
    args = ap.parse_args()

    if not args.upd_file.exists():
        print(f"error: {args.upd_file} does not exist", file=sys.stderr)
        sys.exit(1)

    size = args.upd_file.stat().st_size
    print(f"file: {args.upd_file}")
    print(f"size: {size:,} bytes ({size / (1024*1024):.1f} MiB)")

    data = args.upd_file.read_bytes()

    print("\n-- header/signature scan --")
    hits = scan_signatures(data)
    if hits:
        for offset, desc in hits:
            print(f"  offset {offset}: {desc}")
    else:
        print("  no known signature matched at expected offsets")
        print("  first 64 bytes (hex):", data[:64].hex())

    print("\n-- embedded container search (any offset, first few hits each) --")
    for magic, desc in [
        (b"hsqs", "squashfs"),
        (b"PK\x03\x04", "zip"),
        (b"\x1f\x8b", "gzip"),
        (b"ANDROID!", "android boot image"),
    ]:
        offs = find_all(data, magic)
        if offs:
            print(f"  {desc}: found at offsets {offs}")

    if shutil.which("file"):
        print("\n-- `file` output --")
        subprocess.run(["file", str(args.upd_file)])

    if shutil.which("binwalk"):
        print("\n-- `binwalk` scan (if installed) --")
        subprocess.run(["binwalk", str(args.upd_file)])
    else:
        print(
            "\n(binwalk not installed — `pip install binwalk` or use your OS "
            "package manager for a much more thorough container scan)"
        )

    print("\n-- interesting strings (CarPlay/HMI-related keywords) --")
    found_any = False
    for pattern in INTERESTING_STRING_PATTERNS:
        matches = sorted(set(pattern.findall(data)))
        if matches:
            found_any = True
            label = pattern.pattern.decode(errors="replace")
            print(f"  [{label}]")
            for m in matches[:10]:
                print(f"    {m.decode(errors='replace')}")
    if not found_any:
        print("  none of the expected keywords appeared as plain text — the")
        print("  payload is likely compressed/encrypted at this layer; the")
        print("  container hits above are the next thing to unpack.")

    if args.full_strings_out:
        strings = extract_strings(data)
        args.full_strings_out.write_bytes(b"\n".join(strings))
        print(f"\nwrote {len(strings):,} strings to {args.full_strings_out}")


if __name__ == "__main__":
    main()

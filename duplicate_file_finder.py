#!/usr/bin/env python3
"""Find byte-identical files in a folder, regardless of filename.

Runs entirely on this machine: files are read from disk and hashed in-process.
No network calls are made and no file data leaves the computer.

Nothing is ever deleted or modified. The output is a plain text report,
written into the folder being analysed as "duplicate_files_found.txt".

Three passes, cheapest first:
  1. group by size in bytes
  2. hash the first 64 KB of same-size files
  3. full SHA-256 on whatever still matches

Usage:
    python3 duplicate_file_finder.py ~/Documents
"""

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from datetime import datetime

REPORT_NAME = "duplicate_files_found.txt"

CHUNK = 1024 * 1024   # stream large files 1 MB at a time
HEAD = 64 * 1024      # partial-hash window for pass 2


def hash_file(path, limit=None):
    h = hashlib.sha256()
    remaining = limit
    with open(path, "rb") as f:
        while True:
            want = CHUNK if remaining is None else min(CHUNK, remaining)
            if want <= 0:
                break
            chunk = f.read(want)
            if not chunk:
                break
            h.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return h.hexdigest()


def refine(groups, limit, errors):
    """Split each group by hash, keeping only those with survivors."""
    out = defaultdict(list)
    for key, paths in groups.items():
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                out[(key, hash_file(path, limit))].append(path)
            except OSError as e:
                errors.append((path, str(e)))
    return {k: v for k, v in out.items() if len(v) > 1}


def scan(root, exclude):
    by_size = defaultdict(list)
    errors = []
    total = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            path = os.path.join(dirpath, name)
            if os.path.abspath(path) == exclude:
                continue   # don't scan our own report
            try:
                st = os.lstat(path)
            except OSError as e:
                errors.append((path, str(e)))
                continue
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            total += 1
            if st.st_size > 0:   # empty files are trivially equal; not useful
                by_size[st.st_size].append(path)

    return by_size, total, errors


def main():
    ap = argparse.ArgumentParser(description="Report byte-identical files. Never deletes.")
    ap.add_argument("folder")
    args = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(args.folder))
    if not os.path.isdir(root):
        sys.exit(f"Not a folder: {root}")

    out_path = os.path.join(root, REPORT_NAME)

    by_size, total, errors = scan(root, exclude=out_path)
    sized = {s: p for s, p in by_size.items() if len(p) > 1}
    print(f"Scanned {total} files. {sum(len(p) for p in sized.values())} share a size.")

    partial = refine(sized, HEAD, errors)
    print(f"{sum(len(p) for p in partial.values())} survived the 64 KB check.")

    full = refine(partial, None, errors)

    sets = []
    for paths in full.values():
        paths.sort(key=lambda p: (len(p), p))
        sets.append(paths)
    sets.sort(key=lambda paths: (-len(paths), paths[0]))

    redundant = sum(len(paths) - 1 for paths in sets)

    lines = [
        f"Duplicate files found in {root}",
        f"Scanned {total} files on {datetime.now().strftime('%d %B %Y at %H:%M')}.",
        "",
        f"{len(sets)} set of duplicate files, {redundant} redundant files.",
        "",
    ]

    if not sets:
        lines.append("No duplicates found.")

    for i, paths in enumerate(sets, 1):
        lines.append(f"Duplicate {i}  ({len(paths)} copies)")
        for path in paths:
            lines.append("\t" + os.path.relpath(path, root))
        lines.append("")

    if errors:
        lines.append(f"{len(errors)} files could not be read:")
        for path, err in errors:
            lines.append(f"\t{os.path.relpath(path, root)} — {err}")
        lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\n{len(sets)} duplicate sets, {redundant} redundant files.")
    print(f"Report written to {out_path}. Nothing was deleted.")


if __name__ == "__main__":
    main()

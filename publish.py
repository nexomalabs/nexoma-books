#!/usr/bin/env python3
"""Copy the built site from _site/ to the repository root, where GitHub Pages
serves it from the main branch.

Deletions are confined to paths this script previously wrote, which are recorded
in .publish-manifest. Source directories (build.py, content/, templates/,
static/, tools/, .github/, README.md) are never touched.

    python3 build.py && python3 publish.py
    python3 publish.py --check     # fail if the published output is stale
"""

import argparse
import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "_site")
MANIFEST = os.path.join(ROOT, ".publish-manifest")

# Never deleted or overwritten by a publish, whatever the manifest says.
PROTECTED = {
    ".git", ".github", ".gitignore", ".publish-manifest",
    "build.py", "check.py", "publish.py",
    "content", "templates", "static", "tools", "_site", "README.md",
}


def built_files():
    out = []
    for base, _, files in os.walk(SITE):
        for name in files:
            full = os.path.join(base, name)
            out.append(os.path.relpath(full, SITE))
    return sorted(out)


def read_manifest():
    if not os.path.isfile(MANIFEST):
        return []
    with open(MANIFEST, encoding="utf-8") as fh:
        return [line.strip() for line in fh
                if line.strip() and not line.startswith("#")]


def top_segment(rel):
    return rel.replace(os.sep, "/").split("/", 1)[0]


def publish(check_only=False):
    if not os.path.isdir(SITE):
        print("No _site/ — run: python3 build.py")
        return 1

    files = built_files()
    stale = []

    # 1. remove files this script wrote before that the build no longer produces
    for rel in read_manifest():
        if rel in files or top_segment(rel) in PROTECTED:
            continue
        target = os.path.join(ROOT, rel)
        if os.path.exists(target):
            stale.append("would remove " + rel)
            if not check_only:
                os.remove(target)

    # 2. copy the build output over the root
    for rel in files:
        if top_segment(rel) in PROTECTED:
            print("refusing to overwrite protected path: " + rel)
            return 1
        src = os.path.join(SITE, rel)
        dst = os.path.join(ROOT, rel)
        if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
            continue
        stale.append("would update " + rel)
        if not check_only:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    # 3. prune directories left empty by step 1
    if not check_only:
        for base, dirs, names in os.walk(ROOT, topdown=False):
            rel = os.path.relpath(base, ROOT)
            if rel == "." or top_segment(rel) in PROTECTED:
                continue
            if not os.listdir(base):
                os.rmdir(base)

        with open(MANIFEST, "w", encoding="utf-8") as fh:
            fh.write("# Written by publish.py. Files it manages at the repository "
                     "root; do not edit by hand.\n")
            for rel in files:
                fh.write(rel.replace(os.sep, "/") + "\n")

    if check_only:
        if stale:
            print("STALE — the published site does not match the sources:")
            for line in stale[:40]:
                print("  " + line)
            print("\nRun: python3 build.py && python3 publish.py")
            return 1
        print("OK — published output matches the sources (%d files)." % len(files))
        return 0

    print("Published %d files to the repository root." % len(files))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report staleness without writing anything")
    args = ap.parse_args()
    return publish(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())

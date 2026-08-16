#!/usr/bin/env python3
"""Resolve every artifact reference in the V2 docs against the filesystem.

Run after renaming anything in v2/artifacts/, or after adding a page. Artifact
filenames drifted from the docs once already and nothing surfaced it — the docs
still read fine, the links just stopped pointing anywhere.

Checks three things:
  1. every .html reference in prd/v2/**.md resolves, whether written as a
     markdown link or a backticked path;
  2. every page a generator writes actually exists;
  3. every page in v2/artifacts/ is reachable from some doc or generator, so
     orphans get noticed too.

A reference marked "not yet generated" is expected to be missing and is reported
separately rather than as a failure — forward references to unrun work are
legitimate.

    python v2/build/check_links.py           # report
    python v2/build/check_links.py --strict  # exit 1 if anything is broken
"""
import glob
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = os.path.join(REPO, "prd", "v2")
ART = os.path.join(REPO, "v2", "artifacts")
BUILD = os.path.join(REPO, "v2", "build")

# a link is "pending" if the doc says so on the same line — forward references to
# pages whose workstream has not run are intentional, not rot
PENDING = re.compile(r"not yet generated|has not run|not started", re.I)
LINK = re.compile(r"\]\(([^)]+?\.html)\)|`([^`]*?\.html)`")


def rel(p):
    return os.path.relpath(p, REPO)


def doc_refs():
    """(file, line_no, link, is_pending) for every .html reference in the docs."""
    for f in sorted(glob.glob(os.path.join(DOCS, "**", "*.md"), recursive=True)):
        for n, line in enumerate(open(f, encoding="utf-8"), 1):
            for m in LINK.finditer(line):
                link = m.group(1) or m.group(2)
                if link.startswith("http") or "<" in link:
                    continue          # external, or a naming template
                yield f, n, link, bool(PENDING.search(line))


def resolve(doc, link):
    base = os.path.dirname(doc)
    p = (os.path.join(base, link) if link.startswith(".")
         else os.path.join(REPO, link))
    return os.path.normpath(p)


def generator_outputs():
    """{page: generator} — what each build script claims to write."""
    out = {}
    pat = re.compile(r'["\']([a-z0-9_.-]+\.html)["\']')
    for f in sorted(glob.glob(os.path.join(BUILD, "*.py"))):
        if os.path.basename(f) == os.path.basename(__file__):
            continue
        src = open(f, encoding="utf-8").read()
        for line in src.splitlines():
            if ".html" in line and ("ART" in line or "artifacts" in line):
                m = pat.search(line)
                if m:
                    out[m.group(1)] = os.path.basename(f)
    return out


def main():
    strict = "--strict" in sys.argv
    broken, pending, ok = [], [], 0

    for doc, n, link, is_pending in doc_refs():
        if os.path.exists(resolve(doc, link)):
            ok += 1
        elif is_pending:
            pending.append((doc, n, link))
        else:
            broken.append((doc, n, link))

    present = {os.path.basename(p) for p in glob.glob(os.path.join(ART, "*.html"))}
    gens = generator_outputs()
    missing_gen = {p: g for p, g in gens.items() if p not in present}
    referenced = {os.path.basename(l) for _, _, l, _ in doc_refs()}
    orphans = present - referenced - set(gens) - {"index.html"}

    print(f"docs: {ok} links resolve, {len(broken)} broken, {len(pending)} pending")
    for doc, n, link in broken:
        print(f"  BROKEN  {rel(doc)}:{n}  ->  {link}")
    for doc, n, link in pending:
        print(f"  pending {rel(doc)}:{n}  ->  {link}")

    print(f"\ngenerators: {len(gens)} pages declared, {len(missing_gen)} not on disk")
    for p, g in sorted(missing_gen.items()):
        print(f"  MISSING  {p}  (written by {g}) — run it, or the page was renamed")

    print(f"\nartifacts: {len(present)} pages present, {len(orphans)} unreferenced")
    for p in sorted(orphans):
        print(f"  ORPHAN   {p} — no doc links to it and no generator writes it")

    fail = bool(broken or missing_gen)
    if strict and fail:
        sys.exit(1)
    if not fail:
        print("\nall good")


if __name__ == "__main__":
    main()

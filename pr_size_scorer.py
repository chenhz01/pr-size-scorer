#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pr-size-scorer — review-cost grading for pull request diffs.

Parses a unified diff, computes churn (added+removed), file count, and
directory dispersion, grades the review cost (S/M/L/XL), and emits split
suggestions. Purely local text analysis of one diff file. Pure stdlib.
"""
import argparse
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", newline="\n")
except Exception:
    pass

VERSION = "0.1.1"

GENERATED_HINTS = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                   "poetry.lock", "Cargo.lock", "composer.lock", ".min.js", ".map")
TEST_HINTS = ("test", "spec")

GRADE_BANDS = [("S", 50), ("M", 200), ("L", 400)]  # XL beyond


class DiffError(Exception):
    """Input problem that maps to exit code 2."""


def _strip_ab(p):
    return p[2:] if p.startswith(("a/", "b/")) else p


def parse_diff(text):
    """Parse a unified diff. Returns list of file dicts with added/removed."""
    files = []
    cur = None
    git_old = git_new = None
    pending_old = pending_new = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            cur = None
            git_old = git_new = None
            pending_old = pending_new = None
            parts = line[11:].split(" ")
            if len(parts) == 2:
                git_old, git_new = _strip_ab(parts[0]), _strip_ab(parts[1])
            continue
        if line.startswith("--- "):
            p = line[4:].strip()
            pending_old = None if p == "/dev/null" else _strip_ab(p)
            continue
        if line.startswith("+++ "):
            p = line[4:].strip()
            pending_new = None if p == "/dev/null" else _strip_ab(p)
            path = pending_new or pending_old or git_new or git_old or "unknown"
            cur = {"file": path, "added": 0, "removed": 0, "binary": False,
                   "new": pending_old is None, "deleted": pending_new is None}
            files.append(cur)
            continue
        if cur is None:
            if line.startswith("Binary files ") and git_new:
                files.append({"file": git_new, "added": 0, "removed": 0,
                              "binary": True, "new": False, "deleted": False})
                cur = None
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("+"):
            cur["added"] += 1
        elif line.startswith("-"):
            cur["removed"] += 1
        elif line.startswith("Binary files"):
            cur["binary"] = True
    return files


def is_generated(path):
    low = path.lower()
    return any(h in low for h in GENERATED_HINTS)


def is_test(path):
    low = path.lower()
    return any(h in low for h in TEST_HINTS)


def grade(churn):
    for g, band in GRADE_BANDS:
        if churn < band:
            return g
    return "XL"


def score(files, exclude=None):
    """Core scoring. Returns report dict."""
    rx = re.compile(exclude) if exclude else None
    kept = [f for f in files if not (rx and rx.search(f["file"]))]
    excluded = len(files) - len(kept)
    added = sum(f["added"] for f in kept)
    removed = sum(f["removed"] for f in kept)
    churn = added + removed
    top_dirs = set()
    for f in kept:
        parts = f["file"].replace("\\", "/").split("/")
        top_dirs.add(parts[0] if len(parts) > 1 else "(root)")
    generated = [f["file"] for f in kept if is_generated(f["file"])]
    tests = [f["file"] for f in kept if is_test(f["file"])]
    src = [f for f in kept if not is_generated(f["file"]) and not is_test(f["file"])]

    suggestions = []
    if excluded:
        suggestions.append("%d file(s) excluded by --exclude; grade reflects the rest" % excluded)
    if generated:
        suggestions.append("exclude generated/lock files from review: %s"
                           % ", ".join(generated[:3]))
    if len(top_dirs) >= 3 and len(kept) > 5:
        suggestions.append("spans %d top-level directories; consider one PR per subsystem"
                           % len(top_dirs))
    if churn >= 200 and not tests:
        suggestions.append("large change with no test files touched; add or update tests")
    if len(src) > 10:
        suggestions.append("%d source files changed; split by feature if independent" % len(src))
    if not suggestions:
        suggestions.append("size is reviewable as-is")

    return {
        "schema": "pr-size-scorer/v1",
        "files_changed": len(kept),
        "added": added,
        "removed": removed,
        "churn": churn,
        "grade": grade(churn),
        "top_dirs": sorted(top_dirs),
        "dispersion": len(top_dirs),
        "generated_files": generated,
        "test_files": tests,
        "suggestions": suggestions,
    }


def load_diff(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        raise DiffError("cannot read diff file: %s" % e)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pr-size-scorer",
        description="Grade the review cost of a PR diff: churn + file dispersion -> S/M/L/XL + split suggestions.")
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("score", help="score a unified diff file")
    p.add_argument("--diff", required=True, help="path to a unified diff (.diff/.patch)")
    p.add_argument("--exclude", default=None, help="regex of paths to exclude from scoring")
    p.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd != "score":
        parser.print_usage(sys.stderr)
        return 2
    try:
        rx = None
        if args.exclude:
            try:
                rx = re.compile(args.exclude)
            except re.error as e:
                raise DiffError("invalid --exclude regex: %s" % e)
        files = parse_diff(load_diff(args.diff))
        report = score(files, exclude=args.exclude)
    except DiffError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print("pr-size-scorer: %d file(s), +%d/-%d, churn %d -> grade %s (dispersion %d)"
              % (report["files_changed"], report["added"], report["removed"],
                 report["churn"], report["grade"], report["dispersion"]))
        for s in report["suggestions"]:
            print("  - %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())

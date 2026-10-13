# Changelog

## v0.1.1 (2026-10-13)

Round-2 revisions after first-draft self-review (1 failure + 1 error exposed
2 real parser defects):

- **Parser fix (new files):** `--- /dev/null` arrives *before* the `+++`
  line, so the old code could never set the `new` flag. Rewritten as
  pending-side tracking; new/deleted flags now correct.
- **Parser fix (deleted files):** `+++ /dev/null` previously created an
  entry literally named `/dev/null`; path now falls back to the `diff --git`
  header.
- **Parser fix (binary diffs):** binary files without a `+++` line were
  dropped entirely; now an entry is created from the `diff --git` header.
- Suite raised 57 -> 62 cases (deleted-path, binary-entry, pending-new,
  deleted-churn, mode-change-only); re-run green (SUMMARY: PASS 62/62).
- Performance measured: 7.64 ms/score on a 500-file, 13k-line diff [Measured].

## v0.1.0 (2026-10-13)

First draft:

- Unified-diff parser: per-file added/removed, new/deleted/binary flags.
- Churn = added + removed; S/M/L/XL grade bands; top-level directory
  dispersion; generated/lockfile and test-file tagging.
- Rule-based split suggestions; `--exclude` regex with excluded-count report.
- argparse CLI (`score`), self_test with scaffold-v2 four defenses,
  README, LICENSE, ALIGNMENT.

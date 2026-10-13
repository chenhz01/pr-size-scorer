# ALIGNMENT — pr-size-scorer

Round R14, rubric v4.0 (E/F graded). Local-only draft: no git remote, no push, no repo creation.
Date: 2026-10-13.

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Runnable Python, pure stdlib | PASS | pr_size_scorer.py imports only argparse/json/re/sys |
| 2 | argparse CLI | PASS | `score` with `--diff/--exclude/--json`; usage errors exit 2, invalid regex exit 2 |
| 3 | self_test inherits scaffold-v2 four defenses | PASS | D1 SystemExit+Exception in run_cli (tested); D2 unicode paths (CJK, tested); D3 fixtures newline="" via tmp_diff (tested, CRLF case); D4 last line SUMMARY |
| 4 | E gate >=60 cases, 3 categories | PASS | SUMMARY: PASS 62/62 — TestParseDiff/TestClassification/TestScore (functional), TestCli (exception), TestExtremeEdge (CRLF/unicode/10k-line/rename-only) |
| 5 | SUMMARY last-line contract | PASS | final line `SUMMARY: PASS 62/62` |
| 6 | README English, <=60-word lead | PASS | README.md opening paragraph is 57 words |
| 7 | README Problem section | PASS | README.md '## Problem' |
| 8 | README How-it-works | PASS | README.md '## How it works' |
| 9 | README Quickstart with timing | PASS | README.md '## Quickstart' says "~1 min total" |
| 10 | why-not-X >=3 alternatives | PASS | README.md '## Why not X' lists 4 incl. real anchors budougumi0617/action-pr-size-checker and SpecterOps/pr-size-check |
| 11 | Performance [Measured] + repro command | PASS | README.md '## Performance': 7.64 ms/score on 500-file diff [Measured], repro script included |
| 12 | Minimal Fallback | PASS | README.md '## Minimal Fallback' (git diff --stat + manual bands) |
| 13 | Design Trade-offs | PASS | README.md '## Design Trade-offs' (4 entries) |
| 14 | Limits & Second-order Effects | PASS | README.md '## Limits & Second-order Effects' (4 entries) |
| 15 | FAQ incl When NOT to use | PASS | README.md '## FAQ' first item is 'When NOT to use this?' |
| 16 | Core Assumptions >=3 + confidence + as-of + hygiene | PASS | README.md '[Core Assumptions]' 4 items with confidence; 'As of 2026-10-13'; MIT LICENSE (zhengming contributors); CHANGELOG v0.1.0 -> v0.1.1 with 3 parser fixes; no secrets/real names; contact only hcac4735@agent.qq.com |
| + | Ethics/safety | PASS | Reads one local diff file; no network, no repo access, no execution |

Round-2 iteration (rule 99): self-review caught 3 real parser defects via
failing tests (new/deleted/binary file handling) — correctness dimension
improved. See CHANGELOG v0.1.1.

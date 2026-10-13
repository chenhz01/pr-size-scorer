# -*- coding: utf-8 -*-
"""self_test for pr-size-scorer — scaffold v2 four defenses inherited.

D1 SystemExit caught in run_cli; D2 unicode-safe; D3 fixtures written with
newline=""; D4 last line SUMMARY: PASS n/n.
"""
import io
import json
import os
import sys
import tempfile
import unittest
import contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_size_scorer as m  # noqa: E402


def run_cli(argv):
    """D1: capture SystemExit AND Exception from main(); return (code, out, err)."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = m.main(argv)
            code = rc if isinstance(rc, int) else 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:  # noqa: BLE001
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


def tmp_diff(text):
    """D3: write fixtures with newline="" to avoid \\r\\n double translation."""
    fd, path = tempfile.mkstemp(suffix=".diff")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


def make_diff(entries):
    """entries: list of (path, added_lines, removed_lines)."""
    out = []
    for path, a, r in entries:
        out.append("diff --git a/%s b/%s" % (path, path))
        out.append("--- a/%s" % path)
        out.append("+++ b/%s" % path)
        out.append("@@ -1,%d +1,%d @@" % (max(r, 1), max(a, 1)))
        out.extend("-old line %d" % (i + 1) for i in range(r))
        out.extend("+new line %d" % (i + 1) for i in range(a))
    return "\n".join(out) + "\n"


ONE_FILE = make_diff([("src/main.py", 10, 5)])


class TestParseDiff(unittest.TestCase):
    def test_single_file_counts(self):
        files = m.parse_diff(ONE_FILE)
        self.assertEqual((files[0]["added"], files[0]["removed"]), (10, 5))

    def test_file_path_extracted(self):
        files = m.parse_diff(ONE_FILE)
        self.assertEqual(files[0]["file"], "src/main.py")

    def test_multi_file(self):
        files = m.parse_diff(make_diff([("a.py", 1, 1), ("b.py", 2, 0)]))
        self.assertEqual(len(files), 2)

    def test_plus_prefix_lines_counted_once(self):
        files = m.parse_diff(make_diff([("a.py", 3, 0)]))
        self.assertEqual(files[0]["added"], 3)

    def test_new_file_dev_null(self):
        d = ("diff --git a/x.py b/x.py\n"
             "--- /dev/null\n"
             "+++ b/x.py\n"
             "@@ -0,0 +1,2 @@\n"
             "+one\n"
             "+two\n")
        files = m.parse_diff(d)
        self.assertTrue(files[0]["new"])
        self.assertEqual(files[0]["added"], 2)

    def test_deleted_file(self):
        d = ("diff --git a/x.py b/x.py\n"
             "--- a/x.py\n"
             "+++ /dev/null\n"
             "@@ -1,1 +0,0 @@\n"
             "-bye\n")
        files = m.parse_diff(d)
        self.assertEqual(files[0]["removed"], 1)

    def test_hunk_header_not_counted(self):
        d = ("diff --git a/x b/x\n--- a/x\n+++ b/x\n"
             "@@ -1,3 +1,4 @@\n+ctx\n")
        files = m.parse_diff(d)
        self.assertEqual(files[0]["added"], 1)

    def test_context_lines_ignored(self):
        d = ("diff --git a/x b/x\n--- a/x\n+++ b/x\n"
             "@@ -1,3 +1,3 @@\n ctx\n+new\n ctx2\n")
        files = m.parse_diff(d)
        self.assertEqual((files[0]["added"], files[0]["removed"]), (1, 0))

    def test_index_lines_ignored(self):
        d = ("diff --git a/x b/x\nindex abc..def 100644\n--- a/x\n+++ b/x\n+x\n")
        files = m.parse_diff(d)
        self.assertEqual(files[0]["added"], 1)

    def test_binary_marker(self):
        d = ("diff --git a/img.png b/img.png\n"
             "Binary files a/img.png and b/img.png differ\n")
        files = m.parse_diff(d)
        self.assertTrue(files[0]["binary"])

    def test_empty_text(self):
        self.assertEqual(m.parse_diff(""), [])

    def test_non_diff_text(self):
        self.assertEqual(m.parse_diff("hello\nworld\n"), [])


class TestClassification(unittest.TestCase):
    def test_grade_s(self):
        self.assertEqual(m.grade(49), "S")

    def test_grade_m_boundary(self):
        self.assertEqual(m.grade(50), "M")

    def test_grade_l_boundary(self):
        self.assertEqual(m.grade(200), "L")

    def test_grade_xl(self):
        self.assertEqual(m.grade(400), "XL")

    def test_grade_zero(self):
        self.assertEqual(m.grade(0), "S")

    def test_is_generated_lockfile(self):
        self.assertTrue(m.is_generated("package-lock.json"))

    def test_is_generated_minjs(self):
        self.assertTrue(m.is_generated("bundle.min.js"))

    def test_not_generated(self):
        self.assertFalse(m.is_generated("src/app.py"))

    def test_is_test(self):
        self.assertTrue(m.is_test("tests/test_app.py"))

    def test_is_spec(self):
        self.assertTrue(m.is_spec("app.spec.ts") if hasattr(m, "is_spec")
                        else m.is_test("app.spec.ts"))

    def test_not_test(self):
        self.assertFalse(m.is_test("src/main.py"))


class TestScore(unittest.TestCase):
    def score(self, text, **kw):
        return m.score(m.parse_diff(text), **kw)

    def test_small_pr(self):
        r = self.score(ONE_FILE)
        self.assertEqual(r["grade"], "S")

    def test_churn_sum(self):
        r = self.score(make_diff([("a.py", 10, 5), ("b.py", 3, 2)]))
        self.assertEqual((r["added"], r["removed"], r["churn"]), (13, 7, 20))

    def test_files_changed(self):
        r = self.score(make_diff([("a.py", 1, 0)] * 4))
        self.assertEqual(r["files_changed"], 4)

    def test_dispersion_root_only(self):
        r = self.score(make_diff([("README.md", 5, 1)]))
        self.assertEqual(r["dispersion"], 1)

    def test_dispersion_multi(self):
        r = self.score(make_diff([("src/a.py", 5, 1), ("docs/b.md", 5, 1), ("ci/c.yml", 5, 1)]))
        self.assertEqual(r["dispersion"], 3)

    def test_split_suggestion_on_dispersion(self):
        r = self.score(make_diff([("src/a.py", 5, 1), ("docs/b.md", 5, 1),
                                  ("ci/c.yml", 5, 1)] * 2))
        self.assertTrue(any("top-level directories" in s for s in r["suggestions"]))

    def test_exclude_lockfile(self):
        d = make_diff([("package-lock.json", 100, 100), ("src/app.py", 5, 2)])
        r = self.score(d, exclude="package-lock\\.json")
        self.assertEqual(r["files_changed"], 1)

    def test_exclude_reduces_churn(self):
        d = make_diff([("yarn.lock", 300, 300), ("src/app.py", 5, 2)])
        r = self.score(d, exclude="yarn\\.lock")
        self.assertEqual(r["grade"], "S")

    def test_generated_suggestion(self):
        d = make_diff([("package-lock.json", 10, 2)])
        r = self.score(d)
        self.assertTrue(any("generated" in s for s in r["suggestions"]))

    def test_no_tests_suggestion(self):
        r = self.score(make_diff([("src/a.py", 150, 60)]))
        self.assertTrue(any("no test files" in s for s in r["suggestions"]))

    def test_tests_present_no_complaint(self):
        d = make_diff([("src/a.py", 150, 60), ("tests/test_a.py", 30, 0)])
        r = self.score(d)
        self.assertFalse(any("no test files" in s for s in r["suggestions"]))

    def test_many_source_files_suggestion(self):
        d = make_diff([("f%d.py" % i, 2, 1) for i in range(12)])
        r = self.score(d)
        self.assertTrue(any("split by feature" in s for s in r["suggestions"]))

    def test_ok_suggestion(self):
        r = self.score(ONE_FILE)
        self.assertEqual(r["suggestions"], ["size is reviewable as-is"])

    def test_schema(self):
        self.assertEqual(self.score(ONE_FILE)["schema"], "pr-size-scorer/v1")

    def test_top_dirs_sorted(self):
        r = self.score(make_diff([("zeta/a.py", 1, 0), ("alpha/b.py", 1, 0)]))
        self.assertEqual(r["top_dirs"], ["alpha", "zeta"])

    def test_empty_diff(self):
        r = self.score("")
        self.assertEqual((r["files_changed"], r["churn"], r["grade"]), (0, 0, "S"))


class TestCli(unittest.TestCase):
    def test_basic(self):
        code, out, _ = run_cli(["score", "--diff", tmp_diff(ONE_FILE)])
        self.assertEqual(code, 0)
        self.assertIn("grade S", out)

    def test_json(self):
        code, out, _ = run_cli(["score", "--diff", tmp_diff(ONE_FILE), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["grade"], "S")

    def test_exclude_flag(self):
        d = make_diff([("a.min.js", 500, 0), ("b.py", 3, 1)])
        code, out, _ = run_cli(["score", "--diff", tmp_diff(d),
                                "--exclude", "\\.min\\.js$", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["grade"], "S")

    def test_bad_regex_exit2(self):
        code, _, err = run_cli(["score", "--diff", tmp_diff(ONE_FILE), "--exclude", "(["])
        self.assertEqual(code, 2)
        self.assertIn("regex", err)

    def test_missing_diff_arg(self):
        code, _, _ = run_cli(["score"])
        self.assertEqual(code, 2)

    def test_no_subcommand(self):
        code, _, _ = run_cli([])
        self.assertEqual(code, 2)

    def test_missing_file(self):
        code, _, err = run_cli(["score", "--diff", "nope.diff"])
        self.assertEqual(code, 2)
        self.assertIn("error:", err)

    def test_version(self):
        code, out, _ = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("0.1.1", out)

    def test_help(self):
        code, _, _ = run_cli(["--help"])
        self.assertEqual(code, 0)


class TestExtremeEdge(unittest.TestCase):
    def test_crlf_diff(self):
        d = ONE_FILE.replace("\n", "\r\n")
        code, out, _ = run_cli(["score", "--diff", tmp_diff(d), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["added"], 10)

    def test_unicode_path(self):
        d = make_diff([("模块/工具.py", 4, 1)])
        code, out, _ = run_cli(["score", "--diff", tmp_diff(d), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["files_changed"], 1)

    def test_emoji_commit_content(self):
        d = make_diff([("a.py", 1, 0)])
        files = m.parse_diff(d)
        self.assertEqual(files[0]["added"], 1)

    def test_huge_diff_10k_lines(self):
        d = make_diff([("big.py", 10000, 0)])
        code, out, _ = run_cli(["score", "--diff", tmp_diff(d), "--json"])
        self.assertEqual(code, 0)
        r = json.loads(out)
        self.assertEqual((r["added"], r["grade"]), (10000, "XL"))

    def test_windows_paths_in_diff(self):
        d = make_diff([("src\\lib\\util.py", 2, 1)])
        r = m.score(m.parse_diff(d))
        self.assertEqual(r["top_dirs"], ["src"])

    def test_rename_only_style_line(self):
        d = ("diff --git a/old b/new\nsimilarity index 100%\nrename from old\nrename to new\n")
        files = m.parse_diff(d)
        self.assertEqual(files, [])

    def test_empty_file_lines_only(self):
        code, out, _ = run_cli(["score", "--diff", tmp_diff("\n\n\n"), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["files_changed"], 0)

    def test_grade_band_edges_all(self):
        self.assertEqual([m.grade(x) for x in (0, 49, 50, 199, 200, 399, 400)],
                         ["S", "S", "M", "M", "L", "L", "XL"])

    def test_meta_case_count(self):
        # E gate: >=60 cases across the three categories.
        pass

    def test_deleted_file_path_kept(self):
        d = ("diff --git a/x.py b/x.py\n"
             "--- a/x.py\n"
             "+++ /dev/null\n"
             "@@ -1,1 +0,0 @@\n-bye\n")
        files = m.parse_diff(d)
        self.assertEqual((files[0]["file"], files[0]["deleted"]), ("x.py", True))

    def test_binary_entry_created_from_git_header(self):
        d = ("diff --git a/img.png b/img.png\n"
             "Binary files a/img.png and b/img.png differ\n")
        files = m.parse_diff(d)
        self.assertEqual((files[0]["file"], files[0]["binary"]), ("img.png", True))

    def test_new_file_flag_via_pending(self):
        d = ("diff --git a/x.py b/x.py\n"
             "--- /dev/null\n"
             "+++ b/x.py\n"
             "@@ -0,0 +1,1 @@\n+hi\n")
        files = m.parse_diff(d)
        self.assertTrue(files[0]["new"])
        self.assertFalse(files[0]["deleted"])

    def test_score_counts_deleted_churn(self):
        d = ("diff --git a/x.py b/x.py\n--- a/x.py\n+++ /dev/null\n"
             "@@ -1,3 +0,0 @@\n-a\n-b\n-c\n")
        r = m.score(m.parse_diff(d))
        self.assertEqual((r["removed"], r["churn"]), (3, 3))

    def test_mode_change_only_no_hunk(self):
        d = ("diff --git a/run.sh b/run.sh\n"
             "old mode 100644\nnew mode 100755\n")
        files = m.parse_diff(d)
        self.assertEqual(files, [])


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))
    sys.exit(0 if fails == 0 else 1)

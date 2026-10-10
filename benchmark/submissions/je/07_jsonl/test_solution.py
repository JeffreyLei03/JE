import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

import solution


def run(lines: list[str]) -> tuple[dict, list[str]]:
    source = io.StringIO("\n".join(lines))
    sink = io.StringIO()
    stats = solution.process(source, sink)
    out_lines = [ln for ln in sink.getvalue().split("\n") if ln]
    return stats, out_lines


class ProcessTests(unittest.TestCase):
    def test_empty_input(self):
        stats, out = run([])
        self.assertEqual(stats, {"accepted": 0, "invalid": 0, "ignored": 0})
        self.assertEqual(out, [])

    def test_blank_lines_ignored(self):
        stats, out = run(["", "   ", "\t"])
        self.assertEqual(stats["ignored"], 3)
        self.assertEqual(stats["accepted"], 0)
        self.assertEqual(out, [])

    def test_malformed_json_invalid(self):
        stats, out = run(["{not json}", "42x"])
        self.assertEqual(stats["invalid"], 2)

    def test_non_object_valid_json_invalid(self):
        stats, out = run(["[1,2,3]", '"hello"', "42", "null", "true"])
        self.assertEqual(stats["invalid"], 5)

    def test_non_sale_object_ignored(self):
        stats, out = run([json.dumps({"type": "refund", "amount": 5})])
        self.assertEqual(stats["ignored"], 1)
        self.assertEqual(stats["invalid"], 0)

    def test_missing_type_ignored(self):
        stats, out = run([json.dumps({"customer": "a", "amount": 1})])
        self.assertEqual(stats["ignored"], 1)

    def test_valid_sale_aggregation(self):
        lines = [
            json.dumps({"type": "sale", "customer": "bob", "amount": 5}),
            json.dumps({"type": "sale", "customer": "alice", "amount": 3}),
            json.dumps({"type": "sale", "customer": "bob", "amount": 7}),
        ]
        stats, out = run(lines)
        self.assertEqual(stats["accepted"], 3)
        self.assertEqual(
            out,
            [
                json.dumps({"customer": "alice", "total": 3, "count": 1}),
                json.dumps({"customer": "bob", "total": 12, "count": 2}),
            ],
        )

    def test_customer_whitespace_stripped(self):
        stats, out = run(
            [json.dumps({"type": "sale", "customer": "  carol  ", "amount": 1})]
        )
        self.assertEqual(stats["accepted"], 1)
        self.assertEqual(json.loads(out[0])["customer"], "carol")

    def test_empty_customer_invalid(self):
        stats, _ = run([json.dumps({"type": "sale", "customer": "   ", "amount": 1})])
        self.assertEqual(stats["invalid"], 1)

    def test_non_string_customer_invalid(self):
        stats, _ = run([json.dumps({"type": "sale", "customer": 5, "amount": 1})])
        self.assertEqual(stats["invalid"], 1)

    def test_negative_amount_invalid(self):
        stats, _ = run([json.dumps({"type": "sale", "customer": "a", "amount": -1})])
        self.assertEqual(stats["invalid"], 1)

    def test_bool_amount_invalid(self):
        stats, _ = run(
            [
                json.dumps({"type": "sale", "customer": "a", "amount": True}),
                json.dumps({"type": "sale", "customer": "a", "amount": False}),
            ]
        )
        self.assertEqual(stats["invalid"], 2)

    def test_float_amount_invalid(self):
        stats, _ = run([json.dumps({"type": "sale", "customer": "a", "amount": 1.0})])
        self.assertEqual(stats["invalid"], 1)

    def test_zero_amount_accepted(self):
        stats, out = run([json.dumps({"type": "sale", "customer": "a", "amount": 0})])
        self.assertEqual(stats["accepted"], 1)
        self.assertEqual(json.loads(out[0])["total"], 0)

    def test_unicode_preserved(self):
        stats, out = run(
            [json.dumps({"type": "sale", "customer": "café", "amount": 2})]
        )
        self.assertEqual(stats["accepted"], 1)
        self.assertIn("café", out[0])

    def test_counts_mixed(self):
        lines = [
            "",
            json.dumps({"type": "sale", "customer": "a", "amount": 1}),
            "bad json",
            json.dumps({"type": "other"}),
            json.dumps({"type": "sale", "customer": "", "amount": 1}),
        ]
        stats, out = run(lines)
        self.assertEqual(stats, {"accepted": 1, "invalid": 2, "ignored": 2})
        self.assertEqual(json.loads(out[0])["count"], 1)

    def test_never_calls_read(self):
        class Guarded(io.StringIO):
            def read(self, *a, **k):  # pragma: no cover
                raise AssertionError("read() must not be called")

            def readlines(self, *a, **k):  # pragma: no cover
                raise AssertionError("readlines() must not be called")

        source = Guarded(
            json.dumps({"type": "sale", "customer": "a", "amount": 1}) + "\n"
        )
        sink = io.StringIO()
        stats = solution.process(source, sink)
        self.assertEqual(stats["accepted"], 1)


class CliTests(unittest.TestCase):
    def _run_cli(self, in_text, same_path=False):
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "in.jsonl")
            out_path = os.path.join(tmp, "out.jsonl")
            with open(in_path, "w", encoding="utf-8") as f:
                f.write(in_text)
            target = in_path if same_path else out_path
            proc = subprocess.run(
                [sys.executable, solution.__file__, in_path, target],
                capture_output=True,
                text=True,
            )
            out_text = None
            if os.path.exists(out_path):
                with open(out_path, encoding="utf-8") as f:
                    out_text = f.read()
            return proc, out_text

    def test_cli_success(self):
        proc, out_text = self._run_cli(
            "\n".join(
                [
                    json.dumps({"type": "sale", "customer": "a", "amount": 2}),
                    json.dumps({"type": "sale", "customer": "a", "amount": 3}),
                ]
            )
            + "\n"
        )
        self.assertEqual(proc.returncode, 0)
        stats = json.loads(proc.stdout)
        self.assertEqual(stats, {"accepted": 2, "invalid": 0, "ignored": 0})
        record = json.loads(out_text.strip())
        self.assertEqual(record, {"customer": "a", "total": 5, "count": 2})

    def test_cli_same_path_rejected(self):
        proc, _ = self._run_cli("", same_path=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_cli_wrong_args(self):
        proc = subprocess.run(
            [sys.executable, solution.__file__],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()

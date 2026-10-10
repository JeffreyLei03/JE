"""Smoke tests for solution.run_jobs."""

import unittest

from solution import run_jobs


class TestValidation(unittest.TestCase):
    def test_duplicate_ids_raise_before_handler(self):
        calls = []

        def handler(job, attempt):  # pragma: no cover - must not run
            calls.append(job)
            return None

        with self.assertRaises(ValueError):
            run_jobs(["a", "b", "a"], handler, 3)
        self.assertEqual(calls, [])

    def test_nonstring_id_raises_before_handler(self):
        calls = []

        def handler(job, attempt):  # pragma: no cover - must not run
            calls.append(job)
            return None

        with self.assertRaises(ValueError):
            run_jobs(["a", 1], handler, 3)
        self.assertEqual(calls, [])

    def test_bad_max_attempts(self):
        for bad in (0, -1, True, False, 1.5, "3", None):
            with self.assertRaises(ValueError):
                run_jobs([], lambda j, a: None, bad)

    def test_empty(self):
        self.assertEqual(
            run_jobs([], lambda j, a: None, 3),
            {"results": {}, "attempts": {}, "failed": {}},
        )


class TestExecution(unittest.TestCase):
    def test_all_success(self):
        def handler(job, attempt):
            return job.upper() + str(attempt)

        out = run_jobs(["a", "b"], handler, 3)
        self.assertEqual(out["results"], {"a": "A1", "b": "B1"})
        self.assertEqual(out["attempts"], {"a": 1, "b": 1})
        self.assertEqual(out["failed"], {})

    def test_retry_round_robin_order(self):
        calls = []

        def handler(job, attempt):
            calls.append((job, attempt))
            if job == "a" and attempt < 3:
                raise RuntimeError("transient")
            return job

        out = run_jobs(["a", "b", "c"], handler, 5)
        self.assertEqual(
            calls,
            [("a", 1), ("b", 1), ("c", 1), ("a", 2), ("a", 3)],
        )
        self.assertEqual(out["results"], {"a": "a", "b": "b", "c": "c"})
        self.assertEqual(out["attempts"], {"a": 3, "b": 1, "c": 1})
        self.assertEqual(out["failed"], {})

    def test_valueerror_is_permanent(self):
        calls = []

        def handler(job, attempt):
            calls.append((job, attempt))
            if job == "a":
                raise ValueError("permanent")
            return job

        out = run_jobs(["a", "b"], handler, 4)
        self.assertEqual(calls, [("a", 1), ("b", 1)])
        self.assertEqual(out["attempts"], {"a": 1, "b": 1})
        self.assertEqual(out["failed"], {"a": "ValueError"})
        self.assertEqual(out["results"], {"b": "b"})

    def test_terminal_failure_after_max_attempts(self):
        counter = {"n": 0}

        def handler(job, attempt):
            counter["n"] += 1
            raise KeyError("boom")

        out = run_jobs(["x"], handler, 3)
        self.assertEqual(counter["n"], 3)
        self.assertEqual(out["attempts"], {"x": 3})
        self.assertEqual(out["failed"], {"x": "KeyError"})
        self.assertEqual(out["results"], {})

    def test_none_result_is_stored(self):
        out = run_jobs(["a"], lambda j, a: None, 2)
        self.assertIn("a", out["results"])
        self.assertIsNone(out["results"]["a"])

    def test_base_exception_propagates(self):
        calls = []

        def handler(job, attempt):
            calls.append((job, attempt))
            if job == "b":
                raise KeyboardInterrupt()
            return job

        with self.assertRaises(KeyboardInterrupt):
            run_jobs(["a", "b", "c"], handler, 3)
        self.assertEqual(calls, [("a", 1), ("b", 1)])

    def test_input_not_mutated(self):
        jobs = ["a", "b", "c"]
        snapshot = list(jobs)
        run_jobs(jobs, lambda j, a: j, 2)
        self.assertEqual(jobs, snapshot)

    def test_unique_input_required_across_validation(self):
        out = run_jobs(["z"], lambda j, a: 0, 1)
        self.assertEqual(set(out), {"results", "attempts", "failed"})


if __name__ == "__main__":
    unittest.main()

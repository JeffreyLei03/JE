import asyncio
import unittest

from solution import bounded_map


class LimitValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_limits_raise_value_error(self):
        for bad in (0, -1, -100, True, False, 1.0, "1", None):
            with self.subTest(limit=bad):
                with self.assertRaises(ValueError):
                    await bounded_map(_identity, [], bad)

    async def test_invalid_limit_checked_even_for_empty_input(self):
        # A generator that is never iterated still must trigger validation.
        def gen():
            raise AssertionError("items must not be consumed")
            yield 1  # pragma: no cover

        with self.assertRaises(ValueError):
            await bounded_map(_identity, gen(), 0)


class BasicBehaviourTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_returns_empty_list(self):
        result = await bounded_map(_identity, [], 3)
        self.assertEqual(result, [])

    async def test_simple_mapping(self):
        result = await bounded_map(_double, [1, 2, 3, 4], 2)
        self.assertEqual(result, [2, 4, 6, 8])

    async def test_accepts_generator(self):
        items = (x for x in range(5))
        result = await bounded_map(_double, items, 2)
        self.assertEqual(result, [0, 2, 4, 6, 8])

    async def test_preserves_input_order_with_varying_delays(self):
        async def slow_double(x):
            # Make earlier items slower so completion order differs from input.
            await asyncio.sleep(0.01 * (5 - x))
            return x * 2

        result = await bounded_map(slow_double, range(5), 3)
        self.assertEqual(result, [0, 2, 4, 6, 8])

    async def test_limit_larger_than_items(self):
        result = await bounded_map(_double, [1, 2], 10)
        self.assertEqual(result, [2, 4])


class ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_never_exceeds_limit(self):
        active = 0
        peak = 0

        async def tracked(x):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0.02)
                return x
            finally:
                active -= 1

        result = await bounded_map(tracked, range(10), 3)
        self.assertEqual(result, list(range(10)))
        self.assertLessEqual(peak, 3)
        self.assertGreaterEqual(peak, 2)  # actually runs concurrently


class ErrorPropagationTests(unittest.IsolatedAsyncioTestCase):
    async def test_exception_propagates_and_workers_cancelled(self):
        cancelled = []

        async def flaky(x):
            if x == 0:
                await asyncio.sleep(0)
                raise RuntimeError("boom")
            try:
                await asyncio.sleep(10)
                return x
            except asyncio.CancelledError:
                cancelled.append(x)
                raise

        with self.assertRaises(RuntimeError) as ctx:
            await bounded_map(flaky, range(6), 3)
        self.assertEqual(str(ctx.exception), "boom")
        # The sibling workers must have been cancelled and cleaned up.
        await asyncio.sleep(0)
        self.assertTrue(cancelled)
        self._assert_no_extra_tasks()

    async def test_iterator_error_propagates(self):
        def gen():
            yield 1

            async def _noop(x):  # pragma: no cover
                return x

            raise KeyError("bad source")

        async def work(x):
            await asyncio.sleep(0)
            return x

        with self.assertRaises(KeyError):
            await bounded_map(work, gen(), 2)
        self._assert_no_extra_tasks()

    def _assert_no_extra_tasks(self):
        current = asyncio.current_task()
        leftovers = [t for t in asyncio.all_tasks() if t is not current]
        self.assertEqual(leftovers, [])


class CancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_caller_cancellation_cleans_up_workers(self):
        started = []
        cancelled = []

        async def slow(x):
            started.append(x)
            try:
                await asyncio.sleep(10)
                return x
            except asyncio.CancelledError:
                cancelled.append(x)
                raise

        task = asyncio.ensure_future(bounded_map(slow, range(10), 3))
        # Let the workers reach their sleep.
        for _ in range(5):
            await asyncio.sleep(0)

        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertTrue(task.cancelled())
        await asyncio.sleep(0)
        self.assertEqual(len(cancelled), len(started))
        current = asyncio.current_task()
        leftovers = [t for t in asyncio.all_tasks() if t is not current]
        self.assertEqual(leftovers, [])


async def _identity(x):
    await asyncio.sleep(0)
    return x


async def _double(x):
    await asyncio.sleep(0)
    return x * 2


if __name__ == "__main__":
    unittest.main()

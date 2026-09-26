import unittest

from sddlib.routing import ContextSizeRoutingStrategy, TaskContext, count_task_tokens


class FullTextTest(unittest.TestCase):
    def test_order_and_join(self):
        ctx = TaskContext("T", "S", ["C1", "C2"], ["X"], ["K"])
        self.assertEqual(ctx.full_text(), "T\nS\nC1\nC2\nX\nK")

    def test_empty_parts_skipped(self):
        ctx = TaskContext("", "S", ["", "C"], [], [""])
        self.assertEqual(ctx.full_text(), "S\nC")
        self.assertEqual(TaskContext().full_text(), "")

    def test_default_lists_not_shared(self):
        a, b = TaskContext(), TaskContext()
        a.contract_texts.append("x")
        self.assertEqual(b.contract_texts, [])

    def test_keyword_fields(self):
        ctx = TaskContext(code_file_texts=["code"], task_description="d")
        self.assertEqual(ctx.full_text(), "d\ncode")


class CountTest(unittest.TestCase):
    def test_empty_zero(self):
        self.assertEqual(count_task_tokens(TaskContext()), 0)

    def test_rounds_up(self):
        self.assertEqual(count_task_tokens(TaskContext("a")), 1)
        self.assertEqual(count_task_tokens(TaskContext("abcd")), 1)
        self.assertEqual(count_task_tokens(TaskContext("abcde")), 2)

    def test_counts_separators(self):
        # "ab\ncd" hat 5 Zeichen
        self.assertEqual(count_task_tokens(TaskContext("ab", "cd")), 2)


class RouteTest(unittest.TestCase):
    def test_equality_is_local(self):
        s = ContextSizeRoutingStrategy(1000, 200, True, counter=lambda c: 800)
        self.assertEqual(s.route(TaskContext()), "local")

    def test_one_over_is_cloud(self):
        s = ContextSizeRoutingStrategy(1000, 200, True, counter=lambda c: 801)
        self.assertEqual(s.route(TaskContext()), "cloud")

    def test_reserve_counts(self):
        s = ContextSizeRoutingStrategy(1000, 0, True, counter=lambda c: 1000)
        self.assertEqual(s.route(TaskContext()), "local")
        s = ContextSizeRoutingStrategy(1000, 1, True, counter=lambda c: 1000)
        self.assertEqual(s.route(TaskContext()), "cloud")

    def test_disabled_never_calls_counter(self):
        def boom(ctx):
            raise AssertionError("Zähler darf nicht laufen")
        s = ContextSizeRoutingStrategy(10**9, 0, False, counter=boom)
        self.assertEqual(s.route(TaskContext()), "cloud")

    def test_default_counter(self):
        ctx = TaskContext("x" * 40)  # 10 Tokens
        self.assertEqual(ContextSizeRoutingStrategy(15, 5, True).route(ctx), "local")
        self.assertEqual(ContextSizeRoutingStrategy(14, 5, True).route(ctx), "cloud")

    def test_counter_receives_context(self):
        gesehen = []
        s = ContextSizeRoutingStrategy(100, 0, True, counter=lambda c: gesehen.append(c) or 1)
        ctx = TaskContext("t")
        s.route(ctx)
        self.assertIs(gesehen[0], ctx)

    def test_deterministic(self):
        s = ContextSizeRoutingStrategy(50, 10, True)
        ctx = TaskContext("y" * 160)
        self.assertEqual({s.route(ctx) for _ in range(5)}, {"local"})


if __name__ == "__main__":
    unittest.main()

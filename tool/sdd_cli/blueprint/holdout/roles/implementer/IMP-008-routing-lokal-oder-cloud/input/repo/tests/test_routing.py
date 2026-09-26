import unittest

from sddlib.routing import ContextSizeRoutingStrategy, TaskContext


class RoutingTest(unittest.TestCase):
    def test_fr03_small_context_goes_local(self):
        s = ContextSizeRoutingStrategy(8000, 1000, True, counter=lambda ctx: 500)
        self.assertEqual(s.route(TaskContext(task_description="klein")), "local")

    def test_fr03_large_context_goes_cloud(self):
        s = ContextSizeRoutingStrategy(8000, 1000, True, counter=lambda ctx: 7500)
        self.assertEqual(s.route(TaskContext()), "cloud")


if __name__ == "__main__":
    unittest.main()

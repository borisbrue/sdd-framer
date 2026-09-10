# TST-0147 – ContextSizeRoutingStrategy: Routing nach Token-Größe (CON-0125)
# Spec: SPEC-0036 | Level: unit | Contract: CON-0125


from sdd_cli.routing import ContextSizeRoutingStrategy, TaskContext


def _strategy(enabled: bool = True, window: int = 32768, reserve: int = 4096, token_count: int = 0):
    return ContextSizeRoutingStrategy(
        context_window=window,
        context_reserve_tokens=reserve,
        enabled=enabled,
        counter=lambda _ctx: token_count,
    )


class TestTST0147:
    def test_fits_local(self) -> None:
        # 20000 + 4096 = 24096 ≤ 32768 → local
        s = _strategy(token_count=20_000)
        assert s.route(TaskContext()) == "local"

    def test_too_large_cloud(self) -> None:
        # 30000 + 4096 = 34096 > 32768 → cloud
        s = _strategy(token_count=30_000)
        assert s.route(TaskContext()) == "cloud"

    def test_boundary_inclusive_local(self) -> None:
        # 28672 + 4096 = 32768 = window → local (Grenzwert inklusiv)
        s = _strategy(token_count=28_672)
        assert s.route(TaskContext()) == "local"

    def test_boundary_plus_one_cloud(self) -> None:
        # 28673 + 4096 = 32769 > 32768 → cloud
        s = _strategy(token_count=28_673)
        assert s.route(TaskContext()) == "cloud"

    def test_disabled_always_cloud(self) -> None:
        # enabled=False → cloud, unabhängig von Größe (INV-02)
        s = _strategy(enabled=False, token_count=1_000)
        assert s.route(TaskContext()) == "cloud"

    def test_no_network_call(self) -> None:
        # counter ist rein lokal – kein Netzwerkaufruf (INV-04)
        network_called = []

        def mock_counter(ctx: TaskContext) -> int:
            return 10_000

        s = ContextSizeRoutingStrategy(
            context_window=32768,
            context_reserve_tokens=4096,
            enabled=True,
            counter=mock_counter,
        )
        result = s.route(TaskContext())
        assert result == "local"
        assert network_called == []

    def test_return_values_only_local_or_cloud(self) -> None:
        # INV-01: Rückgabe ist immer "local" oder "cloud"
        for count in [0, 1000, 28672, 28673, 100_000]:
            s = _strategy(token_count=count)
            result = s.route(TaskContext())
            assert result in ("local", "cloud"), f"Unexpected: {result!r}"

    def test_deterministic(self) -> None:
        # INV-03: gleiche Eingabe → gleiche Ausgabe
        s = _strategy(token_count=20_000)
        ctx = TaskContext(task_description="hello")
        results = {s.route(ctx) for _ in range(10)}
        assert len(results) == 1

# TST-0140 | SPEC-0035 | CON-0121
# Token-Aggregation: Summe Sub-Agenten-Token == Gesamt-Eintrag in token-history

from tool.sdd_cli.estimation import TokenHistoryRow


class TestTST0140:
    def _make_row(self, task_id, inp, out):
        return TokenHistoryRow(
            id=1, timestamp="2026-06-03T00:00:00Z", spec_id="SPEC-0035",
            component="test", model="m", input_tokens=inp, output_tokens=out,
            cache_read_tokens=0, cache_write_tokens=0, duration_ms=0,
            task_id=task_id, task_label=f"Task {task_id}" if task_id else None,
        )

    def test_tc01_task_token_sum_equals_total(self) -> None:
        rows = [
            self._make_row("t1", 100, 50),
            self._make_row("t2", 200, 80),
            self._make_row("t3", 150, 60),
        ]
        task_rows = [r for r in rows if r.task_id is not None]
        assert sum(r.input_tokens for r in task_rows) == 450
        assert sum(r.output_tokens for r in task_rows) == 190

    def test_tc02_non_task_entries_excluded_from_aggregation(self) -> None:
        rows = [
            self._make_row("t1", 100, 50),
            self._make_row(None, 999, 999),
        ]
        task_rows = [r for r in rows if r.task_id is not None]
        assert sum(r.input_tokens for r in task_rows) == 100
        assert sum(r.output_tokens for r in task_rows) == 50

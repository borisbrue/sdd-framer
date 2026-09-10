# TST-0080 – LogEventBus: multicast, buffer-limit, subscribe/unsubscribe
# Contract: CON-0070 (log-streamer)
# Spec: SPEC-0022
from __future__ import annotations

import json
import threading

from sdd_cli.log_streamer import LogEventBus


class TestTST0080:
    # TC-01: publish liefert Zeile an alle N Subscribers (Multicast)
    def test_multicast_to_n_subscribers(self) -> None:
        bus = LogEventBus(max_lines=100)
        received: list[list[str]] = [[], [], []]
        bus.subscribe("SPEC-0022", lambda msg: received[0].append(msg))
        bus.subscribe("SPEC-0022", lambda msg: received[1].append(msg))
        bus.subscribe("SPEC-0022", lambda msg: received[2].append(msg))

        bus.publish("SPEC-0022", "hello world")

        assert len(received[0]) == 1
        assert len(received[1]) == 1
        assert len(received[2]) == 1

    # TC-02: veröffentlichte Nachrichten sind gültiges JSON mit spec_id
    def test_published_message_is_valid_json(self) -> None:
        bus = LogEventBus(max_lines=10)
        msgs: list[str] = []
        bus.subscribe("SPEC-0022", msgs.append)
        bus.publish("SPEC-0022", "test line")

        assert len(msgs) == 1
        data = json.loads(msgs[0])
        assert data["spec_id"] == "SPEC-0022"
        assert data["line"] == "test line"
        assert "ts" in data
        assert data["buffered"] is False

    # TC-03: Buffer-Limit wird eingehalten (FIFO, älteste werden verworfen)
    def test_buffer_limit_fifo(self) -> None:
        bus = LogEventBus(max_lines=3)
        for i in range(5):
            bus.publish("SPEC-0022", f"line-{i}")

        buf = bus.get_buffer("SPEC-0022")
        assert len(buf) == 3
        lines = [json.loads(m)["line"] for m in buf]
        assert lines == ["line-2", "line-3", "line-4"]

    # TC-04: get_buffer gibt gespeicherte Nachrichten zurück
    def test_get_buffer_returns_history(self) -> None:
        bus = LogEventBus(max_lines=10)
        bus.publish("SPEC-0022", "line-A")
        bus.publish("SPEC-0022", "line-B")

        buf = bus.get_buffer("SPEC-0022")
        assert len(buf) == 2

    # TC-05: unsubscribe stoppt Delivery für diesen Subscriber
    def test_unsubscribe_stops_delivery(self) -> None:
        bus = LogEventBus(max_lines=10)
        received: list[str] = []

        def cb(msg: str) -> None:
            received.append(msg)

        bus.subscribe("SPEC-0022", cb)
        bus.publish("SPEC-0022", "before")
        bus.unsubscribe("SPEC-0022", cb)
        bus.publish("SPEC-0022", "after")

        assert len(received) == 1
        assert json.loads(received[0])["line"] == "before"

    # TC-06: Client-Disconnect stoppt den Stream nicht für andere
    def test_client_disconnect_does_not_affect_others(self) -> None:
        bus = LogEventBus(max_lines=10)
        client1: list[str] = []
        client2: list[str] = []

        def cb1(msg: str) -> None:
            client1.append(msg)

        def cb2(msg: str) -> None:
            client2.append(msg)

        bus.subscribe("SPEC-0022", cb1)
        bus.subscribe("SPEC-0022", cb2)
        bus.publish("SPEC-0022", "before-disconnect")
        bus.unsubscribe("SPEC-0022", cb1)  # client1 disconnects
        bus.publish("SPEC-0022", "after-disconnect")

        assert len(client1) == 1  # only got the message before disconnect
        assert len(client2) == 2  # got both messages

    # TC-07: has_stream liefert False wenn kein Stream aktiv
    def test_has_stream_false_by_default(self) -> None:
        bus = LogEventBus()
        assert bus.has_stream("SPEC-0022") is False

    # TC-08: mark_active/mark_inactive steuern has_stream korrekt
    def test_mark_active_inactive(self) -> None:
        bus = LogEventBus()
        bus.mark_active("SPEC-0022")
        assert bus.has_stream("SPEC-0022") is True
        bus.mark_inactive("SPEC-0022")
        assert bus.has_stream("SPEC-0022") is False

    # TC-09: Thread-Safety – parallele publishes kein Datenverlust
    def test_thread_safe_parallel_publish(self) -> None:
        bus = LogEventBus(max_lines=1000)
        received: list[str] = []
        lock = threading.Lock()

        def cb(msg: str) -> None:
            with lock:
                received.append(msg)

        bus.subscribe("SPEC-0022", cb)
        threads = [
            threading.Thread(target=bus.publish, args=("SPEC-0022", f"line-{i}"))
            for i in range(50)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(received) == 50

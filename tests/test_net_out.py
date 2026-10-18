"""Live telemetry (UDP/TCP/websocket) is sent from a worker, in order, unchanged."""

import json
import threading

import background
import golden_harness as gh


class FakeTelemetryClient:
    def __init__(self):
        self.sent = []
        self.threads = set()

    def send(self, data):
        self.threads.add(threading.current_thread().name)
        self.sent.append(json.dumps(data, separators=(",", ":")))


def _racer(ns):
    Racer = ns["Racer"]
    return Racer.__new__(Racer)


def test_sendMQTT_order_content_and_thread():
    ns = gh.build_namespace()
    client = FakeTelemetryClient()
    ns["telemetry_client"] = client
    racer = _racer(ns)
    msgs = [
        {"option": "s", "lap": 1, "time": 0, "user": "u"},
        *(
            {"option": "position", "x": i * 0.5, "y": 1.0, "z": -2.0, "speed": i % 99}
            for i in range(300)
        ),
        {"option": "f", "lap": 1, "time": 12.345678901234, "step": 999, "user": "u"},
    ]
    for m in msgs:
        racer.sendMQTT(dict(m))
    background.drain_all()
    assert client.sent == [json.dumps(m, separators=(",", ":")) for m in msgs]
    assert client.threads == {"gw2-netout"}  # never on the caller (Tk) thread


def test_sendMQTT_without_client_is_a_noop():
    ns = gh.build_namespace()
    ns["telemetry_client"] = None
    _racer(ns).sendMQTT({"option": "s"})
    background.drain_all()


def test_sendMQTT_does_not_block_on_a_slow_client():
    ns = gh.build_namespace()
    gate = threading.Event()

    class Slow:
        def __init__(self):
            self.n = 0

        def send(self, data):
            gate.wait(5)
            self.n += 1

    slow = Slow()
    ns["telemetry_client"] = slow
    racer = _racer(ns)
    for _ in range(5):
        racer.sendMQTT(
            {"option": "position"}
        )  # returns immediately although send() blocks
    assert slow.n == 0
    gate.set()
    background.drain_all()
    assert slow.n == 5


def test_send_failure_is_contained():
    ns = gh.build_namespace()

    class Boom:
        def send(self, data):
            raise OSError("socket gone")

    ns["telemetry_client"] = Boom()
    _racer(ns).sendMQTT({"option": "s"})
    background.drain_all()  # must not raise


def test_websocket_event_is_serialised_in_order_and_swallows_closed():
    ns = gh.build_namespace()
    closed = type("WSClosed", (Exception,), {})
    ns["WebSocketConnectionClosedException"] = closed
    sent = []

    class WS:
        def send(self, text):
            sent.append((threading.current_thread().name, text))

    meter = ns["Meterv2"].__new__(ns["Meterv2"])
    events = [
        {"type": "position", "x": i, "timestamp": 1760790125.123456 + i}
        for i in range(50)
    ]
    for e in events:
        background.net_out.submit(meter._send_websocket_event, WS(), e)
    background.drain_all()
    assert [t for _n, t in sent] == [json.dumps(e) for e in events]
    assert {n for n, _t in sent} == {"gw2-netout"}

    class Closed:
        def send(self, text):
            raise closed("closed")

    background.net_out.submit(meter._send_websocket_event, Closed(), events[0])
    background.drain_all()  # swallowed exactly like the old inline try/except

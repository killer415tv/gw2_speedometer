import json
import logging
import threading
import time

import pytest

import telemetry_client as tc
from telemetry_client import MultiplayerListener, TelemetryClient


def wait_for(cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.01)
    return cond()


class FakeWS:
    def __init__(self, messages=(), then=None):
        self.messages = list(messages)
        self.then = then  # exception raised once messages are exhausted
        self.closed = False

    def recv(self):
        if self.messages:
            return self.messages.pop(0)
        if self.then is not None:
            raise self.then
        time.sleep(0.01)
        raise tc.WebSocketTimeoutException()

    def close(self):
        self.closed = True


# ---------------------------------------------------------------- backoff math
def test_backoff_is_exponential_and_capped():
    d = [tc._backoff_delay(n, 2.0, 60.0) for n in range(1, 10)]
    assert d[:5] == [2.0, 4.0, 8.0, 16.0, 32.0]
    assert max(d) == 60.0
    assert tc._backoff_delay(0, 2.0, 60.0) == 2.0
    assert tc._backoff_delay(10_000, 2.0, 60.0) == 60.0  # no overflow


# --------------------------------------------------- MultiplayerListener retry
def test_websocket_really_retries_until_success(monkeypatch):
    """Regression: the old code set running=False on failure, so the retry
    timer never reconnected."""
    monkeypatch.setattr(tc, "WS_RECONNECT_MIN_DELAY", 0.01)
    monkeypatch.setattr(tc, "WS_RECONNECT_MAX_DELAY", 0.05)
    attempts = []
    ws = FakeWS()

    def fake_open(self):
        attempts.append(time.monotonic())
        if len(attempts) < 4:
            raise ConnectionRefusedError("down")
        return ws

    monkeypatch.setattr(MultiplayerListener, "_open_connection", fake_open)
    ml = MultiplayerListener()
    ml.start()
    try:
        assert wait_for(lambda: ml.ws_client is ws)
        assert len(attempts) == 4
        assert ml.running is True
        assert ml._failures == 0  # reset after success
    finally:
        ml.stop()
    assert ws.closed


def test_start_does_not_block_on_connect(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def slow_open(self):
        started.set()
        release.wait(5)
        raise ConnectionRefusedError("x")

    monkeypatch.setattr(MultiplayerListener, "_open_connection", slow_open)
    ml = MultiplayerListener()
    t0 = time.monotonic()
    ml.start()
    assert time.monotonic() - t0 < 0.5  # returned while connect is still pending
    assert started.wait(2)
    ml.stop()
    release.set()


def test_retry_delay_is_bounded_and_grows(monkeypatch):
    delays = []
    ml = MultiplayerListener()
    monkeypatch.setattr(MultiplayerListener, "_open_connection", lambda self: (_ for _ in ()).throw(OSError("no")))
    monkeypatch.setattr(ml, "_schedule_connect", lambda d: delays.append(d))
    ml.running = True
    for _ in range(12):
        ml._connect()
    assert len(delays) == 12
    assert delays[0] >= tc.WS_RECONNECT_MIN_DELAY
    assert delays[3] > delays[0]
    assert max(delays) <= tc.WS_RECONNECT_MAX_DELAY * 1.2 + 1e-9
    assert ml.running is True  # still wants to reconnect


def test_failures_do_not_spam_warnings(monkeypatch, caplog):
    ml = MultiplayerListener()
    monkeypatch.setattr(MultiplayerListener, "_open_connection", lambda self: (_ for _ in ()).throw(OSError("no")))
    monkeypatch.setattr(ml, "_schedule_connect", lambda d: None)
    ml.running = True
    with caplog.at_level(logging.DEBUG, logger="telemetry_client"):
        for _ in range(25):
            ml._connect()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 3  # attempts 1, 11 and 21


def test_missing_websocket_package_stops_cleanly(monkeypatch):
    def no_pkg(self):
        raise ImportError("websocket")

    monkeypatch.setattr(MultiplayerListener, "_open_connection", no_pkg)
    ml = MultiplayerListener()
    ml.running = True
    ml._connect()
    assert ml.running is False


def test_receive_error_schedules_reconnect_and_callback_errors_are_isolated(monkeypatch):
    got = []

    def bad_callback(msg):
        got.append(msg)
        raise RuntimeError("boom")

    snap = json.dumps({"type": "snapshot", "users": []})
    ws = FakeWS(messages=["not json", "[1, 2]", snap, snap], then=ConnectionResetError("reset"))
    ml = MultiplayerListener()
    ml.set_snapshot_callback(bad_callback)
    scheduled = []
    monkeypatch.setattr(ml, "_schedule_connect", lambda d: scheduled.append(d))
    ml.running = True
    ml.ws_client = ws
    ml._receive_loop(ws)  # runs until the reset error
    assert len(got) == 2  # bad callback did not stop the loop; garbage was skipped
    assert ws.closed and ml.ws_client is None
    assert len(scheduled) == 1 and scheduled[0] > 0


def test_idle_timeout_is_not_a_failure(monkeypatch):
    ws = FakeWS()
    ml = MultiplayerListener()
    scheduled = []
    monkeypatch.setattr(ml, "_schedule_connect", lambda d: scheduled.append(d))
    ml.running = True
    ml.ws_client = ws
    t = threading.Thread(target=ml._receive_loop, args=(ws,), daemon=True)
    t.start()
    time.sleep(0.1)
    ml.running = False
    t.join(2)
    assert scheduled == []


def test_stale_loop_does_not_reconnect(monkeypatch):
    old, new = FakeWS(then=OSError("x")), FakeWS()
    ml = MultiplayerListener()
    scheduled = []
    monkeypatch.setattr(ml, "_schedule_connect", lambda d: scheduled.append(d))
    ml.running = True
    ml.ws_client = new
    ml._receive_loop(old)
    assert scheduled == [] and ml.ws_client is new


def test_session_filter_tolerates_bad_types():
    seen = []
    ml = MultiplayerListener(session_code=5)
    ml.set_snapshot_callback(seen.append)
    ml._handle_message({"type": "snapshot", "sessionCodes": None})
    ml._handle_message({"type": "snapshot", "sessionCodes": "5"})
    ml._handle_message({"type": "snapshot", "sessionCodes": [1, 2]})
    assert seen == []
    ml._handle_message({"type": "snapshot", "sessionCodes": [5]})
    assert len(seen) == 1


def test_stop_cancels_pending_retry_and_closes_socket(monkeypatch):
    monkeypatch.setattr(MultiplayerListener, "_open_connection", lambda self: (_ for _ in ()).throw(OSError("no")))
    ml = MultiplayerListener()
    ml.start()
    assert wait_for(lambda: ml._failures >= 1)
    ml.stop()
    n = ml._failures
    time.sleep(0.2)
    assert ml._failures == n and ml.running is False


# ------------------------------------------------------------- TelemetryClient
class FakeSock:
    def __init__(self, fail_connect=False, recv_results=()):
        self.fail_connect = fail_connect
        self.recv_results = list(recv_results)
        self.sent = []
        self.closed = False

    def settimeout(self, t):
        pass

    def setblocking(self, flag):
        pass

    def connect(self, addr):
        if self.fail_connect:
            raise ConnectionRefusedError("refused")

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, n):
        if self.recv_results:
            r = self.recv_results.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        raise BlockingIOError()

    def close(self):
        self.closed = True


def patch_sockets(monkeypatch, factory):
    real = tc.socket.socket

    def fake_socket(family=-1, type=-1, *a, **k):
        if type == tc.socket.SOCK_STREAM:
            return factory()
        return real(family, type, *a, **k)

    monkeypatch.setattr(tc.socket, "socket", fake_socket)


def test_tcp_connect_failure_backs_off_and_does_not_raise(monkeypatch):
    patch_sockets(monkeypatch, lambda: FakeSock(fail_connect=True))
    c = TelemetryClient()
    c._connect_tcp()
    assert c.tcp_connected is False and c.tcp_socket is None
    assert c._tcp_failures == 1
    first = c._tcp_next_attempt
    assert first > time.monotonic()
    # inside the backoff window a send must NOT try (and block) again
    attempts = []
    monkeypatch.setattr(c, "_connect_tcp", lambda: attempts.append(1))
    c._send_tcp(b"{}")
    assert attempts == []
    # once the window has passed it tries again
    c._tcp_next_attempt = time.monotonic() - 1
    c._send_tcp(b"{}")
    assert attempts == [1]
    c.disconnect()


def test_tcp_backoff_grows_and_is_capped(monkeypatch):
    patch_sockets(monkeypatch, lambda: FakeSock(fail_connect=True))
    c = TelemetryClient()
    gaps = []
    for _ in range(10):
        c._tcp_next_attempt = 0.0
        t0 = time.monotonic()
        c._connect_tcp()
        gaps.append(c._tcp_next_attempt - t0)
    assert gaps[0] == pytest.approx(tc.TCP_RECONNECT_MIN_DELAY, abs=0.2)
    assert gaps[2] > gaps[0]
    assert max(gaps) <= tc.TCP_RECONNECT_MAX_DELAY + 0.2
    c.disconnect()


def test_tcp_send_ok_and_send_error_marks_disconnected(monkeypatch):
    sock = FakeSock()
    patch_sockets(monkeypatch, lambda: sock)
    c = TelemetryClient()
    c._connect_tcp()
    assert c.tcp_connected
    c.send({"option": "c", "step": 1, "lap": 1, "time": 1.5})
    assert sock.sent and sock.sent[0].endswith(b"\n")
    assert json.loads(sock.sent[0])["option"] == "c"

    def boom(data):
        raise BrokenPipeError("pipe")

    sock.sendall = boom
    c.send({"option": "s"})  # must not raise
    assert c.tcp_connected is False and sock.closed
    c.disconnect()


def test_receive_loop_reconnects_after_server_closes(monkeypatch):
    monkeypatch.setattr(tc, "TCP_RECONNECT_MIN_DELAY", 0.05)
    socks = [FakeSock(recv_results=[b'{"option": "c"}\n', b""]), FakeSock()]
    patch_sockets(monkeypatch, lambda: socks.pop(0) if socks else FakeSock())
    received = []
    c = TelemetryClient()
    c.set_message_callback(received.append)
    c.connect("ana", "1")
    try:
        assert wait_for(lambda: len(received) == 1)
        # server closed (recv -> b""): the loop must notice and reconnect
        assert wait_for(lambda: c.tcp_connected and c.tcp_socket is not None and not c.tcp_socket.closed and not socks, 5)
    finally:
        c.disconnect()


def test_tcp_callback_and_garbage_do_not_kill_connection(monkeypatch):
    data = b'garbage\n[1]\n{"option": "x"}\n{"option": "y"}\n'
    sock = FakeSock(recv_results=[data])
    patch_sockets(monkeypatch, lambda: sock)
    calls = []

    def cb(m):
        calls.append(m["option"])
        raise RuntimeError("callback bug")

    c = TelemetryClient()
    c.set_message_callback(cb)
    c.connect("ana", "1")
    try:
        assert wait_for(lambda: calls == ["x", "y"])
        assert c.tcp_connected is True
    finally:
        c.disconnect()


def test_close_errors_are_logged_not_raised(caplog):
    class BadSock:
        def close(self):
            raise OSError("already closed")

    with caplog.at_level(logging.DEBUG, logger="telemetry_client"):
        tc._safe_close(BadSock(), "thing")
        tc._safe_close(None, "nothing")
    assert any("Error closing thing" in r.getMessage() for r in caplog.records)


def test_no_bare_except_left():
    import pathlib
    import re

    src = pathlib.Path(tc.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*except\s*:\s*$", src, flags=re.M)

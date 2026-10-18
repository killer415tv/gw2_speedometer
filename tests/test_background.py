import threading
import time

import background
import pytest


def test_worker_runs_tasks_in_submission_order_on_one_thread():
    w = background.Worker("gw2-test-order")
    seen, threads = [], set()

    def task(i):
        time.sleep(0.002 * (5 - i % 5))  # different durations must not reorder
        seen.append(i)
        threads.add(threading.current_thread().name)
        return i

    results = []
    for i in range(20):
        w.submit(task, i, on_done=results.append)
    background.drain_all()
    w.wait_idle(5)
    background.pump()
    assert seen == list(range(20))
    assert threads == {"gw2-test-order"}
    assert sorted(results) == list(range(20))


def test_on_done_runs_only_when_pumped_and_on_the_pumping_thread():
    w = background.Worker("gw2-test-ui")
    ran_on = []
    w.submit(
        lambda: "x", on_done=lambda r: ran_on.append((r, threading.current_thread()))
    )
    assert w.wait_idle(5)
    assert ran_on == []  # worker thread never touches UI callbacks
    background.pump()
    assert ran_on == [("x", threading.current_thread())]


def test_task_exception_is_logged_not_raised_and_on_done_gets_none(caplog):
    w = background.Worker("gw2-test-exc")
    got = []

    def boom():
        raise RuntimeError("network down")

    w.submit(boom, on_done=got.append)
    w.submit(lambda: "after", on_done=got.append)  # the worker survives
    assert w.wait_idle(5)
    background.pump()
    assert got == [None, "after"]
    assert any("background task failed" in r.message for r in caplog.records)


def test_ui_callback_exception_does_not_break_pump(caplog):
    w = background.Worker("gw2-test-uiexc")
    got = []

    def bad(_r):
        raise ValueError("x")

    w.submit(lambda: 1, on_done=bad)
    w.submit(lambda: 2, on_done=got.append)
    w.wait_idle(5)
    background.pump()
    assert got == [2]


def test_pump_is_cheap_when_empty():
    background.drain_all()
    t0 = time.perf_counter()
    for _ in range(10000):
        background.pump()
    assert time.perf_counter() - t0 < 0.5


def test_wait_idle_times_out_while_busy():
    w = background.Worker("gw2-test-busy")
    gate = threading.Event()
    w.submit(gate.wait)
    assert w.wait_idle(0.05) is False
    gate.set()
    assert w.wait_idle(5) is True


@pytest.mark.parametrize("n", [1, 50])
def test_drain_all_waits_for_chained_work(n):
    w = background.jobs  # drain_all only knows the module's own workers
    done = []

    def stage1(_r):  # a UI callback that queues more work
        w.submit(lambda: "second", on_done=done.append)

    w.submit(lambda: "first", on_done=stage1)
    background.drain_all()
    assert done == ["second"]

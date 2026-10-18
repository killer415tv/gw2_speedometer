"""Background workers so that slow network work never runs inside the Tk loop.

The 10 ms Tk callback (``updateMeterTimer``) is also the measurement loop, so
anything that blocks there (log upload ``join()``, ``pd.read_csv(<url>)``
without timeout, ``requests.get``, TCP ``connect``/``sendall``) shows up as a
gap in the samples.  This module gives that work somewhere else to run without
changing WHAT is sent or in WHICH ORDER:

* ``Worker`` = one daemon thread with a FIFO queue.  Tasks of one worker run
  strictly in submission order, one at a time.
* ``jobs``    - uploads, checkpoint downloads, ranking requests (so an upload is
  always sent before the ranking request that follows it).
* ``net_out`` - live telemetry (UDP/TCP/websocket) in the exact order produced.
* Results are handed back to the Tk thread through ``pump()`` (called by the Tk
  loop each tick, and by tests).  UI objects are only touched in ``pump()``.
"""

import atexit
import logging
import queue
import threading

log = logging.getLogger(__name__)

_ui_queue = queue.SimpleQueue()


class Worker:
    def __init__(self, name):
        self.name = name
        self._tasks = queue.SimpleQueue()
        self._thread = None
        self._start_lock = threading.Lock()
        self._cond = threading.Condition()
        self._pending = 0

    def submit(self, fn, *args, on_done=None):
        """Run ``fn(*args)`` on the worker thread; ``on_done(result)`` is queued
        for the UI thread (``pump``). Exceptions are logged, never raised;
        ``on_done`` then receives ``None``."""
        self._ensure_thread()
        with self._cond:
            self._pending += 1
        self._tasks.put((fn, args, on_done))

    def _ensure_thread(self):
        if self._thread is None:
            with self._start_lock:
                if self._thread is None:
                    t = threading.Thread(target=self._run, name=self.name, daemon=True)
                    t.start()
                    self._thread = t

    def _run(self):
        while True:
            fn, args, on_done = self._tasks.get()
            result = None
            try:
                result = fn(*args)
            except Exception:
                log.exception("background task failed (%s)", self.name)
            if on_done is not None:
                _ui_queue.put((on_done, result))
            with self._cond:
                self._pending -= 1
                self._cond.notify_all()

    def wait_idle(self, timeout=None):
        """Block until every submitted task finished. True if idle."""
        with self._cond:
            return self._cond.wait_for(lambda: self._pending == 0, timeout)

    @property
    def pending(self):
        return self._pending


jobs = Worker("gw2-jobs")
net_out = Worker("gw2-netout")
_workers = (jobs, net_out)


def pump():
    """Run queued UI callbacks. Call from the Tk thread only."""
    if _ui_queue.empty():
        return
    while True:
        try:
            fn, result = _ui_queue.get_nowait()
        except queue.Empty:
            return
        try:
            fn(result)
        except Exception:
            log.exception("UI callback failed")


def drain_all(timeout=30):
    """Wait for all workers and run all UI callbacks, until nothing is left
    (callbacks may submit more work). Used by tests and at exit."""
    while True:
        for w in _workers:
            w.wait_idle(timeout)
        pump()
        if _ui_queue.empty() and all(w.pending == 0 for w in _workers):
            return


def _finish_at_exit():
    # an upload that is still in flight when the app closes is given time to end
    for w in _workers:
        w.wait_idle(40)


atexit.register(_finish_at_exit)

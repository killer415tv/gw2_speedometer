"""Lap CSV writer used by the speedometer (competition logs, uploaded to
beetlerank.com).

Until now every CSV row was written with ``open(path, "a")`` + ``seek(0, 2)`` +
``write`` + implicit ``close`` (about 25 opens/s while racing; on Windows an
antivirus/indexer scan on each close shows up as latency inside the 10 ms Tk
sampling loop).  ``LapCsvWriter`` keeps ONE handle open per lap file and
flushes after every append, so:

* the bytes in the file are exactly the same (same mode, ``newline=""``,
  UTF-8 without BOM, same order; the caller still passes ``"\\r" + row`` and the
  header without terminator);
* after every ``append`` the data is already handed to the OS (a crash or a
  killed process loses nothing that the old code would have kept: the old code
  did not ``fsync`` either);
* the handle is closed when a lap ends, on reset, when the file changes, and at
  interpreter exit (``atexit``).
"""

import atexit
import threading


class LapCsvWriter:
    def __init__(self):
        self._lock = threading.Lock()
        self._key = None
        self._fh = None

    @property
    def is_open(self):
        return self._fh is not None

    def append(self, directory, filename, text):
        """Append ``text`` to ``directory/filename`` (created if missing)."""
        key = (directory, filename)
        with self._lock:
            if self._fh is None or self._key != key:
                self._close_locked()
                fh = open(directory / filename, "a", newline="", encoding="utf-8")  # noqa: SIM115 - kept open on purpose
                self._fh = fh
                self._key = key
            else:
                fh = self._fh
            try:
                fh.write(text)
                fh.flush()
            except BaseException:
                # Behave like the old per-row open/close: forget the handle so the
                # next row re-opens the file; the error still propagates.
                self._close_locked(ignore_errors=True)
                raise

    def close(self):
        """Close the current file, if any (idempotent)."""
        with self._lock:
            self._close_locked()

    def _close_locked(self, ignore_errors=False):
        fh, self._fh, self._key = self._fh, None, None
        if fh is not None:
            try:
                fh.close()
            except OSError:
                if not ignore_errors:
                    raise


# One writer per process: the speedometer has a single active lap file.
csv_log = LapCsvWriter()
atexit.register(csv_log.close)

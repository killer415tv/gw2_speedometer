# Golden data (measurement / CSV log / checkpoints)

Generated with `GOLDEN_UPDATE=1 python -m pytest tests/test_golden_measurement.py`
from the **unmodified** measurement code (commit `dddbafa`, before any phase-3
change). Each `<scenario>/files/` holds the exact bytes the app wrote
(`logs/*.csv`, `*_records.csv`) and `<scenario>/result.json` everything else that
is observable (per-tick CSV sizes on disk, uploads, multiplayer messages, key
presses, HUD texts, number of `time.time()` calls, final state...).

**Never regenerate them to make a change pass.** A mismatch means the change is
observable by beetlerank.com. Files are marked `-text` in `.gitattributes` so git
never rewrites their `\r` separators.

Generated with: CPython 3.12.15, numpy 1.26.4, pandas 2.3.3, scipy 1.17.1
(the project's pinned families: Python 3.12, `numpy<2`). The measurement maths
(`np.arctan2`, `np.degrees`, `scipy.spatial.distance.euclidean`) is evaluated by
those libraries, so a very different numpy/scipy build could in principle change
the last digit of an angle; the goldens answer "does *this code change* alter
the log", always compared in the same environment.

The harness drives the REAL `updateMeterTimer` / `checkpoint()` code of both
`Meterv2` and `Meter` (extracted with `ast`, no refactor), so the goldens
describe the code exactly as it ran before the optimisations. Besides the CSV
bytes they pin: the size of every log file after every tick (per-row
durability), the full-precision `velocity`/`pressedQ`/`next_step`/... state per
tick, every upload (URL, fields, headers, bytes), every multiplayer message,
every simulated key press and the number of `time.time()` calls.

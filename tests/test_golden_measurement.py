"""Golden tests: the CSV log, lap times and everything observable must stay
byte-for-byte identical for the same input sequence.

Run ``GOLDEN_UPDATE=1 python -m pytest tests/test_golden_measurement.py`` ONLY
to (re)create goldens from code known to be correct. The goldens in
``tests/golden/`` were generated from the unmodified phase-2 code (dddbafa);
optimisation commits must pass them untouched.
"""

import json
import os

import golden_harness as gh
import pytest
from golden_scenarios import SCENARIOS

pytestmark = pytest.mark.filterwarnings(
    "ignore:datetime.datetime.utcfromtimestamp:DeprecationWarning"
)

UPDATE = os.environ.get("GOLDEN_UPDATE") == "1"


def _run(name, tmp_path):
    return gh.run_scenario(SCENARIOS[name], tmp_path / "app")


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_golden(name, tmp_path):
    result, files = _run(name, tmp_path)
    if UPDATE:
        gh.write_golden(name, result, files)
        return
    exp_result, exp_files = gh.read_golden(name)
    # 1) the CSV files: same names, same BYTES
    assert sorted(files) == sorted(exp_files), "different set of files written"
    for rel in exp_files:
        assert files[rel] == exp_files[rel], "bytes differ in " + rel
    # 2) everything else observable (order within every channel included)
    got = gh.normalise(result)
    for key in sorted(exp_result):
        assert got[key] == exp_result[key], f"golden mismatch in section {key!r}"
    assert sorted(got) == sorted(exp_result)


def test_golden_files_exist_for_all_scenarios():
    for name in SCENARIOS:
        assert (gh.GOLDEN_DIR / name / "result.json").exists(), name


# ---- sanity: the goldens exercise the paths we care about (so that a golden
# ---- cannot be "identical" just because it recorded nothing) --------------
def _golden(name):
    return gh.read_golden(name)


def test_goldens_cover_key_paths():
    res, files = _golden("v2_1lap_3d_accel_q64")
    (csv_name,) = [r for r in files if r.endswith(".csv") and r.startswith("logs/")]
    raw = files[csv_name]
    text = raw.decode("utf-8")
    assert text.startswith(gh.HEADER + "\r")
    assert "\n" not in text and not text.endswith(
        "\r"
    )  # CR separators, no final terminator
    rows = [r.split(",") for r in text.split("\r")[1:]]
    assert len(rows) > 300 and all(len(r) == 9 for r in rows)
    speeds = [int(r[3]) for r in rows]
    assert 99 in speeds and max(speeds) < 150  # SPEED>=150 rows are filtered
    assert any(float(r[7]) != 0.0 for r in rows)  # acceleration column used
    assert any(float(r[4]) != 0.0 for r in rows)  # angles used
    assert (res["exceptions"], res["final_globals"]["filename"]) == ([], "''")

    res3, files3 = _golden("v2_3laps_upload_session_ws")
    assert len([r for r in files3 if r.startswith("logs/")]) == 3
    ups = res3["channels_full"]["uploads"]
    assert len(ups) == 3 and {u["url"] for u in ups} == {
        "https://www.beetlerank.com/upload-log"
    }
    assert [m["step"] for m in res3["mqtt_non_position"] if m["option"] == "f"] == [
        998,
        998,
        999,
    ]
    assert res3["mqtt_position"]["count"] > 100 and res3["websocket"]["count"] > 100
    assert len(res3["channels_full"]["save_guildhall"]) == 3

    res1, _ = _golden("v2_1lap_upload_message")
    assert len(res1["channels_full"]["message"]) == 1  # single lap: result shown

    resr, filesr = _golden("v2_reset_sphere_then_new_race")
    assert len([r for r in filesr if r.startswith("logs/")]) == 2
    assert 0 in resr["channels_full"]["save_checkpoint"]

    _resm, filesm = _golden("v2_manual_reset_then_new_race")
    assert len([r for r in filesm if r.startswith("logs/")]) == 2

    resd, filesd = _golden("v2_log_disabled")
    assert not [r for r in filesd if r.startswith("logs/")]
    assert resd["channels_full"]["uploads"] == []

    resv, _ = _golden("v1_session_unbound_map_angle")
    assert resv["exceptions"] and resv["exceptions"][0][1] == "UnboundLocalError"

    _rese, filese = _golden("v2_end_equals_start_2laps_debounce")
    assert len([r for r in filese if r.startswith("logs/")]) >= 1

    _resn, filesn = _golden("v2_no_checkpoints_loaded")
    assert not filesn


def test_golden_json_is_valid():
    for name in SCENARIOS:
        json.loads((gh.GOLDEN_DIR / name / "result.json").read_text(encoding="utf-8"))

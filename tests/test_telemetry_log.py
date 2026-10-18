"""LapCsvWriter must produce exactly the bytes of the old per-row open/close."""

import pathlib
import random
import subprocess
import sys

import pytest
from telemetry_log import LapCsvWriter, csv_log

HEADER = "X,Y,Z,SPEED,ANGLE_CAM,ANGLE_BEETLE,TIME,ACCELERATION,MAP_ANGLE"


def old_append(directory, filename, text_parts):
    """The code that used to run for every row (phase-2 speedometer.py)."""
    with open(directory / filename, "a", newline="", encoding="utf-8") as writer:
        writer.seek(0, 2)
        for part in text_parts:
            writer.writelines(part)


def rows(rnd, n):
    out = []
    for _ in range(n):
        out.append(
            ",".join(
                [
                    str(round(rnd.uniform(-5000, 5000) * 10000) / 10000),
                    str(round(rnd.uniform(0, 500) * 10000) / 10000),
                    str(round(rnd.uniform(-5000, 5000) * 10000) / 10000),
                    str(rnd.randrange(0, 150)),
                    "0.0",
                    "-3.21",
                    str(rnd.uniform(0, 100)),
                    "0.0",
                    "181.5",
                ]
            )
        )
    return out


def test_bytes_identical_to_old_per_row_open_close(tmp_path):
    rnd = random.Random(7)
    old_dir, new_dir = tmp_path / "old", tmp_path / "new"
    old_dir.mkdir()
    new_dir.mkdir()
    w = LapCsvWriter()
    for lap_file in ("Map_log_1.5.csv", "Map_log_2.25.csv"):
        old_append(old_dir, lap_file, [HEADER])
        w.append(new_dir, lap_file, HEADER)
        for r in rows(rnd, 200):
            old_append(old_dir, lap_file, ["\r", r])
            w.append(new_dir, lap_file, "\r" + r)
            # per-row durability: what is on disk after every append is final
            assert (new_dir / lap_file).stat().st_size == (
                old_dir / lap_file
            ).stat().st_size
    w.close()
    for name in ("Map_log_1.5.csv", "Map_log_2.25.csv"):
        a, b = (old_dir / name).read_bytes(), (new_dir / name).read_bytes()
        assert a == b
        assert (
            a.startswith(HEADER.encode() + b"\r")
            and b"\n" not in a
            and not a.endswith(b"\r")
        )


def test_non_ascii_names_and_utf8_no_bom(tmp_path):
    w = LapCsvWriter()
    w.append(tmp_path, "Ñandú_log_1.csv", "é,ü")
    w.close()
    assert (tmp_path / "Ñandú_log_1.csv").read_bytes() == "é,ü".encode()


def test_appends_to_existing_file_and_creates_missing_file(tmp_path):
    f = tmp_path / "a.csv"
    f.write_bytes(b"old")
    w = LapCsvWriter()
    w.append(tmp_path, "a.csv", "\rnew")
    w.append(tmp_path, "b.csv", "x")  # switching files closes the previous one
    assert f.read_bytes() == b"old\rnew"
    assert (tmp_path / "b.csv").read_bytes() == b"x"
    w.close()
    w.close()  # idempotent
    assert not w.is_open


def test_switching_file_closes_previous_handle(tmp_path):
    w = LapCsvWriter()
    w.append(tmp_path, "a.csv", "1")
    first = w._fh
    w.append(tmp_path, "b.csv", "2")
    assert first.closed and not w._fh.closed
    w.close()


def test_reopens_after_close_like_a_new_lap(tmp_path):
    w = LapCsvWriter()
    w.append(tmp_path, "a.csv", "1")
    w.close()
    w.append(tmp_path, "a.csv", "2")
    w.close()
    assert (tmp_path / "a.csv").read_bytes() == b"12"


def test_write_error_drops_handle_and_recovers(tmp_path):
    w = LapCsvWriter()
    w.append(tmp_path, "a.csv", "1")
    w._fh.close()  # simulate a broken handle
    with pytest.raises(ValueError):
        w.append(tmp_path, "a.csv", "2")
    assert not w.is_open
    w.append(tmp_path, "a.csv", "3")  # next row re-opens, like the old code
    w.close()
    assert (tmp_path / "a.csv").read_bytes() == b"13"


def test_data_survives_killed_process_without_close(tmp_path):
    """No atexit, no close: the process is killed right after the last append."""
    here = pathlib.Path(__file__).resolve().parent.parent / "gw2_speedometer_internal"
    code = (
        f"import sys, os, pathlib; sys.path.insert(0, {str(here)!r})\n"
        "from telemetry_log import csv_log\n"
        f"d = pathlib.Path({str(tmp_path)!r})\n"
        "csv_log.append(d, 'k.csv', 'H')\n"
        "for i in range(5): csv_log.append(d, 'k.csv', '\\r' + str(i))\n"
        "os._exit(9)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], check=False)
    assert r.returncode == 9
    assert (tmp_path / "k.csv").read_bytes() == b"H\r0\r1\r2\r3\r4"


def test_closed_at_normal_exit(tmp_path):
    here = pathlib.Path(__file__).resolve().parent.parent / "gw2_speedometer_internal"
    code = (
        f"import sys, pathlib; sys.path.insert(0, {str(here)!r})\n"
        "from telemetry_log import csv_log\n"
        f"csv_log.append(pathlib.Path({str(tmp_path)!r}), 'k.csv', 'abc')\n"
    )
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0
    assert (tmp_path / "k.csv").read_bytes() == b"abc"


def test_module_singleton_exists():
    assert isinstance(csv_log, LapCsvWriter)

"""Linux/offline compatibility helpers (run on every OS)."""
import json
import os

import platform_compat
import mumblelink
from mumblelink import Link, Context, MumbleLink, get_identity_name, get_identity_fov
import mumblelink_linux as ml_linux


def test_simulate_requested_flag_and_env(monkeypatch):
    monkeypatch.delenv("GW2_SIMULATE", raising=False)
    monkeypatch.setattr(platform_compat.sys, "argv", ["x.py"])
    assert not platform_compat.simulate_requested()
    monkeypatch.setattr(platform_compat.sys, "argv", ["x.py", "--simulate"])
    assert platform_compat.simulate_requested()
    monkeypatch.setattr(platform_compat.sys, "argv", ["x.py"])
    monkeypatch.setenv("GW2_SIMULATE", "1")
    assert platform_compat.simulate_requested()


def test_struct_sizes_match_mumble_layout():
    # uiTick must be 4 bytes also on Linux (ctypes.c_ulong is 8 there)
    assert Link.uiTick.size == 4
    assert Link.fAvatarPosition.offset == 8
    assert Link.name.size == 512 if platform_compat.IS_WINDOWS else True
    assert Context.mapId.offset == 28


def test_simulated_memfile_roundtrip(monkeypatch):
    monkeypatch.setenv("GW2_SIMULATE", "1")
    ml = MumbleLink()
    ml.read()
    assert ml.data.uiVersion == 2
    assert ml.context.mapId == ml_linux.MAP_ID
    assert get_identity_name(ml) == ml_linux.CHARACTER
    assert get_identity_fov(ml) == 0.873
    assert any(abs(v) > 1 for v in ml.data.fAvatarPosition)


def test_simulated_car_moves_on_the_ellipse():
    mem = ml_linux.SimulatedMemfile(5000)
    import struct
    pos = []
    for _ in range(2):
        mem.seek(0)
        pos.append(struct.unpack("<3f", mem.read(1108)[8:20]))
    for x, y, z in pos:
        assert abs((x / ml_linux.SEMI_A) ** 2 + (z / ml_linux.SEMI_B) ** 2 - 1) < 0.01


def test_circuit_rows_are_a_valid_checkpoint_list():
    rows = ml_linux.circuit_rows()
    assert rows[0][1] == "start" and rows[-1][1] == "end"
    assert [r[0] for r in rows] == list(range(len(rows)))


def test_open_shm_memfile_creates_and_grows(tmp_path):
    path = tmp_path / "MumbleLink.test"
    mem = ml_linux.open_shm_memfile(str(path), 4096)
    assert os.path.getsize(path) == 4096
    mem.close()

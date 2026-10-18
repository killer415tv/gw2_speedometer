"""MumbleLink only exists on Windows: mmap is replaced by a fake here."""
import json

import pytest

import mumblelink
from mumblelink import (
    Context,
    Link,
    MumbleLink,
    get_identity_fov,
    get_identity_name,
    parse_identity,
)


class FakeMem:
    """Minimal mmap stand-in backed by bytes."""

    def __init__(self, content=b"", fail=None):
        self.content = content
        self.pos = 0
        self.fail = fail

    def seek(self, pos):
        if self.fail:
            raise self.fail
        self.pos = pos

    def read(self, n):
        chunk = self.content[self.pos:self.pos + n]
        self.pos += n
        return chunk.ljust(n, b"\0")

    def close(self):
        pass


def make_ml(monkeypatch, mem):
    monkeypatch.setattr(mumblelink.mmap, "mmap", lambda **kw: mem)
    return MumbleLink()


def game_bytes(identity, tick=5, x=1.0, y=2.0, z=3.0):
    link = Link()
    link.uiVersion = 2
    link.uiTick = tick
    link.fAvatarPosition[0], link.fAvatarPosition[1], link.fAvatarPosition[2] = x, y, z
    link.identity = identity
    ctx = Context()
    ctx.mapId = 1155
    return bytes(link) + bytes(ctx)


@pytest.mark.parametrize("raw", ["", None, "   ", "not json", "[1]", "3", "null", b"{}", 5])
def test_parse_identity_never_raises(raw):
    assert parse_identity(raw) == {}


def test_parse_identity_ok():
    raw = json.dumps({"name": "Beetle Boy", "fov": 0.9})
    assert parse_identity(raw) == {"name": "Beetle Boy", "fov": 0.9}


def test_game_closed_zero_memory(monkeypatch):
    ml = make_ml(monkeypatch, FakeMem(b""))
    # data exists even before the first read (no AttributeError)
    assert ml.data.uiVersion == 0 and ml.data.identity == ""
    ml.read()
    assert ml.data.uiVersion == 0
    assert get_identity_name(ml) == ""
    assert get_identity_name(ml, "anon") == "anon"
    assert get_identity_fov(ml) is None


def test_game_running(monkeypatch):
    ident = json.dumps({"name": "Beetle Boy", "fov": 0.8})
    ml = make_ml(monkeypatch, FakeMem(game_bytes(ident)))
    ml.read()
    assert ml.data.uiVersion == 2
    assert ml.context.mapId == 1155
    assert list(ml.data.fAvatarPosition) == [1.0, 2.0, 3.0]
    assert get_identity_name(ml) == "Beetle Boy"
    assert get_identity_fov(ml) == 0.8


def test_half_written_identity_does_not_crash(monkeypatch):
    ml = make_ml(monkeypatch, FakeMem(game_bytes('{"name": "Bee')))
    ml.read()
    assert get_identity_name(ml, "anon") == "anon"
    assert get_identity_fov(ml) is None


def test_closed_memory_keeps_last_data_and_does_not_raise(monkeypatch):
    mem = FakeMem(game_bytes(json.dumps({"name": "A"}), tick=7))
    ml = make_ml(monkeypatch, mem)
    ml.read()
    assert ml.data.uiTick == 7
    mem.fail = ValueError("mmap closed or invalid")
    ml.read()  # must not raise
    ml.read()
    assert ml.data.uiTick == 7
    assert ml._read_failed is True
    mem.fail = None
    ml.read()
    assert ml._read_failed is False


def test_helpers_accept_object_without_data():
    class Empty:
        pass

    assert get_identity_name(Empty(), "x") == "x"
    assert get_identity_fov(Empty(), 1.0) == 1.0

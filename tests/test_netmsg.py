import json

import pytest

import netmsg


def test_parse_payload_ok_bytes_and_str():
    assert netmsg.parse_payload(b'{"option": "s"}') == {"option": "s"}
    assert netmsg.parse_payload('{"option": "s"}') == {"option": "s"}


@pytest.mark.parametrize("bad", [None, b"", b"not json", b"\xff\xfe", "[1,2]", "42", '"x"', "null"])
def test_parse_payload_rejects_garbage(bad):
    assert netmsg.parse_payload(bad) is None


def test_valid_start():
    out = netmsg.validate_race_message({"option": "s", "user": "ana", "time": 12.5, "lap": 1})
    assert out == {"option": "s", "user": "ana", "time": 12.5, "lap": 1}


def test_valid_checkpoint_and_finish_normalise_ints():
    out = netmsg.validate_race_message(
        {"option": "c", "user": "ana", "time": 3, "lap": "2", "step": 7.0}
    )
    assert out["lap"] == 2 and out["step"] == 7 and isinstance(out["step"], int)
    out = netmsg.validate_race_message(
        {"option": "f", "user": "ana", "time": 3.2, "lap": 1, "step": 999}
    )
    assert out["step"] == 999


@pytest.mark.parametrize(
    "msg",
    [
        {"option": "c", "user": "ana", "time": 1, "lap": 1},  # no step
        {"option": "c", "user": "ana", "time": 1, "lap": 1, "step": None},
        {"option": "c", "user": "ana", "time": 1, "lap": 1, "step": "abc"},
        {"option": "c", "user": "ana", "time": "1", "lap": 1, "step": 1},  # time str
        {"option": "c", "user": None, "time": 1, "lap": 1, "step": 1},
        {"option": "c", "user": 5, "time": 1, "lap": 1, "step": 1},
        {"option": "c", "user": "a", "time": True, "lap": 1, "step": 1},
        {"option": "s", "user": "a", "time": 1, "lap": None},
        {"option": "s", "user": "a", "time": 1},
        {"option": 3},
        {},
        [],
        "x",
        None,
    ],
)
def test_invalid_messages_rejected(msg):
    assert netmsg.validate_race_message(msg) is None


def test_countdown_and_unknown_options():
    assert netmsg.validate_race_message({"option": "321GO-3"}) == {"option": "321GO-3"}
    assert netmsg.validate_race_message({"option": "321GO-custom", "message": 5}) == {
        "option": "321GO-custom",
        "message": "5",
    }
    assert netmsg.validate_race_message({"option": "321GO-custom"})["message"] == ""
    assert netmsg.validate_race_message({"option": "position", "x": 1})["option"] == "position"


def test_parse_countdown_start():
    ok = json.dumps({"type": "countdown_start", "ends_on": 1760000000000})
    assert netmsg.parse_countdown_start(ok) == 1760000000000
    assert netmsg.parse_countdown_start(json.dumps({"type": "countdown_start"})) is None
    assert netmsg.parse_countdown_start(json.dumps({"type": "countdown_start", "ends_on": "x"})) is None
    assert netmsg.parse_countdown_start(json.dumps({"type": "other", "ends_on": 1})) is None
    assert netmsg.parse_countdown_start("garbage") is None

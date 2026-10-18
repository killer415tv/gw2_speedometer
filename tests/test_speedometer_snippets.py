"""speedometer.py cannot be imported on Linux (Tk root + windll at import time).
These tests extract individual functions from the source with ast and run them
with mocks, which is enough to check the behaviour that matters here."""
import ast
import pathlib
import textwrap

import pytest
import requests

import mumblelink

INTERNAL = pathlib.Path(__file__).resolve().parent.parent / "gw2_speedometer_internal"


def extract(filename, name, nth=0, in_class=None):
    src = (INTERNAL / filename).read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            found.append(node)
    node = sorted(found, key=lambda n: n.lineno)[nth]
    code = textwrap.dedent(ast.get_source_segment(src, node))
    return code


class FakeML:
    class data:  # noqa: N801
        identity = '{"name": "Beetle Boy", "fov": 1}'


class Recorder:
    def __init__(self, raise_exc=None):
        self.calls = []
        self.raise_exc = raise_exc

    def post(self, url, **kw):
        # read the multipart body exactly as requests would build it
        f = kw["files"]["file"]
        kw["_content"] = f.read()
        kw["_file_obj"] = f
        kw["_file_name"] = f.name
        self.calls.append((url, kw))
        if self.raise_exc:
            raise self.raise_exc

        class R:
            text = "OK"

        return R()


def make_upload(tmp_path, rec, which=0):
    code = extract("speedometer.py", "uploadLog", which)
    ns = {
        "requests": rec,
        "APP_DIR": tmp_path,
        "UPLOAD_TIMEOUT": (5, 30),
        "get_identity_name": mumblelink.get_identity_name,
    }
    rec.RequestException = requests.RequestException
    ns["requests"] = type("R", (), {"post": rec.post, "RequestException": requests.RequestException})
    exec(code, ns)
    return ns["uploadLog"]


@pytest.mark.parametrize("which", [0, 1])  # both copies (Racer-era Meter classes)
def test_upload_sends_same_fields_and_closes_file(tmp_path, which):
    (tmp_path / "logs").mkdir()
    content = b"X,Y,Z,SPEED\n1,2,3,4\n"
    (tmp_path / "logs" / "Rata River_log_1.csv").write_bytes(content)
    rec = Recorder()
    upload = make_upload(tmp_path, rec, which)
    out = upload(None, "Rata River", "Rata River_log_1.csv", FakeML)
    assert out == "OK"
    url, kw = rec.calls[0]
    assert url == "https://www.beetlerank.com/upload-log"
    assert kw["data"] == {"user": "Beetle Boy", "guildhall": "Rata River"}
    assert set(kw["files"]) == {"file"}
    assert kw["headers"] == {"Origin": "null", "Referer": "null"}
    assert kw["_content"] == content
    assert kw["timeout"] == (5, 30)
    assert pathlib.Path(kw["_file_name"]).name == "Rata River_log_1.csv"
    assert kw["_file_obj"].closed  # closed by the 'with'


def test_upload_survives_network_error_and_closes_file(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "a.csv").write_bytes(b"x")
    rec = Recorder(raise_exc=requests.ConnectionError("down"))
    out = make_upload(tmp_path, rec)(None, "m", "a.csv", FakeML)
    assert out == ""
    assert rec.calls[0][1]["_file_obj"].closed


def test_upload_missing_file_and_missing_identity(tmp_path):
    (tmp_path / "logs").mkdir()
    rec = Recorder()
    up = make_upload(tmp_path, rec)
    assert up(None, "m", "nope.csv", FakeML) == ""

    class Closed:
        class data:  # noqa: N801
            identity = ""

    (tmp_path / "logs" / "a.csv").write_bytes(b"x")
    assert up(None, "m", "a.csv", Closed) == ""
    assert rec.calls == []  # nothing uploaded without a character name


def test_map_script_argv_parsing():
    code = extract("map_realtime_multiplayer.py", "_parse_argv")
    ns = {}
    exec(code, ns)
    parse = ns["_parse_argv"]
    assert parse([]) == (None, None)
    assert parse(["--room", "1234"]) == ("1234", None)
    assert parse(["--room", "1234", "my.csv"]) == ("1234", "my.csv")
    assert parse(["my.csv"]) == (None, "my.csv")
    assert parse(["--room"]) == (None, None)


def test_no_sys_argv0_path_mixing_left_in_speedometer():
    src = (INTERNAL / "speedometer.py").read_text(encoding="utf-8")
    assert "sys.argv[0]" not in src
    assert '"python",' not in src
    assert "APP_DIR = Path(__file__).resolve().parent" in src


def test_all_requests_get_use_headers_kw_and_timeout():
    for py in INTERNAL.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("get", "post")
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "requests"
            ):
                kws = {k.arg for k in node.keywords}
                assert "timeout" in kws, f"{py.name}:{node.lineno} without timeout"
                assert len(node.args) == 1, f"{py.name}:{node.lineno} positional headers?"


def test_race_handler_source_uses_validation():
    code = extract("speedometer.py", "_handle_race_message")
    assert "netmsg.validate_race_message" in code


def test_multipart_body_identical_for_relative_and_absolute_log_path(tmp_path, monkeypatch):
    """The uploaded multipart (field names, filename, content) must not depend on
    whether the log path is relative (old: Path(sys.argv[0]).parent) or absolute."""
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "Rata River_log_1.csv").write_bytes(b"X,Y\n1,2\n")
    monkeypatch.chdir(tmp_path)

    def body(path):
        with open(path, "rb") as fh:
            req = requests.Request(
                "POST",
                "https://www.beetlerank.com/upload-log",
                data={"user": "Beetle Boy", "guildhall": "Rata River"},
                files={"file": fh},
                headers={"Origin": "null", "Referer": "null"},
            ).prepare()
        boundary = req.headers["Content-Type"].split("boundary=")[1]
        return req.body.replace(boundary.encode(), b"BOUNDARY")

    rel = body(pathlib.Path(".") / "logs" / "Rata River_log_1.csv")
    absolute = body(logs.resolve() / "Rata River_log_1.csv")
    assert rel == absolute
    assert b'name="file"; filename="Rata River_log_1.csv"' in absolute


def _race_handler_env():
    import json
    import logging
    import queue

    import netmsg

    ns = {"netmsg": netmsg, "logging": logging, "countdowntxt": "old"}
    exec(extract("speedometer.py", "_handle_race_message"), ns)
    exec(extract("speedometer.py", "on_message_MQTT"), ns)

    class Self:
        timestamps = []
        thread_queue = queue.Queue()
        _handle_race_message = ns["_handle_race_message"]

    me = Self()
    me.timestamps = []
    me.thread_queue = queue.Queue()

    class Msg:
        def __init__(self, payload):
            self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def send(payload):
        ns["on_message_MQTT"](me, None, None, Msg(payload))

    return ns, me, send


def test_handler_valid_flow_matches_old_behaviour():
    ns, me, send = _race_handler_env()
    send({"option": "321GO-3"})
    assert ns["countdowntxt"] == "3" and me.thread_queue.get_nowait() == "3"
    send({"option": "s", "user": "ana", "time": 1.5, "lap": 1})
    assert me.timestamps == [{"user": "ana", "time": 1.5, "step": 0, "lap": 1}]
    assert ns["countdowntxt"] == ""
    send({"option": "c", "user": "ana", "time": 2.5, "step": 3, "lap": 1})
    send({"option": "f", "user": "ana", "time": 9.5, "step": 999, "lap": 1})
    assert me.timestamps[-1] == {"user": "ana", "time": 9.5, "step": 999, "lap": 1}
    assert me.thread_queue.get_nowait() == "Race positions"
    assert me.thread_queue.get_nowait() == "Race finished\nPositions:"
    # surrender (step >= 1000) removes previous entries of that user first
    send({"option": "c", "user": "ana", "time": 0, "step": 1000, "lap": 1})
    assert me.timestamps == [{"user": "ana", "time": 0, "step": 1000, "lap": 1}]
    send({"option": "321GO-custom", "message": "Ready?"})
    assert ns["countdowntxt"] == "Ready?" and me.timestamps == []
    send({"option": "321GO-GO"})
    assert ns["countdowntxt"] == "GOGOGO! FAEST!"


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\xff\xfe",
        b"[]",
        {"option": "c", "user": "ana", "time": 1, "lap": 1},  # no step
        {"option": "c", "user": "ana", "time": 1, "lap": 1, "step": None},
        {"option": "c", "user": None, "time": 1, "lap": 1, "step": 1},
        {"option": "s", "user": "ana", "time": "x", "lap": 1},
        {"option": "f"},
        {"option": ["x"]},
        {"nothing": 1},
    ],
)
def test_handler_ignores_malformed_without_raising_or_polluting(payload):
    ns, me, send = _race_handler_env()
    send(payload)  # must not raise
    assert me.timestamps == [] and me.thread_queue.empty()

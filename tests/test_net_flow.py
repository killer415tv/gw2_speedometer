"""Order and content of the network traffic around the end of a race, with the
real Racer.saveGuildhall / Meter code running in the golden harness namespace."""

import http.server
import pathlib
import threading
import types

import checkpoint_cache
import golden_harness as gh
import pandas as pd
import pytest
from golden_harness import Var, circuit, make_ticks
from golden_scenarios import ACCEL_3D, PLAIN_2D


def _frame():
    return gh.load_map(gh.MAP_STANDARD)


class NetFakes:
    """Records, in one list, every network call in the order it was made."""

    def __init__(self, rec, fail_checkpoints=False, fail_ranking=False):
        self.rec = rec
        self.fail_checkpoints = fail_checkpoints
        self.fail_ranking = fail_ranking

    def log(self, item):
        self.rec.add("net_order", item)

    def fetch(self, source, *a, **k):
        self.log(["GET checkpoints", str(source)])
        if self.fail_checkpoints:
            raise OSError("down")
        return _frame()


def make_scenario(
    laps,
    upload=1,
    session_id="",
    fail_checkpoints=False,
    fail_ranking=False,
    cup="TESTCUP",
):
    holder = {}

    def racer_factory(ns, rec, workdir):
        Racer = ns["Racer"]
        r = Racer.__new__(Racer)
        r.root = gh.FakeRoot(rec)
        r.session_id = Var(rec, "session_id", session_id, "racer_vars")
        r.username = Var(rec, "username", "", "username_sets")
        r.map_ranking_var = Var(rec, "map_ranking", "", "ranking_var")
        return r

    def hook(ns, rec, workdir):
        net = NetFakes(rec, fail_checkpoints, fail_ranking)
        holder["net"] = net
        real_post = ns["requests"].post

        def post(url, **kw):
            net.log(["POST", url])
            return real_post(url, **kw)

        def get(url, **kw):
            net.log(["GET", url, kw.get("headers"), kw.get("timeout")])
            if fail_ranking:
                raise OSError("down")
            return types.SimpleNamespace(text="RANK-OK")

        import requests as real_requests

        fake = types.SimpleNamespace(
            post=post,
            get=get,
            utils=real_requests.utils,
            RequestException=real_requests.RequestException,
        )
        ns["requests"] = fake
        ns["checkpoint_cache"] = types.SimpleNamespace(
            rows_for=checkpoint_cache.rows_for, fetch_checkpoint_frame=net.fetch
        )
        ns["cup_name"].value = cup
        (workdir / "maps").mkdir(exist_ok=True)
        (workdir / "maps" / "Test Race.csv").write_text(gh.MAP_STANDARD, newline="")

    sc = gh.Scenario(
        f"netflow_{laps}",
        laps=laps,
        upload=upload,
        settings=PLAIN_2D if laps == 1 else ACCEL_3D,
        ticks=make_ticks(circuit(laps), seed=30 + laps, clock="q64"),
        racer_factory=racer_factory,
        namespace_hook=hook,
    )
    return sc


@pytest.mark.parametrize("laps", [1, 2])
def test_upload_fields_and_result_message(tmp_path, laps):
    result, files = gh.run_scenario(make_scenario(laps), tmp_path / "app")
    assert result["exceptions"] == []
    ups = result["channels_full"]["uploads"]
    assert len(ups) == laps
    assert all(u["url"] == "https://www.beetlerank.com/upload-log" for u in ups)
    assert all(u["headers"] == {"Origin": "null", "Referer": "null"} for u in ups)
    assert all(
        u["data"] == {"user": "Beetle Boy", "guildhall": "Test Race"} for u in ups
    )
    names = sorted(pathlib.Path(r).name for r in files if r.startswith("logs/"))
    # the result text is shown only for single-lap races, as before
    assert result["channels_full"]["message"] == (
        ["UPLOAD-OK:" + names[0]] if laps == 1 else []
    )


def collect_channels(sc, tmp_path):
    """Run and also return the raw recorder channels (net_order, ranking...)."""
    captured = {}
    orig = gh.Recorder

    class Spy(orig):
        def __init__(self):
            super().__init__()
            captured["rec"] = self

    gh.Recorder = Spy
    try:
        result, files = gh.run_scenario(sc, tmp_path / "app")
    finally:
        gh.Recorder = orig
    return captured["rec"].channels, result, files


@pytest.mark.parametrize("laps", [1, 2])
def test_network_call_order(tmp_path, laps):
    ch, result, _files = collect_channels(make_scenario(laps), tmp_path)
    order = [e[:2] for e in ch["net_order"]]
    one = [
        ["POST", "https://www.beetlerank.com/upload-log"],
        [
            "GET checkpoints",
            "https://www.beetlerank.com/uploads/checkpoints/Test%20Race.csv",
        ],
        ["GET", "https://www.beetlerank.com/rank/api/Test Race/Beetle Boy"],
    ]
    # one POST -> checkpoint download -> ranking group per finished lap, in this order
    assert order == one * laps
    ranking = [e for e in ch["net_order"] if e[0] == "GET"]
    assert all(e[2] == {"Origin": "null", "Referer": "null"} for e in ranking)
    assert ch["ranking_var"] == [["map_ranking", "RANK-OK"]] * laps
    assert result["exceptions"] == []
    assert (tmp_path / "app" / "guildhall.txt").read_text(
        encoding="utf-8"
    ) == "Test Race"


def test_failed_checkpoint_download_empties_list_like_before(tmp_path):
    """Original behaviour (kept on purpose, see docs/PROBLEMAS_MEDICION.md): a
    failed re-download leaves an EMPTY checkpoint list."""
    holder = {}

    def hook_outer(ns, rec, workdir):
        holder["ns"] = ns

    sc = make_scenario(1, fail_checkpoints=True)
    inner = sc.namespace_hook

    def hook(ns, rec, workdir):
        inner(ns, rec, workdir)
        holder["ns"] = ns

    sc.namespace_hook = hook
    ch, _result, _files = collect_channels(sc, tmp_path)
    assert len(holder["ns"]["checkpoints_list"]) == 0
    assert ch["ranking_var"] == [
        ["map_ranking", "RANK-OK"]
    ]  # ranking is still requested


def test_stale_background_load_is_dropped_if_map_changed(tmp_path):
    rec = gh.Recorder()
    ns = gh.build_namespace()
    ns["APP_DIR"] = tmp_path
    ns["guildhall_name"] = Var(rec, "g", "Map B", "g")
    ns["cup_name"] = Var(rec, "c", "TESTCUP", "c")
    ns["keyboard_"] = gh.FakeKeyboard(rec)
    ns["checkpoints_list"] = ["sentinel"]
    ns["tmhud"] = gh.FakeMessage(rec, "t")
    Racer = ns["Racer"]
    r = Racer.__new__(Racer)
    r.map_ranking_var = Var(rec, "r", "", "r")
    r.username = Var(rec, "u", "me", "u")
    r._finish_saveGuildhall("Map A", ("ok", _frame()))  # user already switched to Map B
    assert ns["checkpoints_list"] == ["sentinel"]
    assert rec.channels == {}
    assert not (tmp_path / "guildhall.txt").exists()


# ---- fetch_checkpoint_frame vs pandas on a real local HTTP server ---------
class _Handler(http.server.BaseHTTPRequestHandler):
    seen = []  # noqa: RUF012
    body = gh.MAP_STANDARD.encode()
    delay = 0.0

    def do_GET(self):
        _Handler.seen.append(dict(self.headers.items()) | {"path": self.path})
        if _Handler.delay:
            import time

            time.sleep(_Handler.delay)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Length", str(len(self.body)))
            self.end_headers()
            self.wfile.write(self.body)
        except (BrokenPipeError, ConnectionResetError):  # client timed out
            pass

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    _Handler.seen = []
    _Handler.delay = 0.0
    yield f"http://127.0.0.1:{srv.server_address[1]}/uploads/checkpoints/Test%20Race.csv"
    srv.shutdown()
    srv.server_close()


def test_fetch_is_same_request_and_same_frame_as_pandas(server):
    via_pandas = pd.read_csv(server)
    pandas_headers = _Handler.seen.pop()
    mine = checkpoint_cache.fetch_checkpoint_frame(server)
    my_headers = _Handler.seen.pop()
    pd.testing.assert_frame_equal(via_pandas, mine)
    assert (
        my_headers == pandas_headers
    )  # User-Agent, Accept-Encoding, path... all equal
    assert gh.load_map(gh.MAP_STANDARD).equals(
        pd.concat([pd.DataFrame(), mine], ignore_index=True)
    )


def test_fetch_times_out_instead_of_hanging(server):
    _Handler.delay = 1.0
    with pytest.raises(OSError):
        checkpoint_cache.fetch_checkpoint_frame(server, timeout=0.2)


def test_fetch_local_path_is_plain_read_csv(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text(gh.MAP_STANDARD, newline="")
    pd.testing.assert_frame_equal(
        checkpoint_cache.fetch_checkpoint_frame(p), pd.read_csv(p)
    )

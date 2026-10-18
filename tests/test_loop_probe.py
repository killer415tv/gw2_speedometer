import importlib
import subprocess
import sys

import loop_probe


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_disabled_by_default_and_noop(tmp_path, monkeypatch):
    monkeypatch.delenv("GW2_SPEEDOMETER_PROBE", raising=False)
    mod = importlib.reload(loop_probe)
    assert not mod.enabled()
    t0 = mod.begin()
    mod.end(t0)  # must not raise, must not create anything
    assert t0 == 0.0
    assert not (mod.default_dir() / "x").exists()


def test_import_without_env_leaves_probe_disabled():
    folder = str(loop_probe.pathlib.Path(loop_probe.__file__).parent)
    code = f"import sys; sys.path.insert(0, {folder!r}); import loop_probe; print(loop_probe.enabled())"
    env = {"PATH": "", "SYSTEMROOT": ""}
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert out.stdout.split()[0] == "False"  # not enabled without the env var


def test_probe_measures_interval_duration_and_missed(tmp_path):
    clk = Clock()
    p = loop_probe.LoopProbe(out_dir=tmp_path, clock=clk, start_thread=False, epoch=1)
    # (gap before the call, call duration)
    plan = [(0.0, 0.002), (0.016, 0.003), (0.016, 0.001), (0.100, 0.020), (0.039, 0.0)]
    for gap, dur in plan:
        clk.t += gap
        t0 = p.begin()
        clk.t += dur
        p.end(t0)
    p.close()
    rows = p.path.read_text().strip().split("\n")
    assert rows[0] == "tick,t_s,interval_ms,duration_ms,missed_updates_est"
    cells = [r.split(",") for r in rows[1:]]
    # interval = time between the START of consecutive calls (gap + previous duration)
    assert [c[2] for c in cells] == ["", "18.000", "19.000", "101.000", "59.000"]
    assert [c[4] for c in cells] == ["0", "0", "0", "2", "1"]
    assert [c[3] for c in cells] == ["2.000", "3.000", "1.000", "20.000", "0.000"]
    summary = p.summary_path.read_text()
    assert "ticks: 5" in summary and "gaps_over_40ms: 2" in summary
    assert "missed_updates_est (sum of ceil(interval/40ms)-1): 3" in summary
    # the competition log folder is never touched
    assert p.path.parent == tmp_path


def test_enable_disable_module_level(tmp_path):
    p = loop_probe.enable(tmp_path, start_thread=False)
    try:
        assert loop_probe.enabled()
        t0 = loop_probe.begin()
        loop_probe.end(t0)
    finally:
        loop_probe.disable()
    assert not loop_probe.enabled()
    assert p.path.exists() and p.summary_path.exists()


def test_golden_identical_with_probe_enabled(tmp_path):
    """Turning the probe on must not change a single observable byte."""
    import golden_harness as gh
    from golden_scenarios import SCENARIOS

    name = "v2_1lap_3d_accel_q64"
    probe = loop_probe.enable(tmp_path / "diag", start_thread=False)
    try:
        result, files = gh.run_scenario(SCENARIOS[name], tmp_path / "app")
    finally:
        loop_probe.disable()
    exp_result, exp_files = gh.read_golden(name)
    assert files == exp_files
    assert gh.normalise(result) == exp_result
    assert probe.path.read_text().count("\n") == SCENARIOS[name].ticks.__len__() + 1
    assert not any("diag" in rel for rel in files)  # nothing in the app/logs tree

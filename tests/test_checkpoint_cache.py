import io
import random

import checkpoint_cache
import numpy as np
import pandas as pd
import pytest


def old_rows(frame):
    """What the old per-sample loop handed to checkpoint(), one tuple per row."""
    out = []
    for _index, checkpoint_data in frame.iterrows():
        if "RADIUS" in checkpoint_data:
            radius = checkpoint_data["RADIUS"]
        else:
            radius = 0
        out.append(
            (
                checkpoint_data["STEP"],
                checkpoint_data["STEPNAME"],
                [checkpoint_data["X"], checkpoint_data["Y"], checkpoint_data["Z"]],
                radius,
            )
        )
    return out


def load(text):
    return pd.concat(
        [pd.DataFrame(), pd.read_csv(io.StringIO(text))], ignore_index=True
    )


MAPS = [
    "STEP,STEPNAME,X,Y,Z,RADIUS\r0,start,1.5,2.5,3.5,0\r1,*,10.25,0.0,-4.0,20\r2,end,7.0,8.0,9.0,15.5\r",
    "STEP,STEPNAME,X,Y,Z,RADIUS,ANGLE\r0,start,1,2,3,0,0.0\r-1,reset,5,6,7,0,0.0\r",
    "STEP,STEPNAME,X,Y,Z\r4,end,1.0,2.0,3.0\r0,start,4.0,5.0,6.0\r2,*,7.0,8.0,9.0\r",
    "STEP,STEPNAME,X,Y,Z,RADIUS\r0,start,1.0,2.0,3.0,\r1,end,4.0,5.0,6.0,12\r",  # blank radius -> NaN
]


@pytest.mark.parametrize("text", MAPS)
def test_rows_identical_values_and_types(text):
    frame = load(text)
    new = checkpoint_cache.build_rows(frame)
    old = old_rows(frame)
    assert len(new) == len(old)
    for n, o in zip(new, old, strict=True):
        assert [type(x) for x in (n[0], n[1], *n[2], n[3])] == [
            type(x) for x in (o[0], o[1], *o[2], o[3])
        ]
        for a, b in zip(
            (n[0], n[1], *n[2], n[3]), (o[0], o[1], *o[2], o[3]), strict=True
        ):
            assert (a == b) or (isinstance(a, float) and np.isnan(a) and np.isnan(b))
        assert list(n[2]) == o[2]


def test_cache_is_keyed_on_the_dataframe_object():
    a = load(MAPS[0])
    r1 = checkpoint_cache.rows_for(a)
    assert checkpoint_cache.rows_for(a) is r1  # no rebuild
    b = load(MAPS[0])  # same content, new DataFrame (what saveGuildhall does)
    r2 = checkpoint_cache.rows_for(b)
    assert r2 == r1 and r2 is not r1
    c = load(MAPS[1])
    assert len(checkpoint_cache.rows_for(c)) == 2
    assert len(checkpoint_cache.rows_for(a)) == 3  # back to the first one


def test_rebuilds_when_rows_are_added_in_place():
    a = load(MAPS[0])
    assert len(checkpoint_cache.rows_for(a)) == 3
    a.loc[len(a)] = [3, "*", 0.0, 0.0, 0.0, 10]
    assert len(checkpoint_cache.rows_for(a)) == 4


@pytest.mark.parametrize("seed", range(30))
def test_prefilter_calls_exactly_the_rows_that_could_act(seed):
    """The old loop called checkpoint() for every row; it acts only when
    step == -1 or step == next_step. Simulate state changes inside the loop."""
    rnd = random.Random(seed)
    rows = [
        (
            rnd.choice([-1, 0, 1, 2, 3, 4, 4, 2]),
            rnd.choice(["start", "*", "end", "reset"]),
            (rnd.random(), rnd.random(), rnd.random()),
            rnd.choice([0, 5, 15]),
        )
        for _ in range(rnd.randrange(1, 12))
    ]
    script = [rnd.random() for _ in range(200)]

    def run(prefilter):
        state = {"next_step": rnd_start, "k": 0, "acted": []}

        def checkpoint(step, name, coords, radius):
            if (
                step == -1 or step == state["next_step"]
            ):  # the real body's two entry tests
                state["k"] += 1
                state["acted"].append((step, name, coords, radius, state["next_step"]))
                if script[state["k"] % len(script)] < 0.5:
                    state["next_step"] = 0 if step == -1 else step + 1

        for step, name, coords, radius in rows:
            if not prefilter or step == -1 or step == state["next_step"]:
                checkpoint(step, name, coords, radius)
        return state["acted"], state["next_step"]

    for rnd_start in (0, 1, 2, 3, 4):
        assert run(False) == run(True)

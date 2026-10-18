"""Pre-computed checkpoint rows for the sampling loop.

``updateMeterTimer`` used to walk ``checkpoints_list.iterrows()`` on EVERY
sample (pandas builds one Series per row per sample: by far the most expensive
step of the loop) and call ``checkpoint()`` for every row, although
``checkpoint()`` only acts on rows whose ``STEP`` is the reset marker (-1) or
the next expected step.

``rows_for`` runs ``iterrows`` once per loaded map and keeps, per row, exactly
the values the loop used to pass to ``checkpoint()``:

    (STEP, STEPNAME, [X, Y, Z], RADIUS)      # RADIUS = 0 when the column is absent

with the very same Python objects pandas produced (no re-typing, no float32
conversion: ``checkpoint()`` still builds the float32 ``ctypes`` arrays and
runs the unchanged ``scipy`` distance test).  The cache is keyed on the
DataFrame object (and its length), and ``saveGuildhall`` always replaces the
DataFrame, so a map change rebuilds it.
"""

_cached_frame = None
_cached_len = -1
_cached_rows = ()


def build_rows(frame):
    """Rows exactly as the old per-sample loop produced them."""
    rows = []
    for _index, checkpoint_data in frame.iterrows():
        if "RADIUS" in checkpoint_data:
            radius = checkpoint_data["RADIUS"]
        else:
            radius = 0
        rows.append(
            (
                checkpoint_data["STEP"],
                checkpoint_data["STEPNAME"],
                (
                    checkpoint_data["X"],
                    checkpoint_data["Y"],
                    checkpoint_data["Z"],
                ),
                radius,
            )
        )
    return tuple(rows)


def rows_for(frame):
    """Cached ``build_rows(frame)`` (rebuilt when the DataFrame changes)."""
    global _cached_frame, _cached_len, _cached_rows
    if frame is not _cached_frame or len(frame) != _cached_len:
        _cached_rows = build_rows(frame)
        _cached_frame = frame
        _cached_len = len(frame)
    return _cached_rows

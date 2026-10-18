# Linux compatibility experiment (branch `linux-compat-experiment`)

Experimental, minimal. Windows behaviour is unchanged (all changes are guarded by `sys.platform`
or are no-ops on Windows).

## Run on Linux (X11 / Xvfb)

```bash
sudo apt install python3-tk libegl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
     libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1
# Python 3.12 whose Tk is built with Xft (see note) + venv
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r gw2_speedometer_internal/requirements.txt
cd gw2_speedometer_internal
python speedometer.py --simulate          # synthetic car on an ellipse circuit (no game needed)
python map_realtime.py --simulate         # or GW2_SIMULATE=1 for any tool / the launcher
python mumblelink_linux.py --dump         # print simulated MumbleLink samples
python mumblelink_linux.py --write-circuit  # regenerates maps/SIM_CIRCUIT.csv
```

Without `--simulate`, Linux reads `/dev/shm/MumbleLink.<uid>` (override with `GW2_MUMBLELINK_PATH`),
which a Wine/Proton MumbleLink bridge must fill (untested here: no GW2 available).

Note: Python from uv's *python-build-standalone* ships a Tk without Xft, so Tk can only use X core
bitmap fonts (Montserrat / Digital-7 are ignored and the HUD looks wrong). Use a Python linked to the
system Tk 8.6 (distro Python, pyenv/source build with `tk-dev`).

`-transparentcolor` (HUD transparency) is Windows-only in Tk: on X11 the grey `#666666` background
stays opaque unless something else (e.g. an external chroma-key/shaped overlay) removes it.

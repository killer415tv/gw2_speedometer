"""Small platform helpers so the Windows-only bits do not break other systems.

On Windows every helper does exactly what the old inline code did. On Linux
(X11/Xwayland) they are harmless fallbacks.  Nothing here imports anything that
only exists on Windows at module level.
"""

import ctypes
import mmap
import os
import sys

IS_WINDOWS = sys.platform == "win32"

# Name of the shared-memory object used by GW2 / Mumble positional audio.
MUMBLE_NAME = "MumbleLink"


def simulate_requested():
    """True if ``--simulate`` was passed or GW2_SIMULATE=1 is set (inherited by
    child processes started from the launcher)."""
    if "--simulate" in sys.argv[1:]:
        return True
    return os.environ.get("GW2_SIMULATE", "").strip().lower() in ("1", "true", "yes", "on")


def set_dpi_aware():
    """Windows: same as the old try/except block. Elsewhere: no-op."""
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Windows >= 8.1
    except Exception:  # noqa: BLE001 - same fallback as the original code
        ctypes.windll.user32.SetProcessDPIAware()  # Windows 8.0 or less


def set_transparent_color(widget, color):
    """``-transparentcolor`` is a Windows-only Tk attribute (X11 raises TclError).

    On Linux the colour key is simply not applied: the HUD background stays as an
    opaque ``color`` rectangle unless a compositor/window manager does something.
    """
    try:
        widget.wm_attributes("-transparentcolor", color)
        return True
    except Exception:
        if IS_WINDOWS:
            raise
        return False


def loadfont_nonwin(fontpath):
    """Linux replacement of AddFontResourceEx: register the font privately in the
    process' fontconfig (libfontconfig), so Tk/Xft can find it by family name."""
    if IS_WINDOWS:
        return False
    try:
        fc = ctypes.CDLL("libfontconfig.so.1")
        fc.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        fc.FcConfigAppFontAddFile.restype = ctypes.c_int
        path = os.fsencode(os.path.abspath(os.fspath(fontpath)))
        ok = bool(fc.FcConfigAppFontAddFile(None, path))
        _add_font_aliases(fc)
        return ok
    except Exception:  # noqa: BLE001 - fontconfig is optional
        return False


_ALIASES_DONE = False
# The app asks for "Montserrat Regular" (GDI full name); fontconfig knows "Montserrat".
_ALIAS_XML = (
    b'<?xml version="1.0"?><fontconfig>'
    b'<alias binding="same"><family>Montserrat Regular</family>'
    b'<prefer><family>Montserrat</family></prefer></alias></fontconfig>'
)


def _add_font_aliases(fc):
    global _ALIASES_DONE
    if _ALIASES_DONE:
        return
    _ALIASES_DONE = True
    try:
        fc.FcConfigParseAndLoadFromMemory.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        fc.FcConfigParseAndLoadFromMemory.restype = ctypes.c_int
        fc.FcConfigGetCurrent.restype = ctypes.c_void_p
        cfg = fc.FcConfigGetCurrent()
        if cfg:
            fc.FcConfigParseAndLoadFromMemory(ctypes.c_void_p(cfg), _ALIAS_XML, 0)
    except Exception:  # noqa: BLE001, S110 - font aliases are cosmetic
        pass


def mumble_shm_path():
    """Path of the Mumble shared memory on Linux (``/dev/shm/MumbleLink.<uid>``).

    Override with GW2_MUMBLELINK_PATH if your Wine/Proton bridge uses another file.
    """
    override = os.environ.get("GW2_MUMBLELINK_PATH")
    if override:
        return override
    return f"/dev/shm/{MUMBLE_NAME}.{os.getuid()}"


def open_mumble_memfile(length):
    """Return an mmap-like object (seek/read/close) with the MumbleLink memory.

    * Windows: the named mapping ``MumbleLink`` (identical to the previous code).
    * ``--simulate`` / GW2_SIMULATE=1: synthetic car on a circuit (any platform).
    * Linux: file-backed mmap of /dev/shm/MumbleLink.<uid>, created zero-filled
      if it does not exist (like Mumble does) so GW2 under Wine can start writing.
    """
    if simulate_requested():
        from mumblelink_linux import SimulatedMemfile
        return SimulatedMemfile(length)
    if IS_WINDOWS:
        return mmap.mmap(fileno=-1, length=length, tagname=MUMBLE_NAME)
    from mumblelink_linux import open_shm_memfile
    return open_shm_memfile(mumble_shm_path(), length)

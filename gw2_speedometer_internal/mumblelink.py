import ctypes
import json
import logging
import mmap

from platform_compat import open_mumble_memfile

log = logging.getLogger(__name__)

# GW2 / Mumble share UTF-16 strings (2 bytes per character). ctypes.c_wchar is 2
# bytes on Windows (identical behaviour as before) but 4 bytes on Linux, so there
# the strings are read as raw 16-bit units and decoded by the properties below.
_WIDE_NATIVE = ctypes.sizeof(ctypes.c_wchar) == 2
_WIDE = ctypes.c_wchar if _WIDE_NATIVE else ctypes.c_uint16


def _encode_utf16(text, units=256):
    raw = text.encode("utf-16-le")[: (units - 1) * 2]
    raw = raw.ljust(units * 2, b"\x00")
    return [int.from_bytes(raw[i:i + 2], "little") for i in range(0, units * 2, 2)]


def _decode_utf16(units):
    raw = b"".join(int(u).to_bytes(2, "little") for u in units)
    return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]


def parse_identity(raw):
    """Parse the MumbleLink ``identity`` string into a dict.

    GW2 leaves ``identity`` empty while the game is closed, on the character
    select screen, or before the first update, so ``json.loads`` on the raw
    value can fail. Returns ``{}`` for empty/invalid/non-object content instead
    of raising.
    """
    if not raw or not isinstance(raw, str):
        return {}
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def get_identity_name(ml, default=""):
    """Character name from ``ml.data.identity`` or ``default`` if unavailable."""
    data = getattr(ml, "data", None)
    name = parse_identity(getattr(data, "identity", "")).get("name")
    return name if isinstance(name, str) and name else default


def get_identity_fov(ml, default=None):
    """Field of view from ``ml.data.identity`` or ``default`` if unavailable."""
    data = getattr(ml, "data", None)
    fov = parse_identity(getattr(data, "identity", "")).get("fov")
    return fov if isinstance(fov, (int, float)) else default


class Link(ctypes.Structure):
    if not _WIDE_NATIVE:
        # Linux/macOS: expose ``name`` and ``identity`` as str like on Windows.
        @property
        def name(self):
            return _decode_utf16(self._name_raw)

        @name.setter
        def name(self, text):
            self._name_raw[:] = _encode_utf16(text)

        @property
        def identity(self):
            return _decode_utf16(self._identity_raw)

        @identity.setter
        def identity(self, text):
            self._identity_raw[:] = _encode_utf16(text)

    def __str__(self):
        return " uiVersion:" + str(self.uiVersion) \
               + " \n uiTick: " + str(self.uiTick) \
               + " \n fAvatarPosition: " + str(self.fAvatarPosition) \
               + " \n fAvatarFront: " + str(self.fAvatarFront) \
               + " \n fAvatarTop: " + str(self.fAvatarTop) \
               + " \n name: " + str(self.name) \
               + " \n fCameraPosition: " + str(self.fCameraPosition) \
               + " \n fCameraFront: " + str(self.fCameraFront) \
               + " \n fCameraTop: " + str(self.fCameraTop) \
               + " \n identity: " + str(self.identity) \
               + " \n context_len: " + str(self.context_len)

    _fields_ = [
        ("uiVersion", ctypes.c_uint32),  # 4 bytes
        ("uiTick", ctypes.c_uint32),  # 4 bytes (c_ulong is 8 bytes on Linux)
        ("fAvatarPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fAvatarFront", ctypes.c_float * 3),  # 3*4 bytes
        ("fAvatarTop", ctypes.c_float * 3),  # 3*4 bytes
        (("name" if _WIDE_NATIVE else "_name_raw"), _WIDE * 256),  # 512 bytes
        ("fCameraPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fCameraFront", ctypes.c_float * 3),  # 3*4 bytes
        ("fCameraTop", ctypes.c_float * 3),  # 3*4 bytes
        (("identity" if _WIDE_NATIVE else "_identity_raw"), _WIDE * 256),  # 512 bytes
        ("context_len", ctypes.c_uint32),  # 4 bytes
        # ("context", ctypes.c_byte * 256),       # 256 bytes, see below
        # ("description", ctypes.c_byte * 2048),  # 2048 bytes, always empty
    ]


class Context(ctypes.Structure):
    def __str__(self):
        return "" \
               + " \n serverAddress:" + str(self.serverAddress) \
               + " \n mapId:" + str(self.mapId) \
               + " \n mapType:" + str(self.mapType) \
               + " \n shardId:" + str(self.shardId) \
               + " \n instance:" + str(self.instance) \
               + " \n buildId:" + str(self.buildId) \
               + " \n uiState:" + str(self.uiState) \
               + " \n compassWidth:" + str(self.compassWidth) \
               + " \n compassHeight:" + str(self.compassHeight) \
               + " \n compassRotation:" + str(self.compassRotation) \
               + " \n playerX:" + str(self.playerX) \
               + " \n playerY:" + str(self.playerY) \
               + " \n mapCenterX:" + str(self.mapCenterX) \
               + " \n mapCenterY:" + str(self.mapCenterY) \
               + " \n mapScale:" + str(self.mapScale)

    _fields_ = [
        ("serverAddress", ctypes.c_byte * 28),  # 28 bytes
        ("mapId", ctypes.c_uint32),  # 4 bytes
        ("mapType", ctypes.c_uint32),  # 4 bytes
        ("shardId", ctypes.c_uint32),  # 4 bytes
        ("instance", ctypes.c_uint32),  # 4 bytes
        ("buildId", ctypes.c_uint32),  # 4 bytes
        ("uiState", ctypes.c_uint32),  # 4 bytes
        ("compassWidth", ctypes.c_uint16),  # 2 bytes
        ("compassHeight", ctypes.c_uint16),  # 2 bytes
        ("compassRotation", ctypes.c_float),  # 4 bytes
        ("playerX", ctypes.c_float),  # 4 bytes
        ("playerY", ctypes.c_float),  # 4 bytes
        ("mapCenterX", ctypes.c_float),  # 4 bytes
        ("mapCenterY", ctypes.c_float),  # 4 bytes
        ("mapScale", ctypes.c_float),  # 4 bytes
    ]


class MumbleLink:
    data: Link
    context: Context

    def __init__(self):
        self.size_link = ctypes.sizeof(Link)
        self.size_context = ctypes.sizeof(Context)
        size_discarded = 256 - self.size_context + 4096  # empty areas of context and description

        # GW2 won't start sending data if memfile isn't big enough so we have to add discarded bits too
        memfile_length = self.size_link + self.size_context + size_discarded

        # Windows: named mapping "MumbleLink" (unchanged). Linux: /dev/shm/MumbleLink.<uid>
        # (Wine/Proton bridge) or the synthetic generator when --simulate is used.
        self.memfile = open_mumble_memfile(memfile_length)

        # Zeroed data (what GW2 exposes while it is closed) so that ``ml.data``
        # and ``ml.context`` always exist, even before the first read().
        self.data = Link()
        self.context = Context()
        self._read_failed = False

    def read(self):
        try:
            self.memfile.seek(0)

            data = self.unpack(Link, self.memfile.read(self.size_link))
            context = self.unpack(Context, self.memfile.read(self.size_context))
        except (ValueError, OSError) as exc:
            # e.g. the shared memory was closed: keep the last known values.
            if not self._read_failed:
                log.warning("MumbleLink read failed: %s", exc)
            self._read_failed = True
            return
        self._read_failed = False
        self.data = data
        self.context = context

    def close(self):
        self.memfile.close()

    @staticmethod
    def unpack(ctype, buf):
        cstring = ctypes.create_string_buffer(buf)
        ctype_instance = ctypes.cast(ctypes.pointer(cstring), ctypes.POINTER(ctype)).contents
        return ctype_instance
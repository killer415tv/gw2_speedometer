import ctypes
import mmap


class Link(ctypes.Structure):
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
        ("uiTick", ctypes.c_ulong),  # 4 bytes
        ("fAvatarPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fAvatarFront", ctypes.c_float * 3),  # 3*4 bytes
        ("fAvatarTop", ctypes.c_float * 3),  # 3*4 bytes
        ("name", ctypes.c_wchar * 256),  # 512 bytes
        ("fCameraPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fCameraFront", ctypes.c_float * 3),  # 3*4 bytes
        ("fCameraTop", ctypes.c_float * 3),  # 3*4 bytes
        ("identity", ctypes.c_wchar * 256),  # 512 bytes
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

        self.memfile = mmap.mmap(fileno=-1, length=memfile_length, tagname="MumbleLink")

    def read(self):
        self.memfile.seek(0)

        self.data = self.unpack(Link, self.memfile.read(self.size_link))
        self.context = self.unpack(Context, self.memfile.read(self.size_context))

    def close(self):
        self.memfile.close()

    @staticmethod
    def unpack(ctype, buf):
        cstring = ctypes.create_string_buffer(buf)
        ctype_instance = ctypes.cast(ctypes.pointer(cstring), ctypes.POINTER(ctype)).contents
        return ctype_instance
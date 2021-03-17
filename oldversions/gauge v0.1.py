import tkinter as tk
from math import pi, cos, sin
import ctypes
import mmap
import time;
import math;
from scipy.spatial import distance
from pynput.keyboard import Key, Controller

#toma de datos inicial
#ml = MumbleLink()

_lastPos = 0
_lastTick = 0
_lastTime = 0
velocity = 0
_time = 0
_pos = [0,0,0]
_tick = 0
timer = 0.01
color = "blue"
delaytimer = 0.5
pressedQ = 0
keyboard = Controller()


class Link(ctypes.Structure):
    _fields_ = [
        ("uiVersion", ctypes.c_uint32),           # 4 bytes
        ("uiTick", ctypes.c_ulong),               # 4 bytes
        ("fAvatarPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fAvatarFront", ctypes.c_float * 3),     # 3*4 bytes
        ("fAvatarTop", ctypes.c_float * 3),       # 3*4 bytes
        ("name", ctypes.c_wchar * 256),           # 512 bytes
        ("fCameraPosition", ctypes.c_float * 3),  # 3*4 bytes
        ("fCameraFront", ctypes.c_float * 3),     # 3*4 bytes
        ("fCameraTop", ctypes.c_float * 3),       # 3*4 bytes
        ("identity", ctypes.c_wchar * 256),       # 512 bytes
        ("context_len", ctypes.c_uint32),         # 4 bytes
        # ("context", ctypes.c_byte * 256),       # 256 bytes, see below
        # ("description", ctypes.c_byte * 2048),  # 2048 bytes, always empty
    ]


class Context(ctypes.Structure):
    _fields_ = [
        ("serverAddress", ctypes.c_byte * 28),    # 28 bytes
        ("mapId", ctypes.c_uint32),               # 4 bytes
        ("mapType", ctypes.c_uint32),             # 4 bytes
        ("shardId", ctypes.c_uint32),             # 4 bytes
        ("instance", ctypes.c_uint32),            # 4 bytes
        ("buildId", ctypes.c_uint32),             # 4 bytes
        ("uiState", ctypes.c_uint32),             # 4 bytes
        ("compassWidth", ctypes.c_uint16),        # 2 bytes
        ("compassHeight", ctypes.c_uint16),       # 2 bytes
        ("compassRotation", ctypes.c_float),      # 4 bytes
        ("playerX", ctypes.c_float),              # 4 bytes
        ("playerY", ctypes.c_float),              # 4 bytes
        ("mapCenterX", ctypes.c_float),           # 4 bytes
        ("mapCenterY", ctypes.c_float),           # 4 bytes
        ("mapScale", ctypes.c_float),             # 4 bytes
    ]


class MumbleLink:
    data: Link
    context: Context

    def __init__(self):
        size_link = ctypes.sizeof(Link)
        size_context = ctypes.sizeof(Context)

        memfile = mmap.mmap(fileno=-1, length=size_link + size_context, tagname="MumbleLink", access=mmap.ACCESS_READ)
        memfile.seek(0)

        self.data = self.unpack(Link, memfile.read(size_link))
        self.context = self.unpack(Context, memfile.read(size_context))

        memfile.close()


    @staticmethod
    def unpack(ctype, buf):
        cstring = ctypes.create_string_buffer(buf)
        ctype_instance = ctypes.cast(ctypes.pointer(cstring), ctypes.POINTER(ctype)).contents
        return ctype_instance

class Meter(tk.Frame):
    def __init__(self, master=None, **kw):
        tk.Frame.__init__(self, master, **kw)

        self.var = tk.IntVar(self, 0)
        self.var100 = tk.IntVar(self, 0)

        self.canvas = tk.Canvas(self, width=200, height=120,
                                borderwidth=0, highlightthickness=0,
                                bg='#666666')
        self.scale = tk.Scale(self, orient='horizontal', from_=0, to=100, variable=self.var)

        self.numero = tk.Label(self, textvariable = self.var100, fg = "white", bg="#666666", font=("Courier", 44, "bold")).place(x = 63, y = 60)

        
        

        self.canvas.create_arc(10, 15, 190, 190, extent=108, start=36,
                               style='arc', outline="#111111", width="26", tags="arcbg")
        self.canvas.create_arc(10, 15, 190, 190, extent=108, start=36,
                               style='arc', outline=color, width="20", tags="arc")

        self.meter = self.canvas.create_line(100, 100, 10, 100,
                                             fill='white',
                                             width=4)
                                             
        self.angle = 0
        self.updateMeterLine(0.2)

        self.canvas.pack(fill='both')
        self.scale.pack()

        self.var.trace_add('write', self.updateMeter)  # if this line raises an error, change it to the old way of adding a trace: self.var.trace('w', self.updateMeter)

    def updateMeterLine(self, a):
        """Draw a meter line"""
        self.angle = a
        x = 100 - 90 * cos(a * pi)
        y = 100 - 90 * sin(a * pi)
        self.canvas.coords(self.meter, 100, 100, x, y)

    def updateMeter(self, name1, name2, op):
        """Convert variable to angle on trace"""
        mini = self.scale.cget('from')
        maxi = self.scale.cget('to')
        pos = (self.var.get() - mini) / (maxi - mini)
        self.updateMeterLine(pos * 0.6 + 0.2)

    def updateMeterTimer(self):

        global _lastPos
        global _lastTick
        global _lastTime
        global velocity
        global _time
        global _pos
        global _tick
        global timer
        global color
        global keyboard
        global pressedQ
        global delaytimer

        """Fade over time"""
        #print("actualiza", flush=True)
        #toma de datos nueva
        ml = MumbleLink()
        _tick = ml.data.uiTick
        _time = time.time()
        if _lastTime + timer <= _time and _tick != _lastTick :
            pressedQ = max(pressedQ - timer, 0)
            _pos = ml.data.fAvatarPosition
            #print(list(_pos) , flush=True)
            
            # inicio de la carrera
            step0 = [49.9, 564.5, 31.9]
            arraystep0 = (ctypes.c_float * len(step0))(*step0)
            
            if distance.euclidean(_pos, arraystep0) < 5 and pressedQ == 0:
                print(distance.euclidean(_pos, arraystep0), flush=True)
                keyboard.press('r')
                keyboard.release('r')
                pressedQ = delaytimer

            # el punto de la estatua
            step1 = [-25.5, 495.9, 219.6]
            arraystep1 = (ctypes.c_float * len(step1))(*step1)
            
            if distance.euclidean(_pos, arraystep1) < 10 and pressedQ == 0:
                print(distance.euclidean(_pos, arraystep1), flush=True)
                keyboard.press('r')
                keyboard.release('r')
                pressedQ = delaytimer

            # entrada a la mina
            step2 = [-156, 363.1, 157.4]
            arraystep2 = (ctypes.c_float * len(step2))(*step2)

            if distance.euclidean(_pos, arraystep2) < 5 and pressedQ == 0:
                print(distance.euclidean(_pos, arraystep2), flush=True)
                keyboard.press('r')
                keyboard.release('r')
                pressedQ = delaytimer

            #salida de la mina
            step3 = [359, 245.7, 84]
            arraystep3 = (ctypes.c_float * len(step3))(*step3)

            if distance.euclidean(_pos, arraystep3) < 10 and pressedQ == 0:
                print(distance.euclidean(_pos, arraystep3), flush=True)
                keyboard.press('r')
                keyboard.release('r')
                pressedQ = delaytimer
            
            #puerta de focking oro
            step4 = [-142.9, 140.2, -57.6]
            arraystep4 = (ctypes.c_float * len(step4))(*step4)

            if distance.euclidean(_pos, arraystep4) < 10 and pressedQ == 0:
                print(distance.euclidean(_pos, arraystep4), flush=True)
                keyboard.press('r')
                keyboard.release('r')
                pressedQ = delaytimer

            #banderita
            step5 = [4.6, 56, 191.6]
            arraystep5 = (ctypes.c_float * len(step5))(*step5)

            if distance.euclidean(_pos, arraystep5) < 5 and pressedQ == 0:
                print(distance.euclidean(_pos, arraystep5), flush=True)
                keyboard.press('r')
                keyboard.release('r')
                pressedQ = delaytimer

            #final
            step6 = [-37.9, 1.74, -26.7]
            arraystep6 = (ctypes.c_float * len(step6))(*step6)

            if distance.euclidean(_pos, arraystep6) < 5 and pressedQ == 0:
                print(distance.euclidean(_pos, arraystep6), flush=True)
                keyboard.press('r')
                keyboard.release('r')
                pressedQ = 1

            dst = distance.euclidean(_pos, _lastPos)
            velocity = dst * 39.3700787 / timer
            if velocity > 0.0:
                #print(velocity, flush=True)
                if velocity > 0:
                    color = "#666666"                
                if velocity > 4000:
                    color = "#2294a8"
                if velocity > 5000:
                    color = "#c970cc"
                if velocity > 6000:
                    color = "#d99d68"
                if velocity > 7250:
                    color = "#ff0000"
                self.var.set(round(velocity*100/10000))
                self.var100.set(round((velocity*100/10000)*99/72))
                i = self.canvas.find_withtag("arc")
                self.canvas.itemconfig(i, outline=color)
            _lastTime = _time
            _lastPos = _pos
            _lastTick = _tick
        self.after(20, self.updateMeterTimer)


if __name__ == '__main__':
    #print("hola", flush=True)
    root = tk.Tk()
    root.call('wm', 'attributes', '.', '-topmost', '1')
    root.wm_attributes("-transparentcolor", "#666666")
    root.withdraw()

    windowWidth = root.winfo_reqwidth()
    windowHeight = root.winfo_reqheight()

    window = tk.Toplevel(root)
    positionRight = int(root.winfo_screenwidth()/2 - windowWidth/2)
    positionDown = int(root.winfo_screenheight()/2 - windowHeight/2) +400
    window.geometry("200x110+{}+{}".format(positionRight, positionDown)) #Whatever size
    window.overrideredirect(1) #Remove border
    window.wm_attributes("-transparentcolor", "#666666")
    window.attributes('-topmost', 1)
    #Whatever buttons, etc 
    
    
    #close = tk.Button(window, text = "Close Window", command = lambda: root.destroy())
    #close.pack(fill = tk.BOTH, expand = 1)

    meter = Meter(window)
    meter.pack(fill = tk.BOTH, expand = 1)
    meter.updateMeterTimer()


    root.mainloop()
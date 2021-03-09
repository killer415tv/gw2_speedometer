import tkinter as tk
from math import pi, cos, sin
import ctypes
import mmap
import time
import datetime
import math
from scipy.spatial import distance
from pynput.keyboard import Key, Controller
import csv
import sys, os


#toma de datos inicial
#ml = MumbleLink()

winh = 110
winw = 200

# this variable adjust the position of the gauge +250 for bottom position or -250 for upper position
position_up_down_offset = -250  

_lastPos = 0
_lastTick = 0
_lastTime = 0
velocity = 0
_time = 0
_pos = [0,0,0]
_tick = 0
timer = 0.01
color = "white"

delaytimer = 2
pressedQ = 0
keyboard = Controller()

#livesplit keys
enable_livesplit_hotkey = 0 # 1 = on , 0 = off
live_start='l' #key binded for start/split
live_reset='k' #key binded for reset

#logger
log = 1  # 1 = on , 0 = off
filename = "" 
filename_timer = 0


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


class Meter(tk.Frame):
    def __init__(self, master=None, **kw):
        global fundo
        global winw
        global winh
        tk.Frame.__init__(self, master, **kw)


        self.var = tk.IntVar(self, 0)
        self.var100 = tk.IntVar(self, 0)
        self.vartime = tk.StringVar(self, "")

        self.canvas = tk.Canvas(self, width=winw+800, height=winh-150,
                                borderwidth=0, highlightthickness=0,
                                bg='#666666')

        #self.scale = tk.Scale(self, orient='horizontal', from_=0, to=100, variable=self.var)

        self.numero1 = tk.Label(self, textvariable = self.vartime, fg = "#aaaaaa", bg="#666666", font=("Lucida Console", 20, "bold")).place(x = 103, y = 145)
        self.numero = tk.Label(self, textvariable = self.var100, fg = "white", bg="#666666", font=("Lucida Console", 44, "bold")).place(x = 165, y = 75)


        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=108, start=36,style='arc', outline="#666666", width="45", tags="arc")
        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=108, start=36,style='arc', outline="white", width="16", tags="arcbg")
        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=108, start=36,style='arc', outline="#666666", width="14", tags="arcbg")

        self.steps_txt = tk.StringVar(self, "")
        self.steps0 = tk.Label(self, textvariable = self.steps_txt, fg = "white", bg="#666666", font=("Lucida Console", 15, "bold")).place(x = 395, y = 0)

        self.step1_txt = tk.StringVar(self, "")
        self.steps1 = tk.Label(self, textvariable = self.step1_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 15+10)
        self.step2_txt = tk.StringVar(self, "")
        self.steps2 = tk.Label(self, textvariable = self.step2_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 30+10)
        self.step3_txt = tk.StringVar(self, "")
        self.steps3 = tk.Label(self, textvariable = self.step3_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 45+10)
        self.step4_txt = tk.StringVar(self, "")
        self.steps4 = tk.Label(self, textvariable = self.step4_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 60+10)
        self.step5_txt = tk.StringVar(self, "")
        self.steps5 = tk.Label(self, textvariable = self.step5_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 75+10)
        self.step6_txt = tk.StringVar(self, "")
        self.steps6 = tk.Label(self, textvariable = self.step6_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 90+10)

        #trans
        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=44, start=101,style='arc', outline="#666666", width="10", tags="arc1")
        #azul
        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=12, start=90,style='arc', outline="#7897ff", width="10", tags="arc2")
        #morado
        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=13, start=77,style='arc', outline="#c970cc", width="10", tags="arc3")
        #amarillo
        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=12, start=66,style='arc', outline="#ff8a36", width="10", tags="arc4")
        #rojo
        self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=31, start=36,style='arc', outline="#ff5436", width="10", tags="arc5")




        ##self.fundo = tk.PhotoImage(file="./gauge.png")
        ##self.canvas.create_image(0, 0, image=self.fundo, anchor='nw')

        self.meter = self.canvas.create_line(winw, winw, 20, winw,
                                             fill='white',
                                             width=4)

        def _create_circle(self, x, y, r, **kwargs):
            return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
        tk.Canvas.create_circle = _create_circle

        self.canvas.create_circle(204, 202, 171, fill="#666", outline="#666666", width=4)

        self.angle = 0
        self.updateMeterLine(0.2)

        self.canvas.pack(side='top', fill='both', expand='yes')
        #self.scale.pack()

        self.var.trace_add('write', self.updateMeter)  # if this line raises an error, change it to the old way of adding a trace: self.var.trace('w', self.updateMeter)

    def updateMeterLine(self, a):
        """Draw a meter line"""
        self.angle = a
        x = winw - 190 * cos(a * pi)
        y = winw - 190 * sin(a * pi)
        self.canvas.coords(self.meter, winw, winw, x, y)

    def updateMeter(self, name1, name2, op):
        """Convert variable to angle on trace"""
        mini = 0
        maxi = 100
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

        global log
        global filename
        global filename_timer

        global live_start
        global live_reset
        global enable_livesplit_hotkey

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
            
            # reset , tp position
            step = [35.67, 111.35, -7.02]
            arraystep = (ctypes.c_float * len(step))(*step)
            #la distancia de 5 es como si fuera una esfera de tamaño similar a una esfera de carreras de tiria
            if distance.euclidean(_pos, arraystep) < 5 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_reset)
                    keyboard.release(live_reset)
                pressedQ = delaytimer
                #cerrar fichero si hubiera una sesión anterior
                filename = ""
                filename_timer = _time
                print("----------------------------------")
                print("GOING TO MAP TP = RESET RUN")
                print("----------------------------------")


            # start
            start = [-1, 462.39, 218.14]
            arraystart = (ctypes.c_float * len(start))(*start)

            if distance.euclidean(_pos, arraystart) < 5 and pressedQ == 0:
                pressedQ = 0.3
                #cerrar fichero si hubiera una sesión anterior
                filename = ""
                filename_timer = _time
                print("----------------------------------")
                print("ENTER RACE START")
                print("----------------------------------")
                self.steps_txt.set("")
                self.step1_txt.set("")
                self.step2_txt.set("")
                self.step3_txt.set("")
                self.step4_txt.set("")
                self.step5_txt.set("")
                self.step6_txt.set("")
                self.vartime.set("")

            # inicio de la carrera
            step0 = [37.53, 462.32, 138.97]
            arraystep0 = (ctypes.c_float * len(step0))(*step0)
            
            if distance.euclidean(_pos, arraystep0) < 5 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_start)
                    keyboard.release(live_start)
                pressedQ = delaytimer
                #cerrar fichero si hubiera una sesión anterior
                filename = "RACE_log_" + str(_time) + ".csv"
                filename_timer = _time
                print("----------------------------------")
                print("NEW LOG FILE - " + filename)
                print("----------------------------------")
                self.steps_txt.set("")
                self.step1_txt.set("")
                self.step2_txt.set("")
                self.step3_txt.set("")
                self.step4_txt.set("")
                self.step5_txt.set("")
                self.step6_txt.set("")
                self.vartime.set("")
                if log:
                    self.steps_txt.set("")
                    writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                    writer.seek(0,2)
                    writer.writelines( (',').join(["X","Y","Z","SPEED","TIME"]))
               
                #abrir fichero nuevo con nombre de fichero terminado en la fecha o _time
                

            step1 = [-58.18, 332.07, 16.30]
            arraystep1 = (ctypes.c_float * len(step1))(*step1)
            
            if distance.euclidean(_pos, arraystep1) < 20 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_start)
                    keyboard.release(live_start)
                pressedQ = 2 # 10 SEGUNDOS
                print("----------------------------------")
                print("CHECKPOINT 1 : " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
                print("----------------------------------")
                self.steps_txt.set("RACE Times")
                self.step1_txt.set(" T1 " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))


            step2 = [161.18, 236.89, 188.38]
            arraystep2 = (ctypes.c_float * len(step2))(*step2)

            if distance.euclidean(_pos, arraystep2) < 15 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_start)
                    keyboard.release(live_start)
                pressedQ = delaytimer
                print("----------------------------------")
                print("CHECKPOINT 2 : " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
                print("----------------------------------")
                self.step2_txt.set(" T2 " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))


            step3 = [303.86, 123.30, -272.41]
            arraystep3 = (ctypes.c_float * len(step3))(*step3)

            if distance.euclidean(_pos, arraystep3) < 20 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_start)
                    keyboard.release(live_start)
                pressedQ = delaytimer
                print("----------------------------------")
                print("CHECKPOINT 3 : " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
                print("----------------------------------")
                self.step3_txt.set(" T3 " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
            

            step4 = [-0.77, 116.96, -198.97]
            arraystep4 = (ctypes.c_float * len(step4))(*step4)

            if distance.euclidean(_pos, arraystep4) < 15 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_start)
                    keyboard.release(live_start)
                pressedQ = delaytimer
                print("----------------------------------")
                print("CHECKPOINT 4 : " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
                print("----------------------------------")
                self.step4_txt.set(" T4 " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))


            step5 = [79.211, 19.69, -76.009]
            arraystep5 = (ctypes.c_float * len(step5))(*step5)

            if distance.euclidean(_pos, arraystep5) < 20 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_start)
                    keyboard.release(live_start)
                pressedQ = delaytimer
                print("----------------------------------")
                print("CHECKPOINT 5 : " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
                print("----------------------------------")
                self.step5_txt.set(" T5 " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))

            #final
            step6 = [-276.66, 42.59, -320.23]
            arraystep6 = (ctypes.c_float * len(step6))(*step6)

            if distance.euclidean(_pos, arraystep6) < 10 and pressedQ == 0:
                if filename != "":
                    datefinish = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f")
                    if enable_livesplit_hotkey == 1:
                        keyboard.press(live_start)
                        keyboard.release(live_start)
                    pressedQ = 0.5
                    filename = ""
                    print("----------------------------------")
                    print("CHECKPOINT FINAL : " + datefinish)
                    print("----------------------------------")
                    self.step6_txt.set("END " + datefinish)



            #dst = distance.euclidean(_pos, _lastPos)
            #print(_pos, _2dpos)
            #calculo de velocidad quitando eje Y (altura)

            _2dpos = [_pos[0],_pos[2]]
            dst = distance.euclidean(_2dpos, _lastPos)

            velocity = dst * 39.3700787 / timer
            if velocity > 0.0:

                #escribir velocidad,tiempo,x,y,z en fichero, solo si está abierto el fichero y si está habilitado el log

                #log = []
                if log and filename != "" and round((velocity*100/10000)*99/72) < 150:
                    #print([filename,str(_pos[0]),str(_pos[1]),str(_pos[2]),str(velocity), str(_time - filename_timer)])
                    writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                    writer.seek(0,2)
                    writer.writelines("\r")
                    writer.writelines( (',').join([str(_pos[0]),str(_pos[1]),str(_pos[2]),str(round((velocity*100/10000)*99/72)), str(_time - filename_timer)]))
                    self.vartime.set(datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))

                #print(velocity, flush=True)
                if velocity > 0:
                    color = "#666666"                
                if velocity > 4000:
                    color = "#666666" #"#2294a8"
                if velocity > 5000:
                    color = "#666666" #"#c970cc"
                if velocity > 6000:
                    color = "#666666" #"#edad18"
                if velocity > 7250:
                    color = "#de1f18"
                if round(velocity*100/10000) < 140:
                    self.var.set(round(velocity*100/10000))
                    self.var100.set(round((velocity*100/10000)*99/72))
                    i = self.canvas.find_withtag("arc")
                    self.canvas.itemconfig(i, outline=color)
                    i = self.canvas.find_withtag("numero")
                    self.canvas.itemconfig(i, fg=color)
            _lastTime = _time
            _lastPos = _2dpos
            _lastTick = _tick
        self.after(20, self.updateMeterTimer)


if __name__ == '__main__':
    root = tk.Tk()
    root.call('wm', 'attributes', '.', '-topmost', '1')
    root.withdraw()

    windowWidth = root.winfo_reqwidth()
    windowHeight = root.winfo_reqheight()

    window = tk.Toplevel(root)
    positionRight = int(root.winfo_screenwidth()/2 - windowWidth/2) -105
    positionDown = int(root.winfo_screenheight()/2 - windowHeight/2) + position_up_down_offset
    window.geometry("600x220+{}+{}".format(positionRight, positionDown)) #Whatever size
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
import tkinter as tk
from tkinter import simpledialog
from tkinter import *
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
import numpy as np
from playsound import playsound
from datetime import date
import json
import pandas as pd

np.seterr(divide='ignore', invalid='ignore')


#-----------------------------
#  CONFIGURATION VARIABLES
#-----------------------------

#WIDGET POSITION 
# this variable adjust the position of the gauge +250 for bottom position or -250 for upper position , 0 is default and center on screen
position_up_down_offset = -250
# this variable adjust the position of the gauge +250 for right position or -250 for left position , 0 is default and center on screen
position_right_left_offset = -100
#Want to press any key to make livesplit program work automatically on checkpoints?
enable_livesplit_hotkey = 0 # 1 = on , 0 = off
#livesplit keys
live_start='l' #key binded for start/split
live_reset='k' #key binded for reset
#Log all the timed splits to file CSV
log = 1  # 1 = on , 0 = off
#Play checkpoint.mp3 file when you open the program and when you go through a checkpoint
audio = 1  # 1 = on , 0 = off
#Angle meter, shows angles between velocity and mouse camera , and velocity and avatar angle 
hud_angles = 1 # 1 = on , 0 = off
hud_angles_bubbles = 0 # 1 = on , 0 = off
#Show acceleration, shows the acceleration number on hud
hud_acceleration = 1 # 1 = on , 0 = off
# show velocity
hud_gauge = 1 # 1 = on , 0 = off
# show timer
hud_timer = 1 # 1 = on , 0 = off

#-----------------------------
#  END CONFIGURATION VARIABLES
#-----------------------------




#toma de datos inicial
#ml = MumbleLink()

winh = 110
winw = 200

_lastPos = [0,0]
_lastVel = 0
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

filename = "" 
filename_timer = 0

total_distance = 0

#test audio on start
if audio:
    playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "checkpoint.mp3", block=False)


class Link(ctypes.Structure):
    def __str__(self): 
        
        return  " uiVersion:" + str(self.uiVersion) \
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
    def __str__(self): 
        return  ""\
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

        if hud_angles:
            self.anglevar = tk.StringVar(self,0)
        if hud_acceleration:
            self.accelvar = tk.StringVar(self,0)

        self.var = tk.IntVar(self, 0)
        self.var100 = tk.IntVar(self, 0)



        self.canvas = tk.Canvas(self, width=winw+800, height=winh-150,
                                borderwidth=0, highlightthickness=0,
                                bg='#666666')

        def _create_circle(self, x, y, r, **kwargs):
            return self.create_oval(x-r, y-r, x+r, y+r, **kwargs)
        tk.Canvas.create_circle = _create_circle

        #self.canvas.create_circle(200, 300, 26, fill="#666", outline="white", width=1)
        #self.canvas.create_circle(200, 300, 22, fill="#666", outline="#00d1e0", width=4)

        if hud_angles_bubbles:
            self.canvas.create_circle(200, 300, 10, fill="#666", outline="#00d1e0", width=1, tags="avatar_angle")
            self.canvas.create_circle(200, 300, 2, fill="#666", outline="#adfaff", width=1, tags="camera_angle")
            self.canvas.create_circle(200, 300, 2, fill="#666", outline="white", width=1, tags="speed_angle")
            self.canvas.create_circle(200, 300, 2, fill="#666", outline="white", width=1, tags="left_50_angle")
            self.canvas.create_circle(200, 300, 2, fill="#666", outline="white", width=1, tags="right_50_angle")


        #self.scale = tk.Scale(self, orient='horizontal', from_=0, to=100, variable=self.var)
        
        
        if hud_angles:
            self.angletext = tk.Label(self, text="v-m   v-b", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 146, y = 46)
            self.anglenum = tk.Label(self, textvariable = self.anglevar, fg = "white", bg="#666666", font=("Lucida Console", 8, "bold")).place(x = 145, y = 57)
        
        if hud_acceleration:
            self.acceltext = tk.Label(self, text="Accel.", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 231, y = 46)
            self.accelnum = tk.Label(self, textvariable = self.accelvar, fg = "white", bg="#666666", font=("Lucida Console", 8, "bold")).place(x = 230, y = 57)

        if hud_gauge:
            self.numero = tk.Label(self, textvariable = self.var100, fg = "white", bg="#666666", font=("Lucida Console", 44, "bold")).place(x = 165, y = 75)
            self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=108, start=36,style='arc', outline="#666666", width="40", tags="arc")
            self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=108, start=36,style='arc', outline="white", width="16", tags="arcbg")
            self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=108, start=36,style='arc', outline="#666666", width="14", tags="arcbg")

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

            self.meter = self.canvas.create_line(winw, winw, 20, winw,fill='white',width=4)
            self.angle = 0
            self.updateMeterLine(0.2)   
            self.var.trace_add('write', self.updateMeter)  # if this line raises an error, change it to the old way of adding a trace: self.var.trace('w', self.updateMeter)

        if hud_timer:
            self.vartime = tk.StringVar(self, "")
            self.timenum = tk.Label(self, textvariable = self.vartime, fg = "#aaaaaa", bg="#666666", font=("Lucida Console", 20, "bold")).place(x = 103, y = 145)
            self.steps_txt = tk.StringVar(self, "")
            self.steps0 = tk.Label(self, textvariable = self.steps_txt, fg = "white", bg="#666666", font=("Lucida Console", 15, "bold")).place(x = 395, y = 0)
            self.step1_txt = tk.StringVar(self, "")
            self.steps1 = tk.Label(self, textvariable = self.step1_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 15+10)


        self.canvas.create_circle(204, 202, 171, fill="#666", outline="#666666", width=4)

        self.canvas.pack(side='top', fill='both', expand='yes')
        #self.scale.pack()


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
        global _lastVel
        global _lastTick
        global _lastTime
        global velocity
        global _time
        global _pos
        global _tick
        global timer
        global color

        global audio

        global keyboard
        global pressedQ
        global delaytimer

        global log
        global filename
        global filename_timer

        global live_start
        global live_reset
        global enable_livesplit_hotkey

        global total_distance


        def checkTP(coords):

            global _pos
            global _time

            global pressedQ
            global keyboard
            global delaytimer
            global filename
            global filename_timer
            global total_distance

            # reset , tp position
            step = coords
            arraystep = (ctypes.c_float * len(step))(*step)
            #la distancia de 5 es como si fuera una esfera de tamaño similar a una esfera de carreras de tiria
            if distance.euclidean(_pos, arraystep) < 5 and pressedQ == 0:
                if enable_livesplit_hotkey == 1:
                    keyboard.press(live_reset)
                    keyboard.release(live_reset)
                pressedQ = 0.5
                #cerrar fichero si hubiera una sesión anterior
                filename = ""
                filename_timer = _time
                print("----------------------------------")
                print("GOING TO MAP TP = RESET RUN ")
                print("----------------------------------")
                self.steps_txt.set("")
                self.step1_txt.set("")
                self.vartime.set("")


        def checkpoint(step, coords):

            global _pos
            global _time
            global guildhall_name

            global pressedQ
            global keyboard
            global delaytimer
            global filename
            global filename_timer
            global total_distance

            total_distance = 0
            step0 = coords
            arraystep0 = (ctypes.c_float * len(step0))(*step0)
            
            if distance.euclidean(_pos, arraystep0) < 15 and pressedQ == 0:
                if step == "start":
                    if audio:
                        playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "checkpoint.mp3", block=False)
                    if enable_livesplit_hotkey == 1:
                        keyboard.press(live_start)
                        keyboard.release(live_start)
                    pressedQ = delaytimer
                    #cerrar fichero si hubiera una sesión anterior
                    
                    #debug mumble link object
                    #print(ml.data)
                    #print(ml.context)

                    self.steps_txt.set("")
                    self.step1_txt.set("")
                    self.vartime.set("")
                    total_distance = 0
                    if log:
                        filename = guildhall_name.get() + "_log_" + str(_time) + ".csv"
                        filename_timer = _time
                        print("----------------------------------")
                        print("NEW LOG FILE - " + filename)
                        print("----------------------------------")
                        self.steps_txt.set("")
                        writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                        writer.seek(0,2)
                        writer.writelines( (',').join(["X","Y","Z","SPEED","ANGLE_CAM", "ANGLE_BEETLE","TIME", "ACCELERATION"]))


                if step == "end":
                
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
                        newline = self.step1_txt.get() + "\n"
                        self.step1_txt.set(newline + "END " + datefinish)
                        self.vartime.set(datefinish)

                        if log:
                            #store in file the record time of full track , today date and player name
                            now = datetime.datetime.now()
                            today_date = now.strftime("%d/%m/%Y %H:%M:%S")
                            writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + guildhall_name.get() + "_records.csv",'a',newline='', encoding='utf-8')
                            writer.seek(0,2)
                            writer.writelines("\r")
                            writer.writelines( (',').join([datefinish, today_date, json.loads(ml.data.identity)["name"]]))
                        
                        if audio:
                            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "checkpoint.mp3", block=False)

                if str(step).isnumeric() == True:
                    
                    if enable_livesplit_hotkey == 1:
                        keyboard.press(live_start)
                        keyboard.release(live_start)
                    pressedQ = 2 # 10 SEGUNDOS
                    print("----------------------------------")
                    print("CHECKPOINT " + str(step) + ": " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
                    print("----------------------------------")
                    self.steps_txt.set(guildhall_name.get() + " Times")
                    newline = self.step1_txt.get() + "\n "
                    if step == 1:
                        newline = " "
                    self.step1_txt.set(newline + "T" + str(step) + " " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f"))
                    if audio:
                        playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "checkpoint.mp3", block=False)
                    

        """Fade over time"""
        #print("actualiza", flush=True)
        #toma de datos nueva
        ml.read()
        _tick = ml.data.uiTick
        _time = time.time()
        _pos = ml.data.fAvatarPosition
        _2Dpos = [_pos[0],_pos[2]]


        if _lastTime + timer <= _time and _tick != _lastTick and _2Dpos != _lastPos :
            pressedQ = max(pressedQ - timer, 0)
            if guildhall_name.get() == "GWTC":
                #GWTC Checkpoints
                checkTP([3.18, 61.32, -35.58]) # use this position when you take te map TP , to stop log file
                checkpoint("start", [49.9, 564.5, 31.9])
                checkpoint(1, [-30.5, 495.9, 219.6])
                checkpoint(2, [-156, 363.1, 157.4])
                checkpoint(3, [359, 245.7, 84])
                checkpoint(4, [-142.9, 140.2, -57.6])
                checkpoint(5, [4.6, 56, 191.6])
                checkpoint("end", [-37.9, 1.74, -26.7])

            if guildhall_name.get() == "RACE":
                #race Checkpoints
                checkTP([35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                checkpoint("start", [37.53, 462.32, 138.97])
                checkpoint(1, [-58.18, 332.07, 16.30])
                checkpoint(2, [161.18, 236.89, 188.38])
                checkpoint(3, [303.86, 123.30, -272.41])
                checkpoint(4, [-0.77, 116.96, -198.97])
                checkpoint(5, [79.211, 19.69, -76.009])
                checkpoint("end", [-276.66, 42.59, -320.23])

            if guildhall_name.get() == "EQE":
                #eqe Checkpoints
                checkTP([114.48, 9.07, 37.47]) # use this position when you take te map TP , to stop log file
                checkpoint("start", [186.02, 140.6, 198.7])
                checkpoint(1, [-78.8, 23.9, -94.5])
                checkpoint(2, [104, 142.6, -44])
                checkpoint(3, [-207, 122, -41])
                checkpoint("end", [117, 158, 256])

            if guildhall_name.get() == "SoTD":
                #SoTD Checkpoints
                checkTP([3.18, 61.32, -35.58]) # use this position when you take te map TP , to stop log file
                checkpoint("start", [93.41, 512.07, -6.85])
                checkpoint(1, [-39.83, -0.34, 74.95])
                checkpoint(2, [5.39, 88.43, 170.73])
                checkpoint(3, [-62.09, 242.28, -251.58])
                checkpoint(4, [369.351, 396.35, 91.34])
                checkpoint("end", [61.96, 512.09, -58.64])

            if guildhall_name.get() == "LRS":
                #SoTD Checkpoints
                checkTP([3.18, 61.32, -35.58]) # use this position when you take te map TP , to stop log file
                checkpoint("start", [25.83, 575.20, -14.51])
                checkpoint(1, [182.53, 488.21, 59.85])
                checkpoint(2, [203.48, 261.82, -96.09])
                checkpoint(3, [-0.6, 19.45, -254.91])
                checkpoint(4, [-101.72, 53.04, 244.96])
                checkpoint("end", [-26.74, 0.55, -51.33])

            if guildhall_name.get() == "HUR":
                #HUR Checkpoints
                checkTP([35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                checkpoint("start", [42.57, 103.83, -282.71])
                checkpoint(1, [-253.95, 162.94, 284.7])
                checkpoint(2, [81.8, 0.56, -323.83])
                checkpoint(3, [293.64, 60.74, -49.93])
                checkpoint(4, [113.59, 154.99, -62.03])
                checkpoint(5, [97.33, 221.3, 278.31])
                checkpoint("end", [42.5, 103.87, -187.45])

            #DEBUG
            #print(list(_pos) , flush=True)
            #dst = distance.euclidean(_pos, _lastPos)
            #print(_pos, _2Dpos)
            #calculo de velocidad quitando eje Y (altura)

            dst = distance.euclidean(_2Dpos, _lastPos)
            total_distance = total_distance + dst
            velocity = dst * 39.3700787 / timer
            
            if velocity > 0.0:

                #calcular el vector unitario
                angle_between_res1 = 0
                angle_between_res2 = 0

                if hud_angles:
                    def unit_vector(a):
                        return a/ np.linalg.norm(a)

                    def angle_between(v1, v2):
                        arg1 = np.cross(v1, v2)
                        arg2 = np.dot(v1, v2)
                        angle = np.arctan2(arg1, arg2)
                        return np.degrees(angle)

                    def angle_between2(v1, v2):
                        dot_pr = v1.dot(v2)
                        norms = np.linalg.norm(v1) * np.linalg.norm(v2)
                    
                        return str(round(np.rad2deg(np.arccos(dot_pr / norms))))

                    # construimos un vector con la posición actual y la anterior
                    a = np.array([_2Dpos[0] - _lastPos[0], _2Dpos[1] - _lastPos[1]])
                    b = np.array([ml.data.fCameraFront[0], ml.data.fCameraFront[2]])
                    c = np.array([ml.data.fAvatarFront[0], ml.data.fAvatarFront[2]])
                    
                    # si el vector es nulo , no hacemos nada, no hay movimiento
                    if _2Dpos[0] - _lastPos[0] == 0 or _2Dpos[1] - _lastPos[1] == 0:
                        # self.step3_txt.set("stop")
                        stop = 1
                    else:
                        # si nos estamos moviendo, calculamos el vector unitario del vector velocidad
                        uv = unit_vector(a)
                        # calculamos el vector unitario del angulo de camara
                        uc = unit_vector(b)
                        # calculamos el vector unitario del angulo de camara (avatarFront)
                        uaf = unit_vector(c)
                        
                        #self.steps_txt.set("Angles :") 

                        #self.step3_txt.set("vel: " + str(round(float(uv[0]),2)) + ' ' + str(round(float(uv[1]),2)) )
                        #self.step4_txt.set("ava: " + str(round(float(uaf[0]),2)) + ' ' + str(round(float(uaf[1]),2)) )
                        #self.step2_txt.set("cam: "+ str(round(float(uc[0]),2)) + ' ' + str(round(float(uc[1]),2)) )

                        angle_between_res1 = float(angle_between(uc, uv))
                        angle_between_res2 = float(angle_between(uaf, uv))
                        if math.isnan(angle_between_res1) == False and math.isnan(angle_between_res2) == False:

                            self.anglevar.set(str(int(angle_between_res1)) + "º/ " + str(int(angle_between_res2)) + "º")

                            full_straight_vector = [0,-1]

                            #forzamos el vector velocidad siempre alante
                            uv = full_straight_vector
                            #creamos un vector camara girando el velocidad 
                            theta = np.radians(angle_between_res1/2)
                            c, s = np.cos(theta), np.sin(theta)
                            R = np.array(((c,-s), (s, c)))
                            uc = np.dot(R, uv)
                            #creamos un vector avatar front girando la velocidad
                            theta = np.radians(angle_between_res2/2)
                            c, s = np.cos(theta), np.sin(theta)
                            R = np.array(((c,-s), (s, c)))
                            uaf = np.dot(R, uv)

                            #uc = [cos(angle_between_res1),sin(angle_between_res1)]

                            if hud_angles_bubbles:
                                theta = np.radians(50/2)
                                c, s = np.cos(theta), np.sin(theta)
                                R = np.array(((c,-s), (s, c)))
                                r50v = np.dot(R, uv)
                                theta = np.radians(-50/2)
                                c, s = np.cos(theta), np.sin(theta)
                                R = np.array(((c,-s), (s, c)))
                                l50v = np.dot(R, uv)
                            
                                #representamos con dos circulos el angulo de velocidad y el de camara
                                left_tick = self.canvas.find_withtag("left_50_angle")
                                # forzamos la representación del angulo velocidad a ponerse arriba en 0º
                                self.canvas.coords(left_tick, 200 + 195 * float(r50v[0])-4,  195 + 195 * float(r50v[1])-4 , 200 + 195 * float(r50v[0])+4 ,  195 + 195 * float(r50v[1])+4 )
                                #representamos con dos circulos el angulo de velocidad y el de camara
                                right_tick = self.canvas.find_withtag("right_50_angle")
                                # forzamos la representación del angulo velocidad a ponerse arriba en 0º
                                self.canvas.coords(right_tick, 200 + 190 * float(l50v[0])-4,  195 + 190 * float(l50v[1])-4 , 200 + 190 * float(l50v[0])+4 ,  195 + 190 * float(l50v[1])+4 )

                                #representamos con dos circulos el angulo de velocidad y el de camara
                                speed_circle = self.canvas.find_withtag("speed_angle")
                                # forzamos la representación del angulo velocidad a ponerse arriba en 0º
                                self.canvas.coords(speed_circle, 200 + 190 * float(uv[0])-4,  195 + 190 * float(uv[1])-4 , 200 + 190 * float(uv[0])+4 ,  195 + 190 * float(uv[1])+4 )
                                camera_circle = self.canvas.find_withtag("camera_angle")
                                # el angulo de la camara hay que forzarlo a ser relativo al de velocidad
                                self.canvas.coords(camera_circle, 200 + 190 * float(uc[0])-8,  195 + 190 * float(uc[1])-8 , 200 + 190 * float(uc[0])+8 ,  195 + 190 * float(uc[1])+8 )
                                avatar_circle = self.canvas.find_withtag("avatar_angle")
                                # el angulo de la camara hay que forzarlo a ser relativo al de velocidad
                                self.canvas.coords(avatar_circle, 200 + 190 * float(uaf[0])-11,  195 + 190 * float(uaf[1])-11 , 200 + 190 * float(uaf[0])+11 ,  195 + 190 * float(uaf[1])+11 )

                if hud_acceleration:
                    #calculamos la aceleración
                    acceleration = round(((velocity - _lastVel) / (_time - _lastTime)))*100/1000 

                    if acceleration > 900:
                        acceleration = 900
                    
                    if acceleration < -900:
                        acceleration = -900

                    if acceleration < 900 and acceleration > -900:
                        self.accelvar.set(acceleration);
                    
                #escribir velocidad,tiempo,x,y,z en fichero, solo si está abierto el fichero y si está habilitado el log
                if log and filename != "" and round((velocity*100/10000)*99/72) < 150:
                    #print([filename,str(_pos[0]),str(_pos[1]),str(_pos[2]),str(velocity), str(_time - filename_timer)])
                    writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                    writer.seek(0,2)
                    writer.writelines("\r")
                    writer.writelines( (',').join([str(_pos[0]),str(_pos[1]),str(_pos[2]),str(round((velocity*100/10000)*99/72)),str(angle_between_res1),str(angle_between_res2), str(_time - filename_timer), str(acceleration)]))
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
            _lastPos = _2Dpos
            _lastVel = velocity
            _lastTick = _tick
        self.after(20, self.updateMeterTimer)


if __name__ == '__main__':


    root = Tk()

    root.title("Guildhall logs")

    choices = ['None, im free!', 'GWTC', 'RACE', 'EQE', 'SoTD', 'LRS', 'HUR']
    guildhall_name = StringVar(root)
    guildhall_name.set('SELECT GUILDHALL')

    tk.Label(root, text="""Choose guildhall for the checkpoints\nYou can close this window once selected""", justify = tk.CENTER, padx = 20).pack()
    w = OptionMenu(root, guildhall_name, *choices)
    w.pack(); 

    #root.mainloop() 

    root = tk.Tk()
    root.call('wm', 'attributes', '.', '-topmost', '1')
    root.withdraw()

    ml = MumbleLink()

    windowWidth = root.winfo_reqwidth()
    windowHeight = root.winfo_reqheight()

    window = tk.Toplevel(root)
    positionRight = int(root.winfo_screenwidth()/2 - windowWidth/2) + position_right_left_offset
    positionDown = int(root.winfo_screenheight()/2 - windowHeight/2) + position_up_down_offset
    window.geometry("650x400+{}+{}".format(positionRight, positionDown)) #Whatever size
    window.overrideredirect(1) #Remove border
    window.wm_attributes("-transparentcolor", "#666666")
    window.attributes('-topmost', 1)
    #Whatever buttons, etc 


    meter = Meter(window)
    meter.pack(fill = tk.BOTH, expand = 1)
    meter.updateMeterTimer()

    root.mainloop()

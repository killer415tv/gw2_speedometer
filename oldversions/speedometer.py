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

import random

import paho.mqtt.client as mqtt #import the client1
import time

import threading
import queue


np.seterr(divide='ignore', invalid='ignore')


#-----------------------------
#  CONFIGURATION VARIABLES
#-----------------------------
#measure the speed in 3 dimensions or ignore the altitude axis
speed_in_3D = 0 # 1 = on , 0 = off
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
#Play dong.wav file when you open the program and when you go through a checkpoint
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
hud_distance = 1 # 1 = on , 0 = off

#-----------------------------
#  END CONFIGURATION VARIABLES
#-----------------------------



#-----------------------------
#  RACING VARIABLES
#-----------------------------

client = ""

#-----------------------------
#  END RACING VARIABLES
#-----------------------------

#toma de datos inicial
#ml = MumbleLink()

winh = 110
winw = 200

_pos = [0,0,0]
if speed_in_3D:
    _lastPos = [0,0,0]
else:
    _lastPos = [0,0]
_lastVel = 0
_lastTick = 0
_lastTime = 0
velocity = 0
_time = 0
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
    playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)


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

class Meter():

    def __init__(self, master=None, **kw):
        global fundo
        global winw
        global winh
        
        self.root = Tk()
        windowWidth = self.root.winfo_reqwidth()
        windowHeight = self.root.winfo_reqheight()
        positionRight = int(root.winfo_screenwidth()/2 - windowWidth/2) + position_right_left_offset
        positionDown = int(root.winfo_screenheight()/2 - windowHeight/2) + position_up_down_offset
        self.root.title("Speedometer")
        self.root.geometry("650x300+{}+{}".format(positionRight, positionDown)) #Whatever size
        self.root.overrideredirect(1) #Remove border
        self.root.wm_attributes("-transparentcolor", "#666666")
        self.root.attributes('-topmost', 1)
        self.root.configure(bg='#f0f0f0')
        def disable_event():
            self.toggleTrans()
        self.root.protocol("WM_DELETE_WINDOW", disable_event)

        if hud_angles:
            self.anglevar = tk.StringVar(self.root,0)
        if hud_acceleration:
            self.accelvar = tk.StringVar(self.root,0)

        self.var = tk.IntVar(self.root, 0)
        self.var100 = tk.IntVar(self.root, 0)

        self.canvas = tk.Canvas(self.root, width=winw+800, height=winh-150,
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


        #self.scale = tk.Scale(self.root, orient='horizontal', from_=0, to=100, variable=self.var)
        
        
        if hud_angles:
            self.angletext = tk.Label(self.root, text="Cam   Beetle", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 146, y = 46)
            self.anglenum = tk.Label(self.root, textvariable = self.anglevar, fg = "white", bg="#666666", font=("Lucida Console", 8, "bold")).place(x = 145, y = 57)
        
        if hud_acceleration:
            self.acceltext = tk.Label(self.root, text="Accel.", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 231, y = 46)
            self.accelnum = tk.Label(self.root, textvariable = self.accelvar, fg = "white", bg="#666666", font=("Lucida Console", 8, "bold")).place(x = 230, y = 57)

        if hud_gauge:
            self.numero = tk.Label(self.root, textvariable = self.var100, fg = "white", bg="#666666", font=("Lucida Console", 44, "bold")).place(x = 165, y = 75)
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
            self.vartime = tk.StringVar(self.root, "")
            self.timenum = tk.Label(self.root, textvariable = self.vartime, fg = "#aaaaaa", bg="#666666", font=("Lucida Console", 20, "bold")).place(x = 124, y = 145)
            self.distance = tk.StringVar(self.root, "")
            self.timenum = tk.Label(self.root, textvariable = self.distance, fg = "#aaaaaa", bg="#666666", font=("Lucida Console", 15)).place(x = 124, y = 170)
            self.steps_txt = tk.StringVar(self.root, "")
            self.steps0 = tk.Label(self.root, textvariable = self.steps_txt, fg = "white", bg="#666666", font=("Lucida Console", 15, "bold")).place(x = 395, y = 0)
            self.step1_txt = tk.StringVar(self.root, "")
            self.steps1 = tk.Label(self.root, textvariable = self.step1_txt, fg = "white", bg="#666666", font=("Lucida Console", 10)).place(x = 395+10, y = 15+10)


        self.canvas.create_circle(204, 202, 171, fill="#666", outline="#666666", width=4)

        self.canvas.pack(side='top', fill='both', expand='yes')

        self.move = False
        #self.scale.pack()

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
        else:
            self.root.overrideredirect(0)
        self.move = not self.move

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
        global _3Dpos
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

        global guildhall_name


        def checkTP(coords):

            global _3Dpos
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
            if distance.euclidean(_3Dpos, arraystep) < 5 and pressedQ == 0:
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
                self.distance.set("")


        def checkpoint(step, coords):

            global _3Dpos
            global _time
            global guildhall_name

            global pressedQ
            global keyboard
            global delaytimer
            global filename
            global filename_timer
            global total_distance

            global racer

            step0 = coords
            arraystep0 = (ctypes.c_float * len(step0))(*step0)
            
            if distance.euclidean(_3Dpos, arraystep0) < 15 and pressedQ == 0:
                if step == "start":
                    if audio:
                        playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)
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
                    self.distance.set("")
                    total_distance = 0
                    filename_timer = _time
                    if log:
                        filename = guildhall_name.get() + "_log_" + str(_time) + ".csv"
                        print("----------------------------------")
                        print("NEW LOG FILE - " + filename)
                        print("----------------------------------")
                        self.steps_txt.set("")
                        writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                        writer.seek(0,2)
                        writer.writelines( (',').join(["X","Y","Z","SPEED","ANGLE_CAM", "ANGLE_BEETLE","TIME", "ACCELERATION"]))
                    if racer.session_id.get() != "":
                        #mqtt se manda el tiempo como inicio
                        racer.sendMQTT({"option": "s", "time" : 0, "user": racer.username.get()})


                if step == "end":
                
                    steptime = _time - filename_timer

                    if filename != "":
                        datefinish = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime), "%M:%S:%f")[:-3]
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
                            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)

                        if racer.session_id.get() != "":
                            #mqtt se manda el tiempo como inicio
                            racer.sendMQTT({"option": "f", "time": steptime, "user": racer.username.get()})

                if str(step).isnumeric() == True:
                    
                    steptime = _time - filename_timer

                    if enable_livesplit_hotkey == 1:
                        keyboard.press(live_start)
                        keyboard.release(live_start)
                    pressedQ = 2 # 10 SEGUNDOS
                    print("----------------------------------")
                    print("CHECKPOINT " + str(step) + ": " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime), "%M:%S:%f")[:-3])
                    print("----------------------------------")
                    self.steps_txt.set(guildhall_name.get() + " Times")
                    newline = self.step1_txt.get() + "\n "
                    if step == 1:
                        newline = " "
                    self.step1_txt.set(newline + "T" + str(step) + " " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime), "%M:%S:%f")[:-3])
                    if audio:
                        playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)
                    if racer.session_id.get() != "":
                        #mqtt se manda el tiempo como inicio
                        racer.sendMQTT({"option": "c", "step": step, "time": steptime, "user": racer.username.get()})
                    

        """Fade over time"""
        #print("actualiza", flush=True)
        #toma de datos nueva
        ml.read()

        _tick = ml.data.uiTick
        _time = time.time()
        
        if ml.data.identity != "":
            racer.username.set(json.loads(ml.data.identity).get("name"))
        else: 
            racer.username.set("anon")

        _3Dpos = ml.data.fAvatarPosition

        if speed_in_3D:
            _pos = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[1],ml.data.fAvatarPosition[2]]
        else:
            _pos = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[2]]


        if _lastTime + timer <= _time and _tick != _lastTick and _pos != _lastPos :
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
            #print(_pos, _pos)
            #calculo de velocidad quitando eje Y (altura)

            dst = distance.euclidean(_pos, _lastPos)
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
                    if speed_in_3D:
                        Y_index = 2
                    else:
                        Y_index = 1
                    a = np.array([_pos[0] - _lastPos[0], _pos[Y_index] - _lastPos[Y_index]])
                    b = np.array([ml.data.fCameraFront[0], ml.data.fCameraFront[2]])
                    c = np.array([ml.data.fAvatarFront[0], ml.data.fAvatarFront[2]])
                    
                    # si el vector es nulo , no hacemos nada, no hay movimiento
                    if _pos[0] - _lastPos[0] == 0 or _pos[Y_index] - _lastPos[Y_index] == 0:
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

                #calculamos la aceleración
                acceleration = round(((velocity - _lastVel) / (_time - _lastTime)))*100/1000 

                if acceleration > 900:
                    acceleration = 900
                
                if acceleration < -900:
                    acceleration = -900

                if acceleration < 900 and acceleration > -900:
                    if hud_acceleration:
                        self.accelvar.set(acceleration);
                    
                #escribir velocidad,tiempo,x,y,z en fichero, solo si está abierto el fichero y si está habilitado el log
                if log and filename != "" and round((velocity*100/10000)*99/72) < 150:
                    #print([filename,str(_pos[0]),str(_pos[1]),str(_pos[2]),str(velocity), str(_time - filename_timer)])
                    writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                    writer.seek(0,2)
                    writer.writelines("\r")
                    writer.writelines( (',').join([str(_3Dpos[0]),str(_3Dpos[1]),str(_3Dpos[2]),str(round((velocity*100/10000)*99/72)),str(angle_between_res1),str(angle_between_res2), str(_time - filename_timer), str(acceleration)]))
                    self.vartime.set(datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - filename_timer), "%M:%S:%f")[:-3])
                    if hud_distance:
                        self.distance.set(str(round(total_distance)) + "m.")

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
            _lastPos = _pos
            _lastVel = velocity
            _lastTick = _tick

        self.root.after(20, self.updateMeterTimer)

class Racer():

    def on_message(self, client, userdata, message):

        #print("message received " ,json.loads(str(message.payload.decode("utf-8"))))
        received = json.loads(str(message.payload.decode("utf-8")))
    
        if received.get('option') == "s":
            #print("first checkpoint for!!", received.get('user'))
            user = received.get('user')
            time = received.get('time')
            self.timestamps.append({"user": user, "time": time, "step": 0})
            self.thread_queue.put("Race positions")
            # guardar tiempo de user para inicio
            # falta mostrar por pantalla el ranking de partida
        if received.get('option') == "f":
            #print("finish!!", received.get('user'))

            user = received.get('user')
            time = received.get('time')
            self.timestamps.append({"user": user, "time": time, "step": 999})
            self.thread_queue.put("Race finished\nPositions:")

            # guardar tiempo de user de fin de carrera
            # falta mostrar por pantalla el ranking de partida
        if received.get('option') == "c":
            #print("checkpoint ", received.get('step') ," for!!", received.get('user'))

            user = received.get('user')
            time = received.get('time')
            step = received.get('step')

            self.timestamps.append({"user": user, "time": time, "step": step})
            #self.thread_queue.put("checkpoint " + str(step))

            # guardar tiempo de checkpoint
            # falta mostrar por pantalla el ranking de partida
        if received.get('option') == "321GO-3":
            #print("3!!")
            self.thread_queue.put("3...")
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "ding.wav", block=False)
            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-2":
            #print("2!!")
            self.thread_queue.put("2...")
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "ding.wav", block=False)
            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-1":
            #print("1!!")
            self.thread_queue.put("1...")
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "ding.wav", block=False)
            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-GO":
            #print("GO GO GO!!")
            self.thread_queue.put("GOGOGOGO")
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)
            self.timestamps = []
            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1

    def sendMQTT(self, data):
        global client
        client.publish(self.prefix_topic + self.session_id.get(), json.dumps(data))

    def newRaceThread(self):
        t = threading.Thread(target=self.newRace())
        t.start()

    def surrender(self):
        self.sendMQTT({"option": "c", "step": 1000, "time": 0, "user": self.username.get()})

    def newRace(self ):
        print("START A NEW RACE")
        
        #mandar el 3 2 1 a todos los subscritos
        self.sendMQTT({"option": "321GO-3"})
        time.sleep(1)
        self.sendMQTT({"option": "321GO-2"})
        time.sleep(1)
        self.sendMQTT({"option": "321GO-1"})
        time.sleep(1.4)
        self.sendMQTT({"option": "321GO-GO"})
        
    def joinRace(self):
        global client

        self.status.set("JOINED!")
        self.race_status.set("Waiting to start...")
        #print(self.username.get() + " JOINED RACE: " + self.session_id.get())
        #subscribición al topico
        broker_address="test.mosquitto.org"
        #broker_address="iot.eclipse.org"
        #print("creating new instance")
        client = mqtt.Client(self.username.get() + str(random.random())) #create new instance
        client.on_message=self.on_message #attach function to callback
        #print("connecting to broker")
        client.connect(broker_address) #connect to broker
        client.loop_start() #start the loop
        #print("Subscribing to topic",self.prefix_topic + str(self.session_id.get()))
        client.subscribe(self.prefix_topic + str(self.session_id.get()))
        
        #self.thread_queue.put('Waiting for start.')
        
    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
            self.t_1.configure(fg=self.color_trans_fg); self.t_1.configure(bg=self.color_trans_bg)
            self.t_2.configure(fg=self.color_trans_fg); self.t_2.configure(bg=self.color_trans_bg)
            self.t_3.configure(fg=self.color_trans_fg); self.t_3.configure(bg="#222222")
            self.t_4.configure(fg=self.color_trans_fg); self.t_4.configure(bg=self.color_trans_bg)
            self.t_5.configure(fg=self.color_trans_fg); self.t_5.configure(bg="#222222")
            self.t_6.configure(fg=self.color_trans_fg); self.t_6.configure(bg="#222222")
            self.t_7.configure(fg=self.color_trans_fg); self.t_7.configure(bg="#222222")
            self.t_7_1.configure(fg=self.color_trans_fg); self.t_7_1.configure(bg="#222222")
            self.t_3_5.configure(fg=self.color_trans_fg); self.t_3_5.configure(bg="#222222")
            self.t_8.configure(fg=self.color_trans_fg); self.t_8.configure(bg=self.color_trans_bg)
            self.t_9.configure(fg=self.color_trans_fg); self.t_9.configure(bg=self.color_trans_bg)
            self.t_10.configure(fg=self.color_trans_fg); self.t_10.configure(bg=self.color_trans_bg)
            self.root.configure(bg=self.color_trans_bg)
            
        else:
            self.root.overrideredirect(0)
            self.t_1.configure(fg=self.color_normal_fg); self.t_1.configure(bg=self.color_normal_bg)
            self.t_2.configure(fg=self.color_normal_fg); self.t_2.configure(bg=self.color_normal_bg)
            self.t_3.configure(fg=self.color_normal_fg); self.t_3.configure(bg=self.color_normal_bg)
            self.t_4.configure(fg=self.color_normal_fg); self.t_4.configure(bg=self.color_normal_bg)
            self.t_5.configure(fg=self.color_normal_fg); self.t_5.configure(bg=self.color_normal_bg)
            self.t_6.configure(fg=self.color_normal_fg); self.t_6.configure(bg=self.color_normal_bg)
            self.t_7.configure(fg=self.color_normal_fg); self.t_7.configure(bg=self.color_normal_bg)
            self.t_7_1.configure(fg=self.color_normal_fg); self.t_7_1.configure(bg=self.color_normal_bg)
            self.t_3_5.configure(fg=self.color_normal_fg); self.t_3_5.configure(bg=self.color_normal_bg)
            self.t_8.configure(fg=self.color_normal_fg); self.t_8.configure(bg=self.color_normal_bg)
            self.t_9.configure(fg=self.color_normal_fg); self.t_9.configure(bg=self.color_normal_bg)
            self.t_10.configure(fg=self.color_normal_fg); self.t_10.configure(bg=self.color_normal_bg)
            self.root.configure(bg=self.color_normal_bg)
            
        self.move = not self.move

    def __init__(self):
        
        global guildhall_name
        global guildhall_laps

        self.move = True

        self.color_trans_fg= "white"
        self.color_trans_bg= "#666666"
        self.color_normal_fg= "black"
        self.color_normal_bg= "#f0f0f0"

        self.root = Tk()
        self.root.call('wm', 'attributes', '.', '-topmost', '1')
        self.root.title("Guildhall logs & challenger")
        self.root.geometry("350x350+0+400")
        self.root.wm_attributes("-transparentcolor", "#666666")
        self.root.configure(bg='#f0f0f0')

        def disable_event():
            self.toggleTrans()
        self.root.protocol("WM_DELETE_WINDOW", disable_event)

        self.fg = StringVar(self.root)
        self.bg = StringVar(self.root)
        self.fg.set(self.color_normal_fg)
        self.bg.set(self.color_normal_bg)
            

        self.one_name_list = []
        self.dic = {}


        self.thread_queue = queue.Queue()

        self.root.after(100, self.listen_for_result)

        self.choices = ['None, im free!', 'GWTC', 'RACE', 'EQE', 'SoTD', 'LRS', 'HUR']
        guildhall_name = StringVar(self.root)
        guildhall_name.set('SELECT GUILDHALL')
        guildhall_laps = StringVar(self.root)
        guildhall_laps.set("1 lap")

        self.t_1 = tk.Label(self.root, text="""Speedometer v1.3.15""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 15))
        self.t_1.place(x=0, y=10)
        self.t_2 = tk.Label(self.root, text="""Choose guildhall for the checkpoints\nYou can close this window once selected""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_2.place(x=0, y=40)
        self.t_3 = OptionMenu(self.root, guildhall_name, *self.choices)
        self.t_3.place(x=19, y=70, width=150)

        self.laps = ['1 lap', '2 laps', '3 laps', '4 laps', '5 laps', '6 laps', '7 laps']
        self.t_3_5 = OptionMenu(self.root, guildhall_laps, *self.laps)
        #self.t_3_5.place(x=167, y=70, width=100)

        self.status = StringVar(self.root)
        self.status.set("JOIN A RACE")

        self.race_status = StringVar(self.root)
        self.race_status.set("No race")
        self.ranking = StringVar(self.root)
        self.ranking.set("Positions")
        self.out_ranking = StringVar(self.root)
        self.out_ranking.set("Positions")

        self.session_id = StringVar(self.root)
        self.prefix_topic = "/gw2/speedometer/race/"
        self.username = StringVar(self.root)
        self.timestamps = []

        self.t_4 = tk.Label(self.root, text="""Want to challenge someone?""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_4.place(x=0, y=100)
        #tk.Label(self.root, text="""Join race:""", justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10)).place(x=0, y=110)
        
        self.t_5 = tk.Entry(self.root,textvariable=self.session_id)
        self.t_5.place(x=20, y=120, height=25)
        self.t_6 = tk.Button(self.root, textvariable=self.status, command=self.joinRace)
        self.t_6.place(x=120, y=120, width=80)

        #tk.Label(self.root, text="""Create new race:""", justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10)).pack()
        self.t_7 = tk.Button(self.root, text='START THE RACE', command=lambda:self.newRaceThread())
        self.t_7.place(x=200, y=120, width=100)
        self.t_7_1 = tk.Button(self.root, text='SURRENDER', command=lambda:self.surrender())
        self.t_7_1.place(x=200, y=175, width=100)
        self.t_8 = tk.Label(self.root, text="""-------------""", justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_8.place(x=0, y=150)
        self.t_9 = tk.Label(self.root, textvariable=self.race_status, justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_9.place(x=0, y=175)
        self.t_10 = tk.Label(self.root, textvariable=self.ranking, justify = tk.LEFT, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_10.place(x=0, y=210)

        

        self.toggleTrans()


    def listen_for_result(self):
        #update the timestamp result

        #self.timestamps = [{"name": "uno", "time": "2.1", "step": "1"},{"name": "dos", "time": "2.2", "step": "1"},{"name": "uno", "time": "4", "step": "2"}]

        values = []
        uniqueNames = []
        top_times = []
        out_times = []

        for i in self.timestamps:
            if(i["user"] not in uniqueNames):
                uniqueNames.append(i["user"]);
                values.append(i)
        for n in uniqueNames:
            filtered_list = list(filter(lambda x: x['user'] in n, self.timestamps))   
            top_time = sorted(filtered_list, key=lambda k: (-int(k['step']), k['time']))

            out = [x for x in top_time if int(x['step']) >= 1000]
            if len(out) > 0:
                out_times.append(top_time[0])
            else:
                top_times.append(top_time[0])
                
        top_times = sorted(top_times, key=lambda k: (-int(k['step']), float(k['time'])))

        rankingtxt = ""
        rankingindex = 1
        for u in top_times:
            steptime = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(u['time']), "%M:%S:%f")[:-3]
            if str(u['step']) == '999':
                rankingtxt = rankingtxt + str(rankingindex) + ": " + str(steptime) + " - FINISH > " + str(u['user']) + "\n"
            else:
                rankingtxt = rankingtxt + str(rankingindex) + ": " + str(steptime) + " - T" + str(u['step']) + " > " + str(u['user']) + "\n"

            rankingindex = rankingindex + 1
        
        out_rankingtxt = ""
        out_rankingindex = 1
        for u in out_times:
            steptime = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(u['time']), "%M:%S:%f")[:-3]
            if str(u['step']) == '1000':
                out_rankingtxt = out_rankingtxt + " OUT > " + str(u['user']) + "\n"
                
            out_rankingindex = out_rankingindex + 1
        
        self.ranking.set(rankingtxt + "---------\n" + out_rankingtxt )

        try:
            self.res = self.thread_queue.get(0)
            #self._print(self.res)
            self.race_status.set(self.res)
            self.root.after(100, self.listen_for_result)

        except queue.Empty:
            self.root.after(100, self.listen_for_result)


if __name__ == '__main__':

    #root.mainloop() 

    root = tk.Tk()
    root.call('wm', 'attributes', '.', '-topmost', '1')

    windowWidth = root.winfo_screenwidth()
    windowHeight = root.winfo_screenheight()
    root.title("Move Speedometer windows")
    root.geometry("170x50+{}+{}".format(windowWidth - 170, 0)) #Whatever size
    root.overrideredirect(1) #Remove border
    root.wm_attributes("-transparentcolor", "#666666")
    root.attributes('-topmost', 1)
    root.configure(bg='#666666')

    #root.withdraw()

    ml = MumbleLink()

    #Whatever buttons, etc 

    racer = Racer()
    meter = Meter()

    def toggleAll():
        if meter.move == racer.move:
            meter.toggleTrans()
            racer.toggleTrans()
        else:
            if meter.move:
                racer.toggleTrans()
            else:
                meter.toggleTrans()

    t_11 = tk.Button(root, text='Move Speedometer windows', command=lambda:toggleAll() ,fg="white", bg="#222222", relief='flat')
    t_11.pack(anchor="ne")

    meter.updateMeterTimer()

    root.mainloop()

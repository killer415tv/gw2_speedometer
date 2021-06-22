import tkinter as tk
from tkinter import simpledialog
from tkinter import *
from tkinter import colorchooser
from math import pi, cos, sin
import ctypes
import mmap
import time
import datetime
import math
import scipy.spatial.transform._rotation_groups
from scipy.spatial import distance
import pynput.keyboard._win32 
import pynput.mouse._win32 
from pynput.keyboard import Key, Controller
from pynput import keyboard
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

import requests

from configparser import RawConfigParser
import shlex, subprocess

np.seterr(divide='ignore', invalid='ignore')

# this variable adjust the position of the gauge +250 for bottom position or -250 for upper position , 0 is default and center on screen
position_up_down_offset = -250
# this variable adjust the position of the gauge +250 for right position or -250 for left position , 0 is default and center on screen
position_right_left_offset = -104

#-----------------------------
#  DEFAULT CONFIGURATION VARIABLES 
#-----------------------------

root = tk.Tk()
root.overrideredirect(1)
root.wm_attributes("-transparentcolor", "#666666")
root.configure(bg='#666666')

windowWidth = 650
windowHeight = 300
positionRight = int(root.winfo_screenwidth()/2 - windowWidth/2) + 120
positionDown = int(root.winfo_screenheight()/2 - windowHeight/2) 

    # IMPORTANT!!!! DONT CHANGE VALUES HERE
    # CHANGE THEM AT CONFIG.TXT
geometry_speedometer = "650x300+{}+{}".format(positionRight, positionDown)
geometry_racer = "750x450+0+400"

#measure the speed in 3 dimensions or ignore the altitude axis
speed_in_3D = 0 # 1 = on , 0 = off
#WIDGET POSITION 
#Want to press any key to make livesplit program work automatically on checkpoints?
enable_livesplit_hotkey = 0 # 1 = on , 0 = off
#livesplit keys
live_start='l' #key binded for start/split
live_reset='k' #key binded for reset
#Log all the timed splits to file CSV , needed for upload to ranking
log = 1  # 1 = on , 0 = off 
#Play dong.wav file when you open the program and when you go through a checkpoint
audio = 1  # 1 = on , 0 = off
#ghost_mode
enable_ghost_keys = 1
ghost_start = 't'
recalculate_ghost = 'y'

#show timer
hud_timer = 1 # 1 = on , 0 = off

#show log distance in metres
hud_distance = 0 # 1 = on , 0 = off

#show velocity and colorarc
hud_gauge = 1 # 1 = on , 0 = off

#show acceleration, shows the acceleration number on hud
hud_acceleration = 0 # 1 = on , 0 = off

#show Angle meter, shows angles between velocity and mouse camera , and velocity and avatar angle 
hud_angles = 0 # 1 = on , 0 = off 
hud_angles_bubbles = 1 # 1 = on , 0 = off
hud_angles_airboost = 1
hud_max_speed = 1
magic_angle = 58 # angle for hud_angles_bubbles, to show a visual guide of the magic angle

#show drift hold meter
hud_drift_hold = 0
drift_key = 'c' # for special keys like ALT use 'Key.alt_l' more info https://pynput.readthedocs.io/en/latest/_modules/pynput/keyboard/_base.html#Key
#show race assistant window, map selection and multiplayer
show_checkpoints_window = 1 

player_color = "#333333"

client = ""
mapId = 0
lastMapId = 0

winh = 110
winw = 200

if speed_in_3D == 1:
    _pos = [0,0,0]
    _lastPos = [0,0,0]
else:
    _pos = [0,0]
    _lastPos = [0,0]
last_checkpoint_position = [0,0,0]
_lastVel = 0
_lastTick = 0
_lastTime = 0
velocity = 0
_time = 0
_tick = 0
timer = 0.01
color = "white"

delaytimer = 1
pressedQ = 0
keyboard_ = Controller()

filename = "" 
total_timer = 0
lap_timer = 0

total_distance = 0
lap = 1
countdowntxt = ""

show_config = 0

map_position_last_time_send = 0

next_step = 0

#Force sound at start
if audio:
    playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)

#-----------------------------
#  END CONFIGURATION VARIABLES
#-----------------------------

from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
FR_PRIVATE  = 0x10
FR_NOT_ENUM = 0x20

def loadfont(fontpath, private=True, enumerable=False):
    '''
    Makes fonts located in file `fontpath` available to the font system.

    `private`     if True, other processes cannot see this font, and this 
                  font will be unloaded when the process dies
    `enumerable`  if True, this font will appear when enumerating fonts

    See https://msdn.microsoft.com/en-us/library/dd183327(VS.85).aspx

    '''
    # This function was taken from
    # https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
    # This function is written for Python 2.x. For 3.x, you
    # have to convert the isinstance checks to bytes and str
    if isinstance(fontpath, bytes):
        pathbuf = create_string_buffer(fontpath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExA
    elif isinstance(fontpath, str):
        pathbuf = create_unicode_buffer(fontpath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExW
    else:
        raise TypeError('fontpath must be of type str or unicode')

    flags = (FR_PRIVATE if private else 0) | (FR_NOT_ENUM if not enumerable else 0)
    numFontsAdded = AddFontResourceEx(byref(pathbuf), flags, 0)
    return bool(numFontsAdded)

loadfont(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "font.ttf")

class Configuration():
    def __init__(self, master=None, **kw):
        self.loadConf()

    def saveConf(self):
        cfg = RawConfigParser()
        global speed_in_3D
        global enable_livesplit_hotkey
        global live_start
        global live_reset
        global log
        global audio
        global hud_angles
        global hud_angles_bubbles
        global magic_angle
        global hud_acceleration
        global hud_gauge
        global hud_timer
        global hud_distance
        global enable_ghost_keys
        global ghost_start
        global recalculate_ghost
        global show_checkpoints_window
        global hud_drift_hold
        global drift_key
        global geometry_speedometer
        global geometry_racer
        global hud_angles_airboost
        global hud_max_speed
        global racer
        global meter
        global player_color

        cfg.add_section("general")

        cfg.set("general", "speed_in_3D", speed_in_3D)
        cfg.set("general", "enable_livesplit_hotkey", enable_livesplit_hotkey)
        cfg.set("general", "live_start", live_start)
        cfg.set("general", "live_reset", live_reset)
        cfg.set("general", "log", log)
        cfg.set("general", "audio", audio)
        cfg.set("general", "hud_angles", hud_angles)
        cfg.set("general", "hud_angles_bubbles", hud_angles_bubbles)
        cfg.set("general", "hud_angles_airboost", hud_angles_airboost)
        cfg.set("general", "hud_max_speed", hud_max_speed)
        cfg.set("general", "magic_angle", magic_angle)
        cfg.set("general", "hud_acceleration", hud_acceleration)
        cfg.set("general", "hud_gauge", hud_gauge)
        cfg.set("general", "hud_timer", hud_timer)
        cfg.set("general", "hud_distance", hud_distance)
        cfg.set("general", "enable_ghost_keys", enable_ghost_keys)
        cfg.set("general", "ghost_start", ghost_start)
        cfg.set("general", "recalculate_ghost", recalculate_ghost)
        cfg.set("general", "show_checkpoints_window", show_checkpoints_window)
        cfg.set("general", "hud_drift_hold", hud_drift_hold)
        cfg.set("general", "drift_key", drift_key)
        cfg.set("general", "player_color", player_color)
        if 'racer' in globals():
            cfg.set("general", "geometry_speedometer", meter.root.geometry())
        if 'meter' in globals():
            cfg.set("general", "geometry_racer", racer.root.geometry())

        f = open("./config.txt", "w")
        cfg.write(f)
        f.close()

    def loadConf(self):
        cfg = RawConfigParser()
        global speed_in_3D
        global enable_livesplit_hotkey
        global live_start
        global live_reset
        global log
        global audio
        global hud_angles
        global hud_angles_bubbles
        global magic_angle
        global hud_acceleration
        global hud_gauge
        global hud_timer
        global hud_distance
        global enable_ghost_keys
        global ghost_start
        global recalculate_ghost
        global show_checkpoints_window
        global hud_drift_hold
        global drift_key
        global geometry_speedometer
        global geometry_racer
        global hud_angles_airboost
        global hud_max_speed
        global player_color


        if (cfg.read(["./config.txt"])):

            if (cfg.has_option("general", "speed_in_3D")):
                speed_in_3D = int(cfg.get("general", "speed_in_3D"))
            if (cfg.has_option("general", "enable_livesplit_hotkey")):
                enable_livesplit_hotkey = int(cfg.get("general", "enable_livesplit_hotkey"))
            if (cfg.has_option("general", "live_start")):
                live_start = cfg.get("general", "live_start")
            if (cfg.has_option("general", "live_reset")):
                live_reset = cfg.get("general", "live_reset")
            if (cfg.has_option("general", "log")):
                log = int(cfg.get("general", "log"))
            if (cfg.has_option("general", "audio")):
                audio = int(cfg.get("general", "audio"))
            if (cfg.has_option("general", "hud_angles")):
                hud_angles = int(cfg.get("general", "hud_angles"))
            if (cfg.has_option("general", "hud_angles_bubbles")):
                hud_angles_bubbles = int(cfg.get("general", "hud_angles_bubbles"))
            if (cfg.has_option("general", "hud_angles_airboost")):
                hud_angles_airboost = int(cfg.get("general", "hud_angles_airboost"))
            if (cfg.has_option("general", "hud_max_speed")):
                hud_max_speed = int(cfg.get("general", "hud_max_speed"))
            if (cfg.has_option("general", "magic_angle")):
                magic_angle = int(cfg.get("general", "magic_angle"))
            if (cfg.has_option("general", "hud_acceleration")):
                hud_acceleration = int(cfg.get("general", "hud_acceleration"))
            if (cfg.has_option("general", "hud_gauge")):
                hud_gauge = int(cfg.get("general", "hud_gauge"))
            if (cfg.has_option("general", "hud_timer")):
                hud_timer = int(cfg.get("general", "hud_timer"))
            if (cfg.has_option("general", "hud_distance")):
                hud_distance = int(cfg.get("general", "hud_distance"))
            if (cfg.has_option("general", "enable_ghost_keys")):
                enable_ghost_keys = int(cfg.get("general", "enable_ghost_keys"))
            if (cfg.has_option("general", "ghost_start")):
                ghost_start = cfg.get("general", "ghost_start")
            if (cfg.has_option("general", "recalculate_ghost")):
                recalculate_ghost = cfg.get("general", "recalculate_ghost")
            if (cfg.has_option("general", "show_checkpoints_window")):
                show_checkpoints_window = int(cfg.get("general", "show_checkpoints_window"))
            if (cfg.has_option("general", "hud_drift_hold")):
                hud_drift_hold = int(cfg.get("general", "hud_drift_hold"))
            if (cfg.has_option("general", "drift_key")):
                drift_key = (cfg.get("general", "drift_key"))
            if (cfg.has_option("general", "player_color")):
                player_color = (cfg.get("general", "player_color"))
            if (cfg.has_option("general", "geometry_speedometer")):
                geometry_speedometer = (cfg.get("general", "geometry_speedometer"))
            if (cfg.has_option("general", "geometry_racer")):
                geometry_racer = (cfg.get("general", "geometry_racer"))

        else:
            # Generate a default config file with default values
            self.saveConf()

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

    def setOnTopfullscreen(self):
        self.root.attributes('-topmost', 1)
        self.root.after(500, self.setOnTopfullscreen)

    def on_press(self,key):
        global filename_timer
        global drift_key
        try:
            if str(key).replace("'","") == drift_key:
                if self.drifting == False:
                    self.drift_time = time.perf_counter() 
                self.drifting = True
                
            
        except AttributeError:
            None

    def on_release(self,key):
        global drift_key
        try:
            if str(key).replace("'","") == drift_key:
                self.drift_time = time.perf_counter()
                self.drifting = False
           
        except AttributeError:
            None

    def __init__(self, master=None, **kw):
        global fundo
        global winw
        global winh
        global _pos
        global _lastPos
        global geometry_speedometer
        

        self.root = Tk()
        self.root.config(cursor="none")
        self.root.title("Speedometer")
        self.root.geometry(geometry_speedometer) #Whatever size
        self.root.overrideredirect(1) #Remove border
        self.root.wm_attributes("-transparentcolor", "#666666")
        self.root.attributes('-topmost', 1)
        self.root.configure(bg='#f0f0f0')
        def disable_event():
            self.toggleTrans()
        self.root.protocol("WM_DELETE_WINDOW", disable_event)

        if speed_in_3D:
            _pos = [0,0,0]
            _lastPos = [0,0,0]
        else:
            _pos = [0,0]
            _lastPos = [0,0]

        self.var = tk.IntVar(self.root, 0)
        self.max_speed = tk.IntVar(self.root, 0)
        self.var100 = tk.IntVar(self.root, 0)

        self.canvas = tk.Canvas(self.root, width=winw+800, height=winh-150,
                                borderwidth=0, highlightthickness=0,
                                bg='#666666')

        if hud_angles:
            self.anglevar = tk.StringVar(self.root,0)

        if hud_angles_airboost:
            self.airdrift_angle_tk = tk.IntVar(self.root, 0.0)
            
            self.outer_airdrift_box = self.canvas.create_rectangle(20 + 356, 30,30 + 356, 100, outline="#666666", width="1", tags="airdrift_meter_border")
            self.inner_airdrift_box = self.canvas.create_rectangle(23 + 356, 33,27 + 356, 97, outline="#666666", fill='#666666', width="5", tags="airdrift_meter")
            self.airdrift_label = tk.Label(self.root, textvariable = self.airdrift_angle_tk, fg = "white", bg="#666666", font=("Digital-7 Mono", 9)).place(x = 17 + 356, y = 102)

        if hud_acceleration:
            self.accelvar = tk.StringVar(self.root,0)
        if hud_drift_hold:
            self.drifting = False
            self.drift_time = 0.0
            self.drift_time_tk = tk.IntVar(self.root, 0.0)


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
        
        if hud_drift_hold:
            listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release)
            listener.start()

            self.outer_drifting_box = self.canvas.create_rectangle(20,30,30,100, outline="white", width="1", tags="drift_meter_border")
            self.inner_drifting_box = self.canvas.create_rectangle(23,33,27,97, outline="#ff5436", fill='#ff5436', width="5", tags="drift_meter")
            self.drifting_label = tk.Label(self.root, textvariable = self.drift_time_tk, fg = "white", bg="#666666", font=("Digital-7 Mono", 9)).place(x = 12, y = 102)

        if hud_angles:
            self.angletext = tk.Label(self.root, text="Cam   Beetle", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 146, y = 46)
            self.anglenum = tk.Label(self.root, textvariable = self.anglevar, fg = "white", bg="#666666", font=("Digital-7 Mono", 8, "bold")).place(x = 145, y = 57)
        
        if hud_acceleration:
            self.acceltext = tk.Label(self.root, text="Accel.", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 231, y = 46)
            self.accelnum = tk.Label(self.root, textvariable = self.accelvar, fg = "white", bg="#666666", font=("Digital-7 Mono", 8, "bold")).place(x = 230, y = 57)

        

        if hud_gauge:
            self.numero = tk.Label(self.root, textvariable = self.var100, fg = "white", bg="#666666", font=("Digital-7 Mono", 50)).place(relx = 1, x = -412, y = 73, anchor = 'ne')
            self.canvas.create_arc(2*10, 2*15, 2*winw-10, 2*winw-10, extent=108, start=36,style='arc', outline="#666666", width="35", tags="arc")
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

            if hud_max_speed:
                self.max_meter_meter = self.canvas.create_line(winw, winw, 20, winw,fill='lime',width=4)
                self.max_speed.set(7250)
                self.updateMeterLine(0.5, self.max_meter_meter)
                self.max_speed.trace_add('write', self.updateMeterMaxSpeed)

            self.meter = self.canvas.create_line(winw, winw, 20, winw,fill='white',width=4)
            self.angle = 0.2
            self.updateMeterLine(self.angle, self.meter)   
            self.var.trace_add('write', self.updateMeter)  # if this line raises an error, change it to the old way of adding a trace: self.var.trace('w', self.updateMeter)



        #if hud_timer:
            self.vartime = tk.StringVar(self.root, "")
            self.timenum_label = tk.Label(self.root, textvariable = self.vartime, fg = "#eee", bg="#666666", font=("Digital-7 Mono", 20)).place(x = 144, y = 145)
            self.distance = tk.StringVar(self.root, "")
            self.distance_label = tk.Label(self.root, textvariable = self.distance, fg = "#eee", bg="#666666", font=("Digital-7 Mono", 15)).place(x = 144, y = 170)
            self.steps_txt = tk.StringVar(self.root, "")
            self.steps0 = tk.Label(self.root, textvariable = self.steps_txt, fg = "#fff", bg="#666666", font=("Lucida Console", 9, "bold")).place(anchor="center", x = 204, y = 202)
            self.step1_txt = tk.StringVar(self.root, "")
            self.steps1 = tk.Label(self.root, textvariable = self.step1_txt, fg = "#eeeeee", bg="#666666", font=("Digital-7 Mono", 10)).place(anchor="center",x = 200, y = 143)

        self.canvas.create_circle(204, 202, 171, fill="#666", outline="#666666", width=4)

        self.canvas.pack(side='top', fill='both', expand='yes')

        self.move = False

        self.setOnTopfullscreen()

        #self.scale.pack()

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
        else:
            self.root.overrideredirect(0)
        self.move = not self.move

    def updateMeterLine(self, angle, line):
        """Draw a meter line"""
        
        x = winw - 190 * cos(angle * pi)
        y = winw - 190 * sin(angle * pi)
        self.canvas.coords(line, winw, winw, x, y)

    def updateMeter(self, name1, name2, op):
        """Convert variable to angle on trace"""
        mini = 0
        maxi = 100
        pos = (self.var.get() - mini) / (maxi - mini)
        self.angle = pos * 0.6 + 0.2
        self.updateMeterLine(self.angle, self.meter)

    def updateMeterMaxSpeed(self, name1, name2, op):
        """Convert variable to angle on trace"""
        mini = 0
        maxi = 100
        pos = (self.max_speed.get() - mini) / (maxi - mini)
        self.updateMeterLine(pos * 0.6 + 0.2, self.max_meter_meter)

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
        global speed_in_3D

        global audio

        global keyboard_
        global pressedQ
        global delaytimer

        global log
        global filename
        global total_timer

        global live_start
        global live_reset
        global enable_livesplit_hotkey

        global enable_ghost_keys
        global ghost_start
        global recalculate_ghost

        global total_distance

        global guildhall_name
        global guildhall_laps

        global racer
        global client
        global map_position_last_time_send

        global mapId
        global lastMapId

        if hud_drift_hold:
            
            i = self.canvas.find_withtag("drift_meter")
            b = self.canvas.find_withtag("drift_meter_border")
            if self.drifting:
                seconds = round((time.perf_counter() - self.drift_time) * 100)/100
                self.drift_time_tk.set(round((time.perf_counter() - self.drift_time) * 10)/10)
                pixels = min(64,round(seconds * 64 / 1.2))
                self.canvas.coords(i, 23, 97-pixels , 27, 97)
                self.canvas.itemconfig(b, outline="white")
                
                if (seconds > 1.0):
                    self.canvas.itemconfig(i, outline="#ff8a36")
                    self.canvas.itemconfig(i, fill="#ff8a36")
                else:
                    self.canvas.itemconfig(i, outline="#7897ff")
                    self.canvas.itemconfig(i, fill="#7897ff")
                if (seconds > 1.2):
                    self.canvas.itemconfig(i, outline="#de1f18")
                    self.canvas.itemconfig(i, fill="#de1f18")
                    self.canvas.itemconfig(b, outline="#de1f18")
            else:
                self.canvas.coords(i, 23, 96 , 27, 97)
                self.canvas.itemconfig(i, outline="white")
                self.canvas.itemconfig(i, fill="white")
                self.canvas.itemconfig(b, outline="#666")


        def different(v1,v2):
            if ( v1[0] == v2[0] and v1[1] == v2[1] and v1[2] == v2[2] ):
                return False
            else:
                return True

        def checkTP(coords):
            global last_checkpoint_position

            global _3Dpos
            global _time

            global pressedQ
            global keyboard_
            global delaytimer
            global filename
            global total_timer
            global lap_timer
            global total_distance

            global lap
            global racer

            # reset , tp position
            arraystep = (ctypes.c_float * len(coords))(*coords)
            #la distancia de 5 es como si fuera una esfera de tamaño similar a una esfera de carreras de tiria
            if distance.euclidean(_3Dpos, arraystep) < 5 and (pressedQ == 0 or different(last_checkpoint_position, arraystep)):
                if 'racer' in globals():
                    racer.saveCheckpoint(0)
                    
                last_checkpoint_position = arraystep
                if enable_livesplit_hotkey == 1:
                    keyboard_.press(live_reset)
                    keyboard_.release(live_reset)
                pressedQ = 0.5
                #cerrar fichero si hubiera una sesión anterior
                filename = ""
                total_timer = _time
                lap_timer = _time
                #print("----------------------------------")
                #print("GOING TO MAP TP = RESET RUN ")
                #print("----------------------------------")
                self.steps_txt.set("")
                self.step1_txt.set("")
                self.vartime.set("")
                self.distance.set("")
                lap = 1

        def checkpoint(step, stepName, coords):
            global last_checkpoint_position
            global _3Dpos
            global _time
            global guildhall_name
            global guildhall_laps
            global speed_in_3D

            global pressedQ
            global keyboard_
            global delaytimer
            global filename
            global total_timer
            global lap_timer
            global total_distance
            global lap

            global magic_angle
            global upload
            global racer
            global map_position_last_time_send
            global next_step

            global player_color


            if step == -1:
                arraystep = (ctypes.c_float * len(coords))(*coords)
                #la distancia de 5 es como si fuera una esfera de tamaño similar a una esfera de carreras de tiria
                if distance.euclidean(_3Dpos, arraystep) < 5 and (pressedQ == 0 or different(last_checkpoint_position, arraystep)):
                    if 'racer' in globals():
                        racer.saveCheckpoint(0)
                        
                    last_checkpoint_position = arraystep
                    if enable_livesplit_hotkey == 1:
                        keyboard_.press(live_reset)
                        keyboard_.release(live_reset)
                    pressedQ = 0.5
                    #cerrar fichero si hubiera una sesión anterior
                    filename = ""
                    total_timer = _time
                    lap_timer = _time
                    #print("----------------------------------")
                    #print("GOING TO MAP TP = RESET RUN ")
                    #print("----------------------------------")
                    self.steps_txt.set("")
                    self.step1_txt.set("")
                    self.vartime.set("")
                    self.distance.set("")
                    lap = 1
            

            total_laps = int(guildhall_laps.get()[:1])

            #only valid steps are the next one, or the first one
            if step == next_step or step == 0:

                step0 = coords
                arraystep0 = (ctypes.c_float * len(step0))(*step0)
                if distance.euclidean(_3Dpos, arraystep0) < 15 and (pressedQ == 0 or different(last_checkpoint_position, arraystep0)):
                    
                    if 'racer' in globals():
                        if stepName == "end":
                            racer.saveCheckpoint(0)
                        else:
                            racer.saveCheckpoint(int(step) + 1)

                    last_checkpoint_position = arraystep0
                    if stepName == "start":
                        next_step = 1
                        if audio:
                            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)
                        if enable_livesplit_hotkey == 1:
                            keyboard_.press(live_start)
                            keyboard_.release(live_start)
                        #first time we start
                        if enable_ghost_keys:
                            keyboard_.press(ghost_start)
                            keyboard_.release(ghost_start)
                        pressedQ = delaytimer
                        #cerrar fichero si hubiera una sesión anterior
                        
                        #debug mumble link object
                        #print(ml.data)
                        #print(ml.context)

                        if int(lap) == 1:
                            
                            self.steps_txt.set(guildhall_name.get() )
                            self.step1_txt.set(str(lap) + "/"+ str(total_laps) + " T0" + " " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(0), "%M:%S:%f")[:-3])
                            self.vartime.set("")
                            self.distance.set("")
                            total_distance = 0
                            total_timer = _time
                            lap_timer = _time
                            filename = guildhall_name.get() + "_log_" + str(round(_time)) + ".csv"
                            if log:
                                #print("----------------------------------")
                                #print("NEW LOG FILE - " + filename)
                                #print("----------------------------------")
                                writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                                writer.seek(0,2)
                                writer.writelines( (',').join(["X","Y","Z","SPEED","ANGLE_CAM", "ANGLE_BEETLE","TIME", "ACCELERATION"]))
                            if show_checkpoints_window and racer.session_id.get() != "":
                                #mqtt se manda el tiempo como inicio
                                racer.sendMQTT({"option": "s", "lap": lap, "time" : 0, "user": racer.username.get()})
                        else:
                            lap_timer = _time
                            steptime_lap = _time - lap_timer
                            steptime = _time - total_timer
                            #cross the start on second lap
                            newline = ""
                            
                            self.step1_txt.set(str(lap) + "/"+ str(total_laps) + " T0" + " " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime_lap), "%M:%S:%f")[:-3])

                            filename = guildhall_name.get() + "_log_" + str(_time) + ".csv"
                            if log:
                                #print("----------------------------------")
                                #print("NEW LOG FILE - " + filename)
                                #print("----------------------------------")
                                writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                                writer.seek(0,2)
                                writer.writelines( (',').join(["X","Y","Z","SPEED","ANGLE_CAM", "ANGLE_BEETLE","TIME", "ACCELERATION"]))
                            if show_checkpoints_window and racer.session_id.get() != "":
                                #mqtt se manda el tiempo como inicio
                                racer.sendMQTT({"option": "s", "lap": lap, "step": 0, "time" : steptime, "user": racer.username.get()})

                        

                    if stepName == "end":
                        next_step = 0
                        steptime = _time - total_timer
                        steptime_lap = _time - lap_timer
                        pressedQ = 0.5
                        if enable_ghost_keys:
                            keyboard_.press(recalculate_ghost)
                            keyboard_.release(recalculate_ghost)

                        if filename != "":
                            if audio:
                                playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)

                            #upload log to 
                            if upload.get() == 1:
                                if log:
                                    headers = {
                                        'Origin': 'null',
                                        'Referer': 'null'
                                    }
                                    response = requests.post('http://beetlerank.bounceme.net/upload-log',data={'user': json.loads(ml.data.identity)["name"], 'guildhall': guildhall_name.get()}, files={'file': open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'rb')}, headers=headers)
                                    print("Log uploaded to web")
                                    print(response.text)
                                    if response.text and int(total_laps) == 1:
                                        message.write(response.text)
                                    racer.saveGuildhall(guildhall_name.get())

                            if int(lap) == int(total_laps):
                                datefinish = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime_lap), "%M:%S:%f")[:-3]
                                if enable_livesplit_hotkey == 1:
                                    keyboard_.press(live_start)
                                    keyboard_.release(live_start)

                                filename = ""
                                #print("----------------------------------")
                                #print("CHECKPOINT FINAL RACE: " + datefinish)
                                #print("----------------------------------")
                                newline = self.step1_txt.get() + "\n"
                                self.step1_txt.set(str(lap) + "/"+ str(total_laps) + " TF " + datefinish)
                                if hud_timer:
                                    self.vartime.set(datefinish)
                                

                                if log:
                                    #store in file the record time of full track , today date and player name
                                    now = datetime.datetime.now()
                                    today_date = now.strftime("%d/%m/%Y %H:%M:%S")
                                    writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + guildhall_name.get() + "_records.csv",'a',newline='', encoding='utf-8')
                                    writer.seek(0,2)
                                    writer.writelines("\r")
                                    writer.writelines( (',').join([datefinish, today_date, json.loads(ml.data.identity)["name"]]))

                                if show_checkpoints_window and racer.session_id.get() != "":
                                    #mqtt se manda el tiempo como inicio
                                    racer.sendMQTT({"option": "f", "lap":lap, "time": steptime, "step": 999, "user": racer.username.get()})
                                
                                lap = 1
                                
                            else:
                                steptime = _time - total_timer
                                steptime_lap = _time - lap_timer
                                #cross the start on second lap
                                newline = self.step1_txt.get() + "\n "
                                #print("----------------------------------")
                                #print("CHECKPOINT FINAL LAP : " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime), "%M:%S:%f")[:-3])
                                #print("----------------------------------")
                                self.step1_txt.set(str(lap) + "/"+ str(total_laps) + " TF " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime_lap), "%M:%S:%f")[:-3])

                                if show_checkpoints_window and racer.session_id.get() != "":
                                    #mqtt se manda el tiempo como inicio
                                    racer.sendMQTT({"option": "f", "lap": lap, "step": 998, "time" : steptime, "user": racer.username.get()})
                                
                                lap = lap + 1

                            """ 
                            #stores in counterDone.txt number of total laps done
                            file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "counterDone.txt")
                            global numero_contador
                            line = file.read()
                            if line == '':
                                line = "1"
                            numero_contador = int(line.strip()) + 1
                            file.close()
                            file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "counterDone.txt", "w")
                            file.write(str(numero_contador))
                            file.close()
                            """

                    if stepName == "*":
                        
                        next_step = step + 1

                        steptime = _time - total_timer
                        steptime_lap = _time - lap_timer


                        if enable_livesplit_hotkey == 1:
                            keyboard_.press(live_start)
                            keyboard_.release(live_start)
                        pressedQ = 2 # 10 SEGUNDOS
                        #print("----------------------------------")
                        #print("CHECKPOINT " + str(step) + ": " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime), "%M:%S:%f")[:-3])
                        #print("----------------------------------")
                        self.steps_txt.set(guildhall_name.get() )
                        newline = self.step1_txt.get() + "\n "
                        if step == 1 and lap == 1:
                            newline = " "
                        self.step1_txt.set(str(lap) + "/"+ str(total_laps) + " T" + str(step) + " " + datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(steptime_lap), "%M:%S:%f")[:-3])
                        if audio:
                            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)
                        if show_checkpoints_window and racer.session_id.get() != "":
                            #mqtt se manda el tiempo como inicio
                            racer.sendMQTT({"option": "c", "step": step, "lap": lap, "time": steptime, "user": racer.username.get()})
                        

        """Fade over time"""
        #print("actualiza", flush=True)
        #toma de datos nueva
        ml.read()

        mapId = ml.context.mapId
        if (mapId != lastMapId):
            lastMapId = ml.context.mapId

            if (guildhall_name.get() != 'None, im free!'):
                if (ml.context.mapId == 54):
                    guildhall_name.set("TYRIA BRISBAN WILD.")
                    racer.saveGuildhall("TYRIA BRISBAN WILD.")
                elif (ml.context.mapId == 39):
                    guildhall_name.set("TYRIA INF.LEAP")
                    racer.saveGuildhall("TYRIA INF.LEAP")
                elif (ml.context.mapId == 32):
                    guildhall_name.set("TYRIA DIESSA PLATEAU")
                    racer.saveGuildhall("TYRIA DIESSA PLATEAU")
                elif (ml.context.mapId == 31):
                    guildhall_name.set("TYRIA SNOWDEN DRIFTS")
                    racer.saveGuildhall("TYRIA SNOWDEN DRIFTS")
                elif (ml.context.mapId == 24):
                    guildhall_name.set("TYRIA GENDARRAN")
                    racer.saveGuildhall("TYRIA GENDARRAN")
                elif (ml.context.mapId == 1330):
                    guildhall_name.set("TYRIA GROTHMAR VALLEY")
                    racer.saveGuildhall("TYRIA GROTHMAR VALLEY")
            
                
        _tick = ml.data.uiTick
        _time = time.time()
        
        _3Dpos = ml.data.fAvatarPosition

        if speed_in_3D:
            _pos = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[1],ml.data.fAvatarPosition[2]]
        else:
            _pos = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[2]]

        
        if 'racer' in globals() and client != "":
            if map_position_last_time_send != round(_time*10/2):
                map_position_last_time_send = round(_time*10/2)
                racer.sendMQTT({"option": "position", "x": ml.data.fAvatarPosition[0], "y": ml.data.fAvatarPosition[1], "z": ml.data.fAvatarPosition[2], "user": racer.username.get(), "map": guildhall_name.get(), "color": player_color})
        

        if show_checkpoints_window and 'racer' in globals():  
            if ml.data.identity != "":
                racer.username.set(json.loads(ml.data.identity).get("name"))
            else: 
                racer.username.set("anon")

        if _lastTime + timer <= _time and _tick != _lastTick and _pos != _lastPos :
            pressedQ = max(pressedQ - timer, 0)

            if show_checkpoints_window: 

                if guildhall_name.get() == "FLY-1 Verdant Brink Hunt":
                    checkpoint(0,"start",[877.1676635742188,428.8018798828125,50.82432174682617])
                    checkpoint(-1,"reset",[932.6641845703125,418.795166015625,53.32091522216797])
                    checkpoint(1,"*",[819.204345703125,323.963623046875,39.1912956237793])
                    checkpoint(2,"*",[603.0380249023438,335.5285949707031,93.37494659423828])
                    checkpoint(3,"*",[564.6641235351562,336.8139343261719,303.9140319824219])
                    checkpoint(4,"*",[533.5425415039062,336.4484558105469,406.2262878417969])
                    checkpoint(5,"*",[439.9372253417969,365.7117919921875,266.8668518066406])
                    checkpoint(6,"*",[550.8067016601562,366.7596130371094,261.3218688964844])
                    checkpoint(7,"*",[730.404296875,368.8663330078125,234.38641357421875])
                    checkpoint(8,"*",[925.6776123046875,361.9156494140625,312.4433898925781])
                    checkpoint(9,"*",[814.8397216796875,340.30828857421875,386.6462097167969])
                    checkpoint(10,"end",[660.4026489257812,339.56341552734375,357.9527282714844])

                if guildhall_name.get() == "GWTC":
                    #GWTC Checkpoints
                    checkpoint(-1,"reset", [3.18, 61.32, -35.58]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [49.9, 564.5, 31.9])
                    checkpoint(1, "*", [-30.5, 495.9, 219.6])
                    checkpoint(2, "*", [-156, 363.1, 157.4])
                    checkpoint(3, "*", [359, 245.7, 84])
                    checkpoint(4, "*", [-142.9, 140.2, -57.6])
                    checkpoint(5, "*", [4.6, 56, 191.6])
                    checkpoint(6,"end", [-37.9, 1.74, -26.7])

                if guildhall_name.get() == "RACE Downhill":
                    #race Checkpoints
                    checkpoint(-1,"reset", [35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [105, 453, 152])
                    checkpoint(1, "*", [75, 388, 132]) #el saltito
                    checkpoint(2, "*", [207, 278,-271]) #las dos aguilas
                    checkpoint(3, "*", [-271, 69, 43]) #estructura parecida al puente
                    checkpoint(4, "end", [-90, 6,-283])

                if guildhall_name.get() == "RACE Hillclimb":
                    #race Checkpoints
                    checkpoint(-1,"reset", [35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [-66, 6, -275])
                    checkpoint(1, "*", [-271, 69, 43]) #estructura parecida al puente
                    checkpoint(2, "*", [225, 285, -145]) #equivalente a las aguilas
                    checkpoint(3, "*", [-123, 385, 301]) #equivalente a las aguilas
                    checkpoint(4, "end", [68,453,110])

                if guildhall_name.get() == "RACE Full Mountain Run":
                    #race Checkpoints
                    checkpoint(-1,"reset", [35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [18.96, 453, 85.98])
                    checkpoint(1, "*", [-81.6, 380.74, 104.90]) 
                    checkpoint(2, "*", [207, 278, -271]) 
                    checkpoint(3, "*", [177.9, 99.84, 236.9])
                    checkpoint(4, "*", [-158.3, 3, -284.8])
                    checkpoint(5, "*", [281.3, 107.9, 245.1])
                    checkpoint(6, "*", [116.2, 246.4, -170.9])
                    checkpoint(7, "*", [-29.9, 380.5, 141.9])
                    checkpoint(8, "end", [27.91, 453, 41.5])

                if guildhall_name.get() == "EQE":
                    #eqe Checkpoints
                    checkpoint(-1,"reset", [114.48, 9.07, 37.47]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [186.02, 140.6, 198.7])
                    checkpoint(1, "*", [-78.8, 23.9, -94.5])
                    checkpoint(2, "*", [104, 142.6, -44])
                    checkpoint(3, "*", [-207, 122, -41])
                    checkpoint(4, "end", [117, 158, 256])

                if guildhall_name.get() == "SoTD":
                    #SoTD Checkpoints
                    checkpoint(-1,"reset", [3.18, 61.32, -35.58]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [93.41, 512.07, -6.85])
                    checkpoint(1, "*", [-39.83, -0.34, 74.95])
                    checkpoint(2, "*", [5.39, 88.43, 170.73])
                    checkpoint(3, "*", [-62.09, 242.28, -251.58])
                    checkpoint(4, "*", [369.351, 396.35, 91.34])
                    checkpoint(5, "end", [61.96, 512.09, -58.64])

                if guildhall_name.get() == "LRS":
                    #SoTD Checkpoints
                    checkpoint(-1,"reset", [3.18, 61.32, -35.58]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [25.83, 575.20, -14.51])
                    checkpoint(1, "*", [182.53, 488.21, 59.85])
                    checkpoint(2, "*", [203.48, 261.82, -96.09])
                    checkpoint(3, "*", [-0.6, 19.45, -254.91])
                    checkpoint(4, "*", [-101.72, 53.04, 244.96])
                    checkpoint(5, "end", [-26.74, 0.55, -51.33])

                if guildhall_name.get() == "HUR":
                    #HUR Checkpoints
                    checkpoint(-1,"reset", [35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [42.57, 103.83, -282.71])
                    checkpoint(1, "*", [-253.95, 162.94, 284.7])
                    checkpoint(2, "*", [81.8, 0.56, -323.83])
                    checkpoint(3, "*", [293.64, 60.74, -49.93])
                    checkpoint(4, "*", [113.59, 154.99, -62.03])
                    checkpoint(5, "*", [97.33, 221.3, 278.31])
                    checkpoint(6,"end", [42.5, 103.87, -187.45])

                if guildhall_name.get() == "TYRIA INF.LEAP":
                    checkpoint(0,"start", [172.08766174316406,6.024808883666992,-547.970458984375])
                    checkpoint(-1,"reset", [239.65151977539062,2.9369618892669678,-550.4412231445312])
                    checkpoint(1,"*", [29.13327980041504,55.82658004760742,-583.2632446289062])
                    checkpoint(2,"*", [-51.2392692565918,79.49896240234375,-379.94647216796875])
                    checkpoint(3,"*", [-9.615543365478516,78.45231628417969,-309.3282470703125])
                    checkpoint(4,"*", [-48.472530364990234,62.86130142211914,-106.99578094482422])
                    checkpoint(5,"*", [-100.83071899414062,71.53402709960938,52.68389129638672])
                    checkpoint(6,"*", [-91.94183349609375,61.61763381958008,112.29816436767578])
                    checkpoint(7,"*", [-147.08193969726562,71.2541275024414,198.99038696289062])
                    checkpoint(8,"*", [-417.5687561035156,74.10258483886719,162.71331787109375])
                    checkpoint(9,"*", [-488.59130859375,71.60765838623047,27.125934600830078])
                    checkpoint(10,"*", [-427.56011962890625,52.862422943115234,-114.37564849853516])
                    checkpoint(11,"*", [-320.72216796875,9.928861618041992,-265.4931335449219])
                    checkpoint(12,"*", [-46.586875915527344,51.671600341796875,-164.40892028808594])
                    checkpoint(13,"*", [50.92682647705078,42.65714645385742,-338.25128173828125])
                    checkpoint(14,"end",[166.60678100585938,1.3314199447631836,-490.23712158203125])


                if guildhall_name.get() == "TYRIA DIESSA PLATEAU":
                    checkpoint(0,"start", [-104.83451843261719,27.776851654052734,-524.923828125])
                    checkpoint(-1,"reset", [-147.5781707763672,32.125404357910156,-532.2943725585938])
                    checkpoint(1,"*", [1.1407662630081177,19.605104446411133,-578.863037109375])
                    checkpoint(2,"*", [676.86279296875,20.384946823120117,-336.33447265625])
                    checkpoint(3,"*", [703.8831787109375,26.951656341552734,260.63909912109375])
                    checkpoint(4,"*", [609.3909301757812,24.277347564697266,369.7010803222656])
                    checkpoint(5,"*", [369.9383239746094,3.642069101333618,270.60150146484375])
                    checkpoint(6,"*", [504.962646484375,27.541580200195312,35.69978713989258])
                    checkpoint(7,"*", [233.28945922851562,38.541439056396484,-69.48370361328125])
                    checkpoint(8,"*", [132.38165283203125,17.785154342651367,2.164975166320801])
                    checkpoint(9,"*", [-432.2799987792969,42.51692199707031,-42.65890121459961])
                    checkpoint(10,"*", [-357.3988952636719,41.89646530151367,-167.71923828125])
                    checkpoint(11,"*", [-401.38409423828125,28.78837013244629,-361.96881103515625])
                    checkpoint(12,"end",[-161.61705017089844,30.59449577331543,-507.6558532714844])

                if guildhall_name.get() == "TYRIA SNOWDEN DRIFTS":
                    checkpoint(0,"start", [241.68540954589844,21.559755325317383,-125.37120819091797])
                    checkpoint(-1,"reset", [261.70538330078125,35.725868225097656,-59.49063491821289])
                    checkpoint(1,"*", [-5.7246994972229,80.48108673095703,-242.01596069335938])
                    checkpoint(2,"*", [-75.52835845947266,48.116947174072266,-86.60132598876953])
                    checkpoint(3,"*", [-28.39924430847168,59.33915710449219,-12.004525184631348])
                    checkpoint(4,"*", [73.7730941772461,52.45607376098633,-35.24717712402344])
                    checkpoint(5,"*", [199.7474365234375,27.030221939086914,29.305269241333008])
                    checkpoint(6,"*", [333.5821228027344,31.937904357910156,96.81157684326172])
                    checkpoint(7,"*", [324.86370849609375,36.481956481933594,-15.774405479431152])
                    checkpoint(8,"end",[253.3621826171875,26.54821014404297,-98.40397644042969])

                if guildhall_name.get() == "TYRIA GENDARRAN":
                    checkpoint(0,"start", [233.21591186523438,8.56054401397705,477.771240234375])
                    checkpoint(-1,"reset", [308.26007080078125,35.16044998168945,515.2572021484375])
                    checkpoint(1,"*", [-108.59925079345703,16.908260345458984,340.125244140625])
                    checkpoint(2,"*", [-220.9199981689453,28.74785041809082,-32.014652252197266])
                    checkpoint(3,"*", [-307.2057189941406,7.515278339385986,-235.68634033203125])
                    checkpoint(4,"*", [-173.0546417236328,5.826416492462158,-436.0346984863281])
                    checkpoint(5,"*", [-59.84772872924805,13.091215133666992,-420.60833740234375])
                    checkpoint(6,"*", [439.3578796386719,9.453458786010742,-430.45904541015625])
                    checkpoint(7,"*", [491.85968017578125,1.7009484767913818,-160.43212890625])
                    checkpoint(8,"*", [521.2687377929688,11.1598482131958,-70.7208023071289])
                    checkpoint(9,"*", [604.9369506835938,8.81571102142334,-21.48897933959961])
                    checkpoint(10,"*", [581.4658813476562,24.684406280517578,275.7775573730469])
                    checkpoint(11,"*", [461.9334716796875,50.010581970214844,373.51275634765625])
                    checkpoint(12,"*", [355.84332275390625,2.554835557937622,456.06304931640625])
                    checkpoint(13,"end",[289.72845458984375,12.304443359375,464.3570556640625])

                if guildhall_name.get() == "TYRIA BRISBAN WILD.":
                    checkpoint(0,"start", [-799.442138671875,65.7823257446289,355.7180480957031])
                    checkpoint(-1,"reset", [-851.652587890625,66.03923797607422,391.6478576660156])
                    checkpoint(1,"*", [-699.8272705078125,23.893230438232422,-44.24618911743164])
                    checkpoint(2,"*", [-611.359619140625,40.56562423706055,-113.68000030517578])
                    checkpoint(3,"*", [-618.2125244140625,27.34697151184082,-303.1869201660156])
                    checkpoint(4,"*", [-393.02789306640625,4.553216934204102,-559.7305908203125])
                    checkpoint(5,"*", [-299.12213134765625,27.9654541015625,-435.876953125])
                    checkpoint(6,"*", [-377.175048828125,20.820322036743164,-267.90020751953125])
                    checkpoint(7,"*", [33.68626022338867,43.313297271728516,-233.00523376464844])
                    checkpoint(8,"*", [258.9540710449219,46.97104263305664,-222.0779266357422])
                    checkpoint(9,"*", [326.4122314453125,41.9850959777832,-387.8382873535156])
                    checkpoint(10,"*", [300.7703857421875,28.654491424560547,-543.6235961914062])
                    checkpoint(11,"*", [357.5238952636719,35.345149993896484,-630.9033203125])
                    checkpoint(12,"*", [665.6546630859375,55.883975982666016,-568.7774047851562])
                    checkpoint(13,"*", [851.6265258789062,45.196346282958984,-61.594444274902344])
                    checkpoint(14,"*", [824.1830444335938,78.1462631225586,324.7612609863281])
                    checkpoint(15,"*", [865.7689208984375,41.68893051147461,525.5531616210938])
                    checkpoint(16,"*", [496.33392333984375,92.67289733886719,552.6304321289062])
                    checkpoint(17,"*", [99.04247283935547,66.29413604736328,605.229248046875])
                    checkpoint(18,"*", [-47.385406494140625,-0.24002154171466827,603.7735595703125])
                    checkpoint(19,"*", [-133.09849548339844,0.28277185559272766,690.7421875])
                    checkpoint(20,"*", [-558.9813232421875,43.84546661376953,622.4324340820312])
                    checkpoint(21,"*", [-702.5592651367188,63.19841766357422,536.9096069335938])
                    checkpoint(22,"end",[-826.1544189453125,66.1941909790039,445.2254333496094])

                if guildhall_name.get() == "TYRIA GROTHMAR VALLEY":
                    checkpoint(0,"start", [465.6228332519531,27.168245315551758,258.44146728515625])
                    checkpoint(-1,"reset", [515.8200073242188,20.60076332092285,151.648681640625])
                    checkpoint(1,"*", [332.18426513671875,64.0356674194336,328.2277526855469])
                    checkpoint(2,"*", [-233.25413513183594,25.687461853027344,364.53253173828125])
                    checkpoint(3,"*", [-286.15069580078125,2.4846606254577637,246.47425842285156])
                    checkpoint(4,"*", [-32.641300201416016,21.47239112854004,140.7539825439453])
                    checkpoint(5,"*", [-61.54493713378906,15.462581634521484,45.632171630859375])
                    checkpoint(6,"*", [-426.6194763183594,54.90696716308594,-77.02539825439453])
                    checkpoint(7,"*", [-494.7391357421875,103.20759582519531,-274.52392578125])
                    checkpoint(8,"*", [-400.7825622558594,77.3409652709961,-315.7843933105469])
                    checkpoint(9,"*", [-289.7224426269531,29.51124382019043,-258.2286682128906])
                    checkpoint(10,"*", [-140.0670623779297,15.343700408935547,-632.8471069335938])
                    checkpoint(11,"*", [-74.65828704833984,42.41508102416992,-607.2628173828125])
                    checkpoint(12,"*", [85.6784896850586,54.044246673583984,-375.0093688964844])
                    checkpoint(13,"*", [235.5856475830078,34.27231216430664,-275.458984375])
                    checkpoint(14,"*", [378.7042541503906,15.718698501586914,29.149442672729492])
                    checkpoint(15,"*", [494.23297119140625,-0.06953207403421402,117.8377456665039])
                    checkpoint(16,"*", [583.8775024414062,18.935264587402344,246.39712524414062])
                    checkpoint(17,"end",[507.4120788574219,16.257854461669922,193.37490844726562])

                if guildhall_name.get() == "OLLO Akina":
                    checkpoint(-1,"reset", [114, 9,37]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [-387, 997, -273.4])
                    checkpoint(1, "*", [97.3, 842.8, -75])
                    checkpoint(2, "end", [-314, 997, -378.2])

                if guildhall_name.get() == "OLLO Shortcut":

                    checkpoint(0,"start",[24.269977569580078,16.183862686157227,-40.50206756591797])
                    checkpoint(1,"*",[9.049388885498047,39.9488525390625,82.58651733398438])
                    checkpoint(2,"*",[-11.155280113220215,40.044132232666016,289.6002502441406])
                    checkpoint(3,"*",[99.26748657226562,23.069229125976562,192.68919372558594])
                    checkpoint(4,"*",[98.61570739746094,23.08808135986328,282.6737365722656])
                    checkpoint(5,"*",[139.25704956054688,42.244361877441406,346.36370849609375])
                    checkpoint(6,"*",[205.88778686523438,29.56764030456543,217.02557373046875])
                    checkpoint(7,"*",[208.2991485595703,36.79213333129883,5.360412120819092])
                    checkpoint(8,"end",[109.66463470458984,36.829837799072266,-21.301481246948242])
                    checkpoint(-1,"reset", [114.61094665527344,9.075913429260254,37.21352005004883])

                if guildhall_name.get() == "VAW Left path":
                    checkpoint(-1,"reset", [35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [-293.9,  525.1,  293.7])
                    checkpoint(1, "end", [-255.1, 3.8, 303.8])

                if guildhall_name.get() == "VAW Right path":
                    checkpoint(-1,"reset", [35.67, 111.35, -7.02]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [-293.9,  525.1,  293.7])
                    checkpoint(1, "end", [-255.1, 3.8, 303.8])

                if guildhall_name.get() == "GeeK":
                    checkpoint(-1,"reset", [114, 9,37]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [89, 50.4, 67.67])
                    checkpoint(1, "end", [206.5, 62.9, 141.5])
                
                if guildhall_name.get() == "UAoT":
                    #UAoT Checkpoints
                    checkpoint(-1,"reset", [114.48, 9.07, 37.47]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [179, 96, 183.5])
                    checkpoint(1, "*", [-150, 59, 321])
                    checkpoint(2, "*", [27, 237, -80])
                    checkpoint(3, "*", [230, 19, -226])
                    checkpoint(4, "end", [302, 96, 215])
                
                if guildhall_name.get() == "INDI":
                    checkpoint(-1,"reset", [3.1, 61, -35]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [0, 730.6,-43])
                    checkpoint(1, "end", [0.5, 59, -115])

                if guildhall_name.get() == "DRFT-1 Fractal Actual Speedway":
                    checkpoint(-1,"reset", [-156, 31, 431]) # use this position when you take te map TP , to stop log file
                    checkpoint(0, "start", [-117, 22, 348])
                    checkpoint(1, "*", [144,25,-271])
                    checkpoint(1, "*", [143,25,-281])
                    checkpoint(1, "*", [142,25,-291])
                    checkpoint(2, "*", [-179,11,95])
                    checkpoint(3, "*", [-271,13,279])
                    checkpoint(4, "end", [-178, 22, 391])

                if guildhall_name.get() == "DRFT-2 Wayfar Out":
                    checkpoint(0,"start",[236.18545532226562,182.43496704101562,1193.39501953125])
                    checkpoint(1,"*",[119.91375732421875,108.96684265136719,965.742919921875])
                    checkpoint(2,"*",[-193.8041229248047,137.92950439453125,845.072998046875])
                    checkpoint(3,"*",[-198.61849975585938,102.17216491699219,474.2681884765625])
                    checkpoint(4,"*",[243.06484985351562,87.04293060302734,244.41075134277344])
                    checkpoint(5,"*",[300.2074890136719,14.289880752563477,29.330516815185547])
                    checkpoint(6,"*",[-16.304609298706055,28.552560806274414,-257.130126953125])
                    checkpoint(7,"*",[-249.95533752441406,74.66495513916016,-399.3951721191406])
                    checkpoint(8,"*",[18.190637588500977,25.067520141601562,-869.16259765625])
                    checkpoint(9,"end",[70.45439910888672,8.777570724487305,-1082.09912109375])
                    checkpoint(-1,"reset", [264.8414001464844,197.06907653808594,1235.7269287109375])

                if guildhall_name.get() == "DRFT-3 Summers Sunset":
                    checkpoint(0,"start",[-117.07197570800781,-0.026282841339707375,202.3591766357422])
                    checkpoint(1,"*",[334.6391906738281,14.71496868133545,195.56500244140625])
                    checkpoint(2,"*",[473.8343811035156,3.5347018241882324,196.9063262939453])
                    checkpoint(3,"*",[685.062744140625,0.3344975411891937,165.6804656982422])
                    checkpoint(4,"*",[609.5730590820312,1.0014756917953491,-26.836214065551758])
                    checkpoint(5,"*",[623.8477172851562,0.609783947467804,-257.33380126953125])
                    checkpoint(6,"*",[591.6400146484375,-0.32482725381851196,-460.17620849609375])
                    checkpoint(7,"*",[370.8766784667969,-0.5230938792228699,-879.7811889648438])
                    checkpoint(8,"*",[-133.28067016601562,0.1356085240840912,-898.5278930664062])
                    checkpoint(9,"*",[-413.52783203125,5.071121692657471,-240.91851806640625])
                    checkpoint(10,"*",[-204.90223693847656,0.7035499811172485,-80.8447265625])
                    checkpoint(11,"end",[-162.6918487548828,3.4913501739501953,100.76415252685547])
                    checkpoint(-1,"reset", [545.7351684570312,0.991686999797821,145.00607299804688])


                if guildhall_name.get() == "DRFT-4 Mossheart Memory":
                    checkpoint(0,"start",[770.6901245117188,61.681766510009766,-555.9796752929688])
                    checkpoint(1,"*",[932.1886596679688,50.579689025878906,-471.4723815917969])
                    checkpoint(2,"*",[769.68603515625,35.71115493774414,-330.1717529296875])
                    checkpoint(3,"*",[679.4821166992188,51.92412185668945,-560.703125])
                    checkpoint(4,"*",[369.9617919921875,33.695064544677734,-630.2423095703125])
                    checkpoint(5,"*",[321.8377685546875,35.29410171508789,-404.81536865234375])
                    checkpoint(6,"*",[35.278564453125,42.79775619506836,-225.3185272216797])
                    checkpoint(7,"*",[-355.0137939453125,41.88217544555664,-97.36225128173828])
                    checkpoint(8,"*",[-202.68838500976562,47.71106719970703,-12.467292785644531])
                    checkpoint(9,"*",[275.9913635253906,29.38922691345215,-427.5582275390625])
                    checkpoint(10,"*",[370.9323425292969,33.57604217529297,-629.8128662109375])
                    checkpoint(11,"end",[656.0433959960938,51.61550521850586,-575.2821655273438])
                    checkpoint(-1,"reset", [252.3805389404297,52.90296936035156,-636.0989379882812])

                if guildhall_name.get() == "DRFT-5 Roller Coaster Canyon":
                    checkpoint(0,"start",[189.24212646484375,38.04368209838867,412.3811340332031])
                    checkpoint(1,"*",[-70.00048065185547,30.43256950378418,451.5010986328125])
                    checkpoint(2,"*",[-52.569393157958984,37.93097686767578,250.85276794433594])
                    checkpoint(3,"*",[-6.233772277832031,111.81794738769531,83.85763549804688])
                    checkpoint(4,"*",[202.64353942871094,46.57558059692383,1.6096469163894653])
                    checkpoint(5,"*",[313.4672546386719,59.56179428100586,-203.94168090820312])
                    checkpoint(6,"*",[763.8953857421875,82.28750610351562,-248.554443359375])
                    checkpoint(7,"*",[861.5894165039062,-0.11061082780361176,150.6088409423828])
                    checkpoint(8,"*",[885.3433227539062,-0.2789803743362427,409.9283447265625])
                    checkpoint(9,"*",[1037.5267333984375,-0.34036582708358765,551.0679321289062])
                    checkpoint(10,"*",[1076.2242431640625,13.433802604675293,430.6039123535156])
                    checkpoint(11,"*",[796.7359619140625,41.71104049682617,468.15771484375])
                    checkpoint(12,"end",[352.8476867675781,45.145347595214844,425.576416015625])
                    checkpoint(-1,"reset", [243.18453979492188,78.04730987548828,521.9669189453125])


                if guildhall_name.get() == "DRFT-6 Centurion Circuit":
                    checkpoint(0,"start",[81.60356140136719,169.28707885742188,149.9441680908203])
                    checkpoint(1,"*",[110.7217025756836,169.14312744140625,376.41265869140625])
                    checkpoint(2,"*",[111.17762756347656,139.6862335205078,477.0283508300781])
                    checkpoint(3,"*",[-255.87911987304688,57.80933380126953,502.0262756347656])
                    checkpoint(4,"*",[-176.75387573242188,7.059552192687988,314.19964599609375])
                    checkpoint(5,"*",[-288.5499572753906,3.7643115520477295,-97.32538604736328])
                    checkpoint(6,"*",[-75.8969497680664,13.366032600402832,-146.5823974609375])
                    checkpoint(7,"*",[-22.72895622253418,104.4173812866211,-1.7704955339431763])
                    checkpoint(8,"end",[20.252696990966797,168.30413818359375,86.17316436767578])
                    checkpoint(-1,"reset", [81.61611938476562,168.58372497558594,47.076927185058594])


                if guildhall_name.get() == "DRFT-7 Dredgehaunt Cliffs":
                    checkpoint(0,"start",[-184.38546752929688,64.9686508178711,-627.9636840820312])
                    checkpoint(1,"*",[-364.6119079589844,82.46500396728516,-591.880126953125])
                    checkpoint(2,"*",[-337.85821533203125,39.892425537109375,-701.2764892578125])
                    checkpoint(3,"*",[-180.5691375732422,63.36720657348633,-721.6331176757812])
                    checkpoint(4,"*",[-7.6090593338012695,56.80658721923828,-794.8373413085938])
                    checkpoint(5,"*",[167.4985809326172,50.757049560546875,-545.6727294921875])
                    checkpoint(6,"*",[138.0374755859375,70.06675720214844,-493.1942443847656])
                    checkpoint(7,"end",[-46.31200408935547,60.5682258605957,-566.6380615234375])
                    checkpoint(-1,"reset", [9.354050636291504,65.31747436523438,-751.1548461914062])


                if guildhall_name.get() == "DRFT-8 Icy Rising Ramparts":
                    checkpoint(0,"start",[702.6351928710938,60.39939498901367,372.7860107421875])
                    checkpoint(1,"*",[840.886474609375,41.5600700378418,200.27175903320312])
                    checkpoint(2,"*",[769.0579223632812,54.74429702758789,51.941104888916016])
                    checkpoint(3,"*",[444.1422119140625,32.01011276245117,109.65090942382812])
                    checkpoint(4,"*",[131.88671875,50.89085006713867,50.434326171875])
                    checkpoint(5,"*",[217.90818786621094,74.62855529785156,226.0938720703125])
                    checkpoint(6,"end",[575.1735229492188,58.270286560058594,365.3240661621094])
                    checkpoint(-1,"reset", [650.6351928710938,61.81232833862305,520.927001953125])

                if guildhall_name.get() == "DRFT-9 Soulthirst Savannah of Svanier":
                    checkpoint(0,"start",[803.3325805664062,136.01504516601562,153.9782257080078])
                    checkpoint(1,"*",[994.793212890625,58.54420852661133,-29.675212860107422])
                    checkpoint(2,"*",[726.4783325195312,98.12777709960938,-75.74417114257812])
                    checkpoint(3,"*",[702.5076904296875,106.40855407714844,-20.23108673095703])
                    checkpoint(4,"*",[914.1011962890625,86.15933227539062,0.9789632558822632])
                    checkpoint(5,"*",[817.55029296875,113.25086975097656,232.247802734375])
                    checkpoint(6,"*",[726.7265014648438,128.68972778320312,251.99386596679688])
                    checkpoint(7,"end",[724.0528564453125,137.1461639404297,214.591064453125])
                    checkpoint(-1,"reset", [1127.3040771484375,47.6551399230957,-118.5078125])


                if guildhall_name.get() == "DRFT-10 Toxic Turnpike":
                    checkpoint(0,"start",[478.70538330078125,32.394351959228516,593.5602416992188])
                    checkpoint(1,"*",[425.78375244140625,30.675657272338867,734.249267578125])
                    checkpoint(2,"*",[253.68408203125,13.492131233215332,703.203125])
                    checkpoint(3,"*",[269.7676086425781,1.9378552436828613,316.82672119140625])
                    checkpoint(4,"*",[387.2690124511719,63.51634979248047,55.66465377807617])
                    checkpoint(5,"*",[562.5924072265625,35.866424560546875,7.624796390533447])
                    checkpoint(6,"*",[612.9382934570312,83.97993469238281,155.996826171875])
                    checkpoint(7,"*",[627.3564453125,79.93864440917969,373.3465881347656])
                    checkpoint(8,"end",[557.4955444335938,52.8920783996582,464.1280822753906])
                    checkpoint(-1,"reset", [485.0301208496094,37.27165603637695,539.51708984375])


                if guildhall_name.get() == "DRFT-11 Estuary of Twilight":
                    checkpoint(0,"start",[-158.1619110107422,28.030956268310547,724.9016723632812])
                    checkpoint(1,"*",[-61.81842803955078,10.977461814880371,939.747314453125])
                    checkpoint(2,"*",[183.70884704589844,11.293512344360352,1079.24169921875])
                    checkpoint(3,"*",[248.54811096191406,9.358901977539062,941.6489868164062])
                    checkpoint(4,"*",[18.913454055786133,1.8325788974761963,993.8555908203125])
                    checkpoint(5,"*",[-80.55955505371094,3.1585092544555664,1055.0838623046875])
                    checkpoint(6,"*",[-243.66128540039062,1.2709424495697021,1019.9541625976562])
                    checkpoint(7,"end",[-187.4603271484375,19.422760009765625,668.4896850585938])
                    checkpoint(-1,"reset", [-213.1799774169922,55.91027069091797,446.1829528808594])


                if guildhall_name.get() == "DRFT-12 Celedon Circle":
                    checkpoint(0,"start",[-77.15221405029297,2.23431658744812,-1019.9838256835938])
                    checkpoint(1,"*",[101.35590362548828,7.339758396148682,-1080.101318359375])
                    checkpoint(2,"*",[282.3252258300781,5.095705986022949,-1023.9260864257812])
                    checkpoint(3,"*",[188.30189514160156,0.4303003251552582,-808.58740234375])
                    checkpoint(4,"*",[38.39978790283203,18.88983154296875,-668.1705322265625])
                    checkpoint(5,"*",[-39.359962463378906,9.778656005859375,-722.13916015625])
                    checkpoint(6,"end",[-68.65498352050781,-0.2025335431098938,-932.6437377929688])
                    checkpoint(-1,"reset", [-173.44895935058594,4.851062774658203,-1010.41650390625])


                if guildhall_name.get() == "DRFT-13 Thermo Reactor Escape":
                    checkpoint(0,"start",[279.7813415527344,34.551063537597656,290.5838928222656])
                    checkpoint(1,"*",[547.1992797851562,19.02662467956543,405.10009765625])
                    checkpoint(2,"*",[187.2203369140625,39.40522003173828,467.0896301269531])
                    checkpoint(3,"*",[17.029438018798828,19.717058181762695,334.06427001953125])
                    checkpoint(4,"*",[-229.64370727539062,12.694239616394043,453.90576171875])
                    checkpoint(5,"*",[-367.4956359863281,7.273587226867676,621.5048828125])
                    checkpoint(6,"*",[-370.50714111328125,24.50360107421875,805.6455688476562])
                    checkpoint(7,"*",[-236.3816375732422,-0.20320039987564087,847.4727172851562])
                    checkpoint(8,"*",[-173.07815551757812,25.64794921875,508.05267333984375])
                    checkpoint(9,"*",[-67.14794158935547,11.553140640258789,327.2286682128906])
                    checkpoint(10,"end",[181.4370880126953,27.945026397705078,239.04833984375])
                    checkpoint(-1,"reset", [166.6081085205078,32.82973861694336,271.2810363769531])

                if guildhall_name.get() == "DRFT-14 Jormags Jumpscare":
                    checkpoint(0,"start",[569.9375610351562,50.231842041015625,465.77166748046875])
                    checkpoint(1,"*",[327.5111083984375,37.00214767456055,409.0692138671875])
                    checkpoint(2,"*",[168.40768432617188,37.03746032714844,337.578125])
                    checkpoint(3,"*",[209.5767364501953,92.88089752197266,154.71066284179688])
                    checkpoint(4,"*",[100.67471313476562,76.22732543945312,-380.8691711425781])
                    checkpoint(5,"*",[167.1279296875,115.92082214355469,-564.3450927734375])
                    checkpoint(6,"*",[342.7794494628906,113.67243957519531,-641.1884765625])
                    checkpoint(7,"*",[290.9875183105469,99.20130920410156,-366.7642517089844])
                    checkpoint(8,"*",[355.0185546875,130.84153747558594,-234.8645782470703])
                    checkpoint(9,"*",[435.31292724609375,73.08574676513672,-56.45564651489258])
                    checkpoint(10,"*",[470.2713317871094,25.34433937072754,168.29811096191406])
                    checkpoint(11,"*",[594.4365844726562,21.244632720947266,305.04095458984375])
                    checkpoint(12,"end",[661.1888427734375,39.34746551513672,462.04925537109375])
                    checkpoint(-1,"reset", [741.5009765625,127.52398681640625,771.8026123046875])

                if guildhall_name.get() == "DRFT-GP-1 Lions Summer Sights":
                    checkpoint(0,"start",[-291.50177001953125,33.43931198120117,-365.4147033691406])
                    checkpoint(1,"*",[22.172447204589844,36.463619232177734,-306.20770263671875])
                    checkpoint(2,"*",[216.31475830078125,30.973173141479492,-336.59539794921875])
                    checkpoint(3,"*",[378.82159423828125,12.987125396728516,-184.07696533203125])
                    checkpoint(4,"*",[428.25018310546875,0.8933775424957275,14.895291328430176])
                    checkpoint(5,"*",[433.9792175292969,6.8723907470703125,284.9019775390625])
                    checkpoint(6,"*",[307.42926025390625,23.06127166748047,278.4302978515625])
                    checkpoint(7,"*",[255.7796173095703,22.937456130981445,196.2340087890625])
                    checkpoint(8,"*",[75.72550964355469,28.31073570251465,259.300537109375])
                    checkpoint(9,"*",[-137.1382293701172,20.434810638427734,251.7682342529297])
                    checkpoint(10,"*",[-426.54852294921875,3.5873279571533203,263.56951904296875])
                    checkpoint(11,"*",[-505.60748291015625,-0.7064051628112793,21.56854820251465])
                    checkpoint(12,"*",[-584.4908447265625,33.917808532714844,-89.221435546875])
                    checkpoint(13,"*",[-422.3626708984375,9.026193618774414,111.91932678222656])
                    checkpoint(14,"*",[-373.8471374511719,3.470728874206543,263.1591491699219])
                    checkpoint(15,"*",[-47.79479217529297,21.424884796142578,267.87060546875])
                    checkpoint(16,"*",[194.29788208007812,36.526126861572266,215.05055236816406])
                    checkpoint(17,"*",[337.1695861816406,21.519868850708008,293.462646484375])
                    checkpoint(18,"*",[450.2850036621094,0.04633375257253647,254.8535919189453])
                    checkpoint(19,"*",[423.9905700683594,-0.5120408535003662,-17.82129669189453])
                    checkpoint(20,"*",[418.01312255859375,8.600109100341797,-162.09478759765625])
                    checkpoint(21,"*",[194.4971160888672,30.973176956176758,-322.2392578125])
                    checkpoint(22,"*",[-23.896034240722656,37.33087921142578,-320.6465148925781])
                    checkpoint(23,"end",[-216.6181182861328,31.319185256958008,-353.88165283203125])
                    checkpoint(-1,"reset", [-92.85139465332031,9.955810546875,-223.57749938964844])
                if guildhall_name.get() == "DRFT-GP-2 Sandswept Shore Sprint":
                    checkpoint(0,"start",[-544.0419921875,0.31721049547195435,1014.862060546875])
                    checkpoint(1,"*",[-311.1061706542969,3.732792854309082,750.316162109375])
                    checkpoint(2,"*",[-168.55824279785156,1.6326221227645874,735.5054931640625])
                    checkpoint(3,"*",[-28.18683624267578,3.6100552082061768,550.9224243164062])
                    checkpoint(4,"*",[87.91732788085938,0.5940253138542175,494.3864440917969])
                    checkpoint(5,"*",[342.45745849609375,-0.14637383818626404,509.168701171875])
                    checkpoint(6,"*",[681.2310791015625,0.7173949480056763,653.148193359375])
                    checkpoint(7,"*",[686.1966552734375,0.09021551162004471,930.7727661132812])
                    checkpoint(8,"*",[679.3375854492188,0.7372751235961914,653.7467651367188])
                    checkpoint(9,"*",[310.86383056640625,2.744239330291748,514.2866821289062])
                    checkpoint(10,"*",[46.38405227661133,0.1685870736837387,495.5599060058594])
                    checkpoint(11,"*",[-105.0680923461914,6.339461326599121,653.8186645507812])
                    checkpoint(12,"*",[-400.7470397949219,0.9481762051582336,780.3505249023438])
                    checkpoint(13,"end",[-502.1472473144531,1.6342060565948486,910.4564208984375])
                    checkpoint(-1,"reset", [-99.79989624023438,7.133966445922852,709.6367797851562])
                if guildhall_name.get() == "DRFT-GP-3 Inquest Isle Invasion":

                    checkpoint(0,"start",[-153.13572692871094,2.3076281547546387,-77.4347152709961])
                    checkpoint(1,"*",[-163.57579040527344,0.9244344234466553,169.5970916748047])
                    checkpoint(2,"*",[497.6688537597656,-0.15405692160129547,188.75460815429688])
                    checkpoint(3,"*",[607.784423828125,1.0246295928955078,-34.34113693237305])
                    checkpoint(4,"*",[594.784423828125,-0.3246295928955078,-203.34113693237305])
                    checkpoint(5,"*",[403.7969970703125,-0.18220704793930054,-529.399169921875])
                    checkpoint(6,"*",[263.2414855957031,0.27951872944831848,-669.9658203125])
                    checkpoint(7,"*",[97.99069213867188,-0.518017053604126,-930.4939575195312])
                    checkpoint(8,"*",[-403.6644592285156,-0.40145934224128723,-593.4263000488281])
                    checkpoint(9,"*",[-472.6644592285156,-0.30145934224128723,-370.4263000488281])
                    checkpoint(10,"end",[-223.18630981445312,0.7399634122848511,-81.19659423828125])
                    checkpoint(-1,"reset", [521.0791015625,8.74111557006836,120.58473205566406])
                if guildhall_name.get() == "DRFT-GP-4 Triple Trek Periphery":
                    checkpoint(0,"start",[142.01397705078125,2.7381067276000977,-43.56310272216797])
                    checkpoint(1,"*",[32.260528564453125,0.9025144577026367,9.47095012664795])
                    checkpoint(2,"*",[-173.63543701171875,3.380297899246216,-288.3064270019531])
                    checkpoint(3,"*",[-114.51219940185547,12.092617988586426,-444.6318664550781])
                    checkpoint(4,"*",[55.57835006713867,5.305901050567627,-596.287109375])
                    checkpoint(5,"*",[288.112548828125,0.8734909892082214,-581.1058349609375])
                    checkpoint(6,"*",[545.3038940429688,34.874671936035156,-184.90989685058594])
                    checkpoint(7,"*",[348.4444885253906,1.4226492643356323,-95.94324493408203])
                    checkpoint(8,"end",[234.2526397705078,2.7598352432250977,-83.74826049804688])
                    checkpoint(-1,"reset", [151.7235870361328,8.812746047973633,-92.4794692993164])
                if guildhall_name.get() == "DRFT-GP-5 Beachin Crabwalk":
                    checkpoint(0,"start",[-383.92169189453125,46.209877014160156,-235.84828186035156])
                    checkpoint(1,"*",[-122.37680053710938,39.26274490356445,-247.13525390625])
                    checkpoint(2,"*",[94.57499694824219,0.8819980621337891,-192.31317138671875])
                    checkpoint(3,"*",[225.81768798828125,-0.7168354392051697,-85.63114929199219])
                    checkpoint(4,"*",[267.88330078125,-0.3114772439002991,211.86936950683594])
                    checkpoint(5,"*",[484.4364929199219,-0.30362629890441895,320.18316650390625])
                    checkpoint(6,"*",[574.8967895507812,34.887596130371094,-0.5284920930862427])
                    checkpoint(7,"*",[423.9496154785156,50.69232940673828,-123.71199035644531])
                    checkpoint(8,"*",[223.737548828125,48.37929916381836,-83.23470306396484])
                    checkpoint(9,"*",[107.25992584228516,43.245182037353516,32.137298583984375])
                    checkpoint(10,"*",[-123.32205963134766,39.122764587402344,-247.27691650390625])
                    checkpoint(11,"*",[-285.9521789550781,52.25719451904297,-188.34300231933594])
                    checkpoint(12,"end",[-417.37591552734375,44.911865234375,-181.865478515625])
                    checkpoint(-1,"reset", [-539.3897094726562,31.712434768676758,-411.2883605957031])
                



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

                if True:
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
                    if speed_in_3D == 1:
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

                            if hud_max_speed:
                                
                                aa = int(angle_between_res2)
                                bb = 0

                                if aa < -90:
                                    bb = (72) 
                                elif aa >= -90 and aa < -45:
                                    bb = (((aa+90) * (aa+90)) / 50) 
                                elif int(aa) >= -45 and int(aa) < 45:
                                    bb = ((aa * aa) / 50)
                                elif aa >= 45 and aa < 90: 
                                    bb = (((aa-90) * (aa-90)) / 50)
                                else:
                                    bb = (72) 

                                self.max_speed.set(min(bb + 72, 100))

                            if hud_angles:
                                self.anglevar.set(str(int(angle_between_res1)) + "º/ " + str(int(angle_between_res2)) + "º")
                            
                            if hud_angles_airboost:
                                global magic_angle

                                i = self.canvas.find_withtag("airdrift_meter")
                                b = self.canvas.find_withtag("airdrift_meter_border")
                                beetleangle = abs(int(angle_between_res2))
                                self.airdrift_angle_tk.set(beetleangle)
                                pixels = min(64,round(beetleangle * 64 / magic_angle))
                                self.canvas.coords(i, 23 + 356, 97-pixels , 27 + 356, 97)
                                self.canvas.itemconfig(i, outline="#7897ff")
                                self.canvas.itemconfig(i, fill="#7897ff")
                                self.canvas.itemconfig(b, outline="#666666")
                                
                                if (beetleangle > 5):
                                    self.canvas.itemconfig(i, outline="#7897ff")
                                    self.canvas.itemconfig(i, fill="#7897ff")
                                    self.canvas.itemconfig(b, outline="white")
                                if (beetleangle > magic_angle):
                                    self.canvas.itemconfig(i, outline="#ff8a36")
                                    self.canvas.itemconfig(i, fill="#ff8a36")
                                    self.canvas.itemconfig(b, outline="#ff8a36")
                                if (beetleangle > magic_angle + 10):
                                    self.canvas.itemconfig(i, outline="#de1f18")
                                    self.canvas.itemconfig(i, fill="#de1f18")
                                    self.canvas.itemconfig(b, outline="#de1f18")
                            

                            if hud_angles_bubbles:
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

                                theta = np.radians(magic_angle/2)
                                c, s = np.cos(theta), np.sin(theta)
                                R = np.array(((c,-s), (s, c)))
                                r50v = np.dot(R, uv)
                                theta = np.radians(-magic_angle/2)
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
                acceleration = 0
                if hud_acceleration:
                    acceleration = round(((velocity - _lastVel) / (_time - _lastTime)))*100/1000 

                    if acceleration > 900:
                        acceleration = 900
                    
                    if acceleration < -900:
                        acceleration = -900

                    if acceleration < 900 and acceleration > -900:
                            self.accelvar.set(acceleration);
                    
                #escribir velocidad,tiempo,x,y,z en fichero, solo si está abierto el fichero y si está habilitado el log
                if filename != "" and round((velocity*100/10000)*99/72) < 150:
                    #print([filename,str(_pos[0]),str(_pos[1]),str(_pos[2]),str(velocity), str(_time - total_timer)])
                    if hud_timer:
                        self.vartime.set(datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - total_timer), "%M:%S:%f")[:-3])
                    if hud_distance:
                        self.distance.set(str(round(total_distance)) + "m.")
                    if log:
                        writer = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + filename,'a',newline='', encoding='utf-8')
                        writer.seek(0,2)
                        writer.writelines("\r")
                        writer.writelines( (',').join([str(_3Dpos[0]),str(_3Dpos[1]),str(_3Dpos[2]),str(round((velocity*100/10000)*99/72)),str(angle_between_res1),str(angle_between_res2), str(_time - lap_timer), str(acceleration)]))

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
                    #self.max_speed.set(72)
                    self.var100.set(round((velocity*100/10000)*99/72))
                    i = self.canvas.find_withtag("arc")
                    self.canvas.itemconfig(i, outline=color)
                    #i = self.canvas.find_withtag("numero")
                    #self.canvas.itemconfig(i, fg=color)

                                    
            _lastTime = _time
            _lastPos = _pos
            _lastVel = velocity
            _lastTick = _tick

        self.root.after(10, self.updateMeterTimer)

class Racer():

    def setOnTopfullscreen(self):
        self.root.attributes('-topmost', 1)
        self.root.after(5000, self.setOnTopfullscreen)

    def on_message(self, client, userdata, message):

        global countdowntxt

        #print("message received " ,json.loads(str(message.payload.decode("utf-8"))))
        received = json.loads(str(message.payload.decode("utf-8")))
    
        if received.get('option') == "s":
            #print("first checkpoint for!!", received.get('user'))
            user = received.get('user')
            time = received.get('time')
            lap = received.get('lap')

            countdowntxt = ""

            self.timestamps.append({"user": user, "time": time, "step": 0, "lap": lap})
            self.thread_queue.put("Race positions")
            # guardar tiempo de user para inicio
            # falta mostrar por pantalla el ranking de partida
        if received.get('option') == "f":
            #print("finish!!", received.get('user'))

            user = received.get('user')
            time = received.get('time')
            step = received.get('step')
            lap = received.get('lap')

            self.timestamps.append({"user": user, "time": time, "step": step, "lap": lap})
            if str(step) == '999':
                self.thread_queue.put("Race finished\nPositions:")

            # guardar tiempo de user de fin de carrera
            # falta mostrar por pantalla el ranking de partida
        if received.get('option') == "c":
            #print("checkpoint ", received.get('step') ," for!!", received.get('user'))

            user = received.get('user')
            time = received.get('time')
            step = received.get('step')
            lap = received.get('lap')

            #self.thread_queue.put("checkpoint " + str(step))
            if step >= 1000:
                self.timestamps = list(filter(lambda x: x['user'] not in [str(user)], self.timestamps))

            self.timestamps.append({"user": user, "time": time, "step": step, "lap": lap})

            # guardar tiempo de checkpoint
            # falta mostrar por pantalla el ranking de partida
        if received.get('option') == "321GO-custom":
            #print("3!!")
            self.thread_queue.put(received.get('message'))
            countdowntxt = received.get('message')
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "ding.wav", block=False)
            self.timestamps = []

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-3":
            #print("3!!")
            self.thread_queue.put("3...")
            countdowntxt = "3"
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "ding.wav", block=False)
            self.timestamps = []

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-2":
            #print("2!!")
            self.thread_queue.put("2...")
            countdowntxt = "2!"
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "ding.wav", block=False)

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-1":
            #print("1!!")
            self.thread_queue.put("1...")
            countdowntxt = "1!!"
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "ding.wav", block=False)

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-GO":
            #print("GO GO GO!!")
            self.thread_queue.put("GOGOGOGO")
            countdowntxt = "Brr!"
            playsound(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "dong.wav", block=False)
            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1

    def sendMQTT(self, data):
        global client
        if client != "":
            client.publish(self.prefix_topic + self.session_id.get(), json.dumps(data))

    def newRaceThread(self):
        self.root.focus_set()
        self.countdown = 4
        self.newRace()
        #t = threading.Thread(target=self.newRace())
        #t.start()

    def surrender(self):
        self.root.focus_set()
        global countdowntxt
        global lap
        self.sendMQTT({"option": "c", "step": 1000, "time": 0 ,"lap": 1, "user": self.username.get()})
        lap = 1
        countdowntxt = ""

    def ready(self):
        self.root.focus_set()
        global lap
        global countdowntxt
        self.sendMQTT({"option": "c", "step": 1001, "time": 0 ,"lap": 1, "user": self.username.get()})
        lap = 1
        countdowntxt = ""

    def newRace(self):
        self.countdown = self.countdown - 1
        if self.countdown == 0:
            self.sendMQTT({"option": "321GO-GO"})
        
        if self.countdown > 0:
            self.sendMQTT({"option": "321GO-"+str(self.countdown)})
            self.root.after(1000, self.newRace)
        
    def ignore_message(self, client, userdata, message):
        pass

    def open_multiplayer_map(self):
        if not self.mapOpen:
            self.session_id.get()
            subprocess.Popen(["python", os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "map_realtime_multiplayer.py", self.session_id.get()])
            self.mapOpen = True

    def joinRace(self):
        global client
        self.root.focus_set()
        #ignore old channel
        if client != "":
            client.on_message=self.ignore_message 

        self.status.set("JOINED!")
        self.race_status.set("Waiting to start...")
        #print(self.username.get() + " JOINED RACE: " + self.session_id.get())
        #subscribición al topico
        broker_address="beetlerank.bounceme.net"
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

    def reset(self):

        self.root.focus_set()
        self.saveCheckpoint(0)

        global _3Dpos
        global _time

        global keyboard_
        global filename
        global total_timer
        global lap_timer
        global total_distance

        global lap
        global meter

        if enable_livesplit_hotkey == 1:
            keyboard_.press(live_reset)
            keyboard_.release(live_reset)
        if enable_ghost_keys:
            keyboard_.press(recalculate_ghost)
            keyboard_.release(recalculate_ghost)
        #cerrar fichero si hubiera una sesión anterior
        filename = ""
        total_timer = _time
        lap_timer = _time
        #print("----------------------------------")
        #print("GOING TO MAP TP = RESET RUN ")
        #print("----------------------------------")
        meter.steps_txt.set("")
        meter.step1_txt.set("")
        meter.vartime.set("")
        meter.distance.set("")

        lap = 1
        total_distance = 0

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
            self.map_ranking.configure(fg=self.color_trans_fg); self.map_ranking.configure(bg=self.color_trans_bg)
            self.t_1.configure(fg=self.color_trans_fg); self.t_1.configure(bg=self.color_trans_bg)
            self.t_2.configure(fg=self.color_trans_fg); self.t_2.configure(bg=self.color_trans_bg)
            self.t_3.configure(fg=self.color_trans_fg); self.t_3.configure(bg="#222222")
            self.t_4.configure(fg=self.color_trans_fg); self.t_4.configure(bg=self.color_trans_bg)
            self.t_4_4.configure(fg=self.color_trans_fg); self.t_4_4.configure(bg=self.color_trans_bg)
            self.t_4_5.configure(fg="black"); self.t_4_5.configure(bg=self.color_trans_bg)
            self.t_4_6.configure(fg="black"); self.t_4_6.configure(bg=self.color_trans_bg)
            self.t_5.configure(fg=self.color_trans_fg); self.t_5.configure(bg="#222222")
            self.t_6.configure(fg=self.color_trans_fg); self.t_6.configure(bg="#222222")
            #self.t_6_1.configure(fg=self.color_trans_fg); self.t_6_1.configure(bg="#222222")
            self.t_7.configure(fg=self.color_trans_fg); self.t_7.configure(bg="#222222")
            self.t_7_1.configure(fg=self.color_trans_fg); self.t_7_1.configure(bg="#222222")
            self.t_7_2.configure(fg=self.color_trans_fg); self.t_7_2.configure(bg="#222222")
            self.t_3_5.configure(fg=self.color_trans_fg); self.t_3_5.configure(bg="#222222")
            self.t_3_6.configure(fg=self.color_trans_fg); self.t_3_6.configure(bg="#222222")
            self.t_8.configure(fg=self.color_trans_fg); self.t_8.configure(bg=self.color_trans_bg)
            self.t_9.configure(fg=self.color_trans_fg); self.t_9.configure(bg=self.color_trans_bg)
            self.t_10.configure(fg=self.color_trans_fg); self.t_10.configure(bg=self.color_trans_bg)
            self.conf_move.configure(fg=self.color_trans_fg); self.conf_move.configure(bg="#222222")
            self.conf_1_1.configure(fg=self.color_trans_fg); self.conf_1_1.configure(bg=self.color_trans_bg)
            self.conf_1_2.configure(fg="black"); self.conf_1_2.configure(bg=self.color_trans_bg)
            self.conf_2_1.configure(fg=self.color_trans_fg); self.conf_2_1.configure(bg=self.color_trans_bg)
            self.conf_2_2.configure(fg="black"); self.conf_2_2.configure(bg=self.color_trans_bg)
            self.conf_3_1.configure(fg=self.color_trans_fg); self.conf_3_1.configure(bg=self.color_trans_bg)
            self.conf_3_2.configure(fg="black"); self.conf_3_2.configure(bg=self.color_trans_bg)
            self.conf_4_1.configure(fg=self.color_trans_fg); self.conf_4_1.configure(bg=self.color_trans_bg)
            self.conf_4_2.configure(fg="black"); self.conf_4_2.configure(bg=self.color_trans_bg)
            self.conf_5_1.configure(fg=self.color_trans_fg); self.conf_5_1.configure(bg=self.color_trans_bg)
            self.conf_5_2.configure(fg="black"); self.conf_5_2.configure(bg=self.color_trans_bg)
            self.conf_6_1.configure(fg=self.color_trans_fg); self.conf_6_1.configure(bg=self.color_trans_bg)
            self.conf_6_2.configure(fg="black"); self.conf_6_2.configure(bg=self.color_trans_bg)
            self.conf_7_1.configure(fg=self.color_trans_fg); self.conf_7_1.configure(bg=self.color_trans_bg)
            self.conf_7_2.configure(fg="black"); self.conf_7_2.configure(bg=self.color_trans_bg)
            self.conf_8_1.configure(fg=self.color_trans_fg); self.conf_8_1.configure(bg=self.color_trans_bg)
            self.conf_8_2.configure(fg="black"); self.conf_8_2.configure(bg=self.color_trans_bg)
            self.conf_9_1.configure(fg=self.color_trans_fg); self.conf_9_1.configure(bg=self.color_trans_bg)
            self.conf_9_2.configure(fg="black"); self.conf_9_2.configure(bg=self.color_trans_bg)
            self.conf_10_1.configure(fg=self.color_trans_fg); self.conf_10_1.configure(bg=self.color_trans_bg)
            self.conf_10_2.configure(fg="black"); self.conf_10_2.configure(bg=self.color_trans_bg)
            self.conf_11_1.configure(fg=self.color_trans_fg); self.conf_11_1.configure(bg=self.color_trans_bg)
            self.conf_11_2.configure(fg="black"); self.conf_11_2.configure(bg=self.color_trans_bg)
            self.conf_12_1.configure(fg=self.color_trans_fg); self.conf_12_1.configure(bg=self.color_trans_bg)
            self.conf_12_2.configure(fg="black"); self.conf_12_2.configure(bg=self.color_trans_bg)
            self.conf_13_1.configure(fg=self.color_trans_fg); self.conf_13_1.configure(bg=self.color_trans_bg)
            self.conf_13_2.configure(fg="black"); self.conf_13_2.configure(bg=self.color_trans_bg)
            self.conf_14_1.configure(fg=self.color_trans_fg); self.conf_14_1.configure(bg=self.color_trans_bg)
            self.conf_14_2.configure(fg="black"); self.conf_14_2.configure(bg=self.color_trans_bg)
            self.conf_15_1.configure(bg=self.color_trans_bg)
            self.conf_15_2.configure(fg=self.color_trans_fg); self.conf_15_2.configure(bg="#222222")
            self.conf_save.configure(fg=self.color_trans_fg); self.conf_save.configure(bg="#222222")
            self.conf.configure(fg=self.color_trans_fg); self.conf.configure(bg="#222222")

            self.root.configure(bg=self.color_trans_bg)
            
        else:
            self.root.overrideredirect(0)
            self.map_ranking.configure(fg=self.color_normal_fg); self.map_ranking.configure(bg=self.color_normal_bg)
            self.t_1.configure(fg=self.color_normal_fg); self.t_1.configure(bg=self.color_normal_bg)
            self.t_2.configure(fg=self.color_normal_fg); self.t_2.configure(bg=self.color_normal_bg)
            self.t_3.configure(fg=self.color_normal_fg); self.t_3.configure(bg=self.color_normal_bg)
            self.t_4.configure(fg=self.color_normal_fg); self.t_4.configure(bg=self.color_normal_bg)
            self.t_4_4.configure(fg=self.color_normal_fg); self.t_4_4.configure(bg=self.color_normal_bg)
            self.t_4_5.configure(fg=self.color_normal_fg); self.t_4_5.configure(bg=self.color_normal_bg)
            self.t_4_6.configure(fg=self.color_normal_fg); self.t_4_6.configure(bg=self.color_normal_bg)
            self.t_5.configure(fg=self.color_normal_fg); self.t_5.configure(bg=self.color_normal_bg)
            self.t_6.configure(fg=self.color_normal_fg); self.t_6.configure(bg=self.color_normal_bg)
            #self.t_6_1.configure(fg=self.color_normal_fg); self.t_6_1.configure(bg=self.color_normal_bg)
            self.t_7.configure(fg=self.color_normal_fg); self.t_7.configure(bg=self.color_normal_bg)
            self.t_7_1.configure(fg=self.color_normal_fg); self.t_7_1.configure(bg=self.color_normal_bg)
            self.t_7_2.configure(fg=self.color_normal_fg); self.t_7_2.configure(bg=self.color_normal_bg)
            self.t_3_5.configure(fg=self.color_normal_fg); self.t_3_5.configure(bg=self.color_normal_bg)
            self.t_3_6.configure(fg=self.color_normal_fg); self.t_3_6.configure(bg=self.color_normal_bg)
            self.t_8.configure(fg=self.color_normal_fg); self.t_8.configure(bg=self.color_normal_bg)
            self.t_9.configure(fg=self.color_normal_fg); self.t_9.configure(bg=self.color_normal_bg)
            self.t_10.configure(fg=self.color_normal_fg); self.t_10.configure(bg=self.color_normal_bg)
            self.conf_move.configure(fg=self.color_normal_fg); self.conf_move.configure(bg=self.color_normal_bg)
            self.conf_1_1.configure(fg=self.color_normal_fg); self.conf_1_1.configure(bg=self.color_normal_bg)
            self.conf_1_2.configure(fg=self.color_normal_fg); self.conf_1_2.configure(bg=self.color_normal_bg)
            self.conf_2_1.configure(fg=self.color_normal_fg); self.conf_2_1.configure(bg=self.color_normal_bg)
            self.conf_2_2.configure(fg=self.color_normal_fg); self.conf_2_2.configure(bg=self.color_normal_bg)
            self.conf_3_1.configure(fg=self.color_normal_fg); self.conf_3_1.configure(bg=self.color_normal_bg)
            self.conf_3_2.configure(fg=self.color_normal_fg); self.conf_3_2.configure(bg=self.color_normal_bg)
            self.conf_4_1.configure(fg=self.color_normal_fg); self.conf_4_1.configure(bg=self.color_normal_bg)
            self.conf_4_2.configure(fg=self.color_normal_fg); self.conf_4_2.configure(bg=self.color_normal_bg)
            self.conf_5_1.configure(fg=self.color_normal_fg); self.conf_5_1.configure(bg=self.color_normal_bg)
            self.conf_5_2.configure(fg=self.color_normal_fg); self.conf_5_2.configure(bg=self.color_normal_bg)
            self.conf_6_1.configure(fg=self.color_normal_fg); self.conf_6_1.configure(bg=self.color_normal_bg)
            self.conf_6_2.configure(fg=self.color_normal_fg); self.conf_6_2.configure(bg=self.color_normal_bg)
            self.conf_7_1.configure(fg=self.color_normal_fg); self.conf_7_1.configure(bg=self.color_normal_bg)
            self.conf_7_2.configure(fg=self.color_normal_fg); self.conf_7_2.configure(bg=self.color_normal_bg)
            self.conf_8_1.configure(fg=self.color_normal_fg); self.conf_8_1.configure(bg=self.color_normal_bg)
            self.conf_8_2.configure(fg=self.color_normal_fg); self.conf_8_2.configure(bg=self.color_normal_bg)
            self.conf_9_1.configure(fg=self.color_normal_fg); self.conf_9_1.configure(bg=self.color_normal_bg)
            self.conf_9_2.configure(fg=self.color_normal_fg); self.conf_9_2.configure(bg=self.color_normal_bg)
            self.conf_10_1.configure(fg=self.color_normal_fg); self.conf_10_1.configure(bg=self.color_normal_bg)
            self.conf_10_2.configure(fg=self.color_normal_fg); self.conf_10_2.configure(bg=self.color_normal_bg)
            self.conf_11_1.configure(fg=self.color_normal_fg); self.conf_11_1.configure(bg=self.color_normal_bg)
            self.conf_11_2.configure(fg=self.color_normal_fg); self.conf_11_2.configure(bg=self.color_normal_bg)
            self.conf_12_1.configure(fg=self.color_normal_fg); self.conf_12_1.configure(bg=self.color_normal_bg)
            self.conf_12_2.configure(fg=self.color_normal_fg); self.conf_12_2.configure(bg=self.color_normal_bg)
            self.conf_13_1.configure(fg=self.color_normal_fg); self.conf_13_1.configure(bg=self.color_normal_bg)
            self.conf_13_2.configure(fg=self.color_normal_fg); self.conf_13_2.configure(bg=self.color_normal_bg)
            self.conf_14_1.configure(fg=self.color_normal_fg); self.conf_14_1.configure(bg=self.color_normal_bg)
            self.conf_14_2.configure(fg=self.color_normal_fg); self.conf_14_2.configure(bg=self.color_normal_bg)
            self.conf_15_1.configure(bg=self.color_normal_bg)
            self.conf_15_2.configure(fg=self.color_normal_fg); self.conf_15_2.configure(bg=self.color_normal_bg)
            self.conf_save.configure(fg=self.color_normal_fg); self.conf_save.configure(bg=self.color_normal_bg)
            self.conf.configure(fg=self.color_normal_fg); self.conf.configure(bg=self.color_normal_bg)

            self.root.configure(bg=self.color_normal_bg)
            
        self.move = not self.move

    def saveCheckpoint(self,value):
        #stores in counterDone.txt number of total laps done
        file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "checkpoint.txt", "w")
        file.write(str(value))
        file.close()

    def saveGuildhall(self,value):
        #stores in counterDone.txt number of total laps done
        global guildhall_name

        self.root.focus_set()
    
        file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "guildhall.txt", "w")
        file.write(str(guildhall_name.get()))
        file.close()
        if enable_ghost_keys:
            keyboard_.press(recalculate_ghost)
            keyboard_.release(recalculate_ghost)

        #get ranking from web
        #pepe
        if (guildhall_name.get() == "None, im free!"):
            self.map_ranking_var.set("")
        else:
            try:
                headers = {
                    'Origin': 'null',
                    'Referer': 'null'
                }
                response = requests.get('http://beetlerank.bounceme.net/rank/api/' + str(guildhall_name.get()), headers)
            
                self.map_ranking_var.set(response.text)

            except:
                self.map_ranking_var.set("")
    
    def __init__(self):
        
        global guildhall_name
        global guildhall_laps
        global upload
        global geometry_racer
        global player_color


        self.mapOpen = False
        self.move = True

        self.color_trans_fg= "white"
        self.color_trans_bg= "#666666"
        self.color_normal_fg= "black"
        self.color_normal_bg= "#f0f0f0"

        self.root = Tk()
        self.root.call('wm', 'attributes', '.', '-topmost', '1')
        self.root.title("Guildhall logs & challenger")
        self.root.geometry(geometry_racer)
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

        guildhall_name = StringVar(self.root)
        guildhall_name.set('SELECT MAP')
        guildhall_laps = StringVar(self.root)
        guildhall_laps.set("1 lap")


        self.t_1 = tk.Label(self.root, text="""Race Assistant v1.6.22""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 15))
        self.t_1.place(x=0, y=10)
        self.t_2 = tk.Label(self.root, text="""Choose map to race""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_2.place(x=0, y=40)
        
        self.choices = ['None, im free!', "OLLO Akina", "OLLO Shortcut", 'RACE Downhill', 'RACE Hillclimb', 'RACE Full Mountain Run', 
            'GeeK','INDI', 'UAoT', 'VAW Left path', 'VAW Right path', 'GWTC', 'EQE', 'SoTD', 'LRS', 'HUR', 
            "TYRIA INF.LEAP", "TYRIA DIESSA PLATEAU", "TYRIA SNOWDEN DRIFTS", "TYRIA GENDARRAN", "TYRIA BRISBAN WILD.", "TYRIA GROTHMAR VALLEY",
            "DRFT-1 Fractal Actual Speedway", "DRFT-2 Wayfar Out", "DRFT-3 Summers Sunset", "DRFT-4 Mossheart Memory", "DRFT-5 Roller Coaster Canyon", 
            "DRFT-6 Centurion Circuit", "DRFT-7 Dredgehaunt Cliffs", "DRFT-8 Icy Rising Ramparts", "DRFT-9 Soulthirst Savannah of Svanier", "DRFT-10 Toxic Turnpike", 
            "DRFT-11 Estuary of Twilight", "DRFT-12 Celedon Circle", "DRFT-13 Thermo Reactor Escape", "DRFT-14 Jormags Jumpscare", 
            "DRFT-GP-1 Lions Summer Sights","DRFT-GP-2 Sandswept Shore Sprint","DRFT-GP-3 Inquest Isle Invasion","DRFT-GP-4 Triple Trek Periphery","DRFT-GP-5 Beachin Crabwalk",
            "FLY-1 Verdant Brink Hunt"]
        self.t_3 = tk.OptionMenu(self.root, guildhall_name, *self.choices, command = self.saveGuildhall)
        self.t_3.config(font=("Lucida Console", 10))
        self.t_3["highlightthickness"] = 0
        self.t_3["activebackground"] = "#222222"
        self.t_3["activeforeground"] = "white" 
        self.t_3.place(x=19, y=60, width=150, height=27)
        

        self.laps = ['1 lap', '2 laps', '3 laps', '4 laps', '5 laps', '6 laps', '7 laps']
        self.t_3_5 = OptionMenu(self.root, guildhall_laps, *self.laps)
        self.t_3_5["highlightthickness"] = 0
        self.t_3_5["activebackground"] = "#222222"
        self.t_3_5["activeforeground"] = "white"
        self.t_3_5.place(x=169, y=60, width=70)

        global audio
        global hud_gauge
        global hud_timer
        global hud_distance
        global hud_acceleration
        global hud_angles
        global hud_angles_bubbles
        global hud_angles_airboost
        global hud_max_speed
        global hud_drift_hold
        global enable_livesplit_hotkey
        global enable_ghost_keys
        global speed_in_3D
        global log
        global player_color


        def conf_toggle(field):
            if globals()[field] == 1:
                globals()[field] = 0
            else:
                globals()[field] = 1

        def choose_color():
 
            global player_color 
            # variable to store hexadecimal code of color
            player_color = colorchooser.askcolor(title ="Choose color")[1]
            if (player_color):
                self.conf_15_1.configure(fg=player_color)
                conf_save()

        def conf_save():
            print("saved and restart")
            global conf

            conf.saveConf()

            subprocess.Popen(["python", sys.argv[0]])
            sys.exit()

        def toggleAll():
            global meter
            global racer
            global countdownWidget
            global show_checkpoints_window

            if not show_checkpoints_window:
                    meter.toggleTrans()
            else:
                if meter.move == racer.move:
                    meter.toggleTrans()
                    racer.toggleTrans()
                    countdownWidget.toggleTrans()
                else:
                    if meter.move:
                        racer.toggleTrans()
                    else:
                        meter.toggleTrans()


        self.conf_move = tk.Button(self.root, text='MOVE SPEEDOMETER', command=lambda:toggleAll(),font=("Lucida Console", 10))
        self.conf_move.place(x=310, y=23, width=160, height=20)
        
        #OPTION 1 
        self.conf_1_0 = IntVar(self.root, audio)

        self.conf_1_1 = tk.Label(self.root, text="""Audio on checkpoints""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_1_1.place(x=314, y=44)

        self.conf_1_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_1_0,
            borderwidth=0, command=lambda:conf_toggle("audio"))
        self.conf_1_2.place(x=310, y=44)
        
        
        #OPTION 1 
        self.conf_2_0 = IntVar(self.root, hud_gauge)

        self.conf_2_1 = tk.Label(self.root, text="""Show speed""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_2_1.place(x=314, y=44 + 1 * 20)

        self.conf_2_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_2_0,
            borderwidth=0, command=lambda:conf_toggle("hud_gauge"))
        self.conf_2_2.place(x=310, y=44 + 1 * 20 )
        
        
        #OPTION 1 
        self.conf_3_0 = IntVar(self.root, hud_timer)

        self.conf_3_1 = tk.Label(self.root, text="""Show timer""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_3_1.place(x=314, y=44 + 2 * 20)

        self.conf_3_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_3_0,
            borderwidth=0, command=lambda:conf_toggle("hud_timer"))
        self.conf_3_2.place(x=310, y=44 + 2 * 20)
        
        
        #OPTION 1 
        self.conf_4_0 = IntVar(self.root, hud_distance)

        self.conf_4_1 = tk.Label(self.root, text="""Show distance""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_4_1.place(x=314, y=44 + 3 * 20)

        self.conf_4_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_4_0,
            borderwidth=0, command=lambda:conf_toggle("hud_distance"))
        self.conf_4_2.place(x=310, y=44 + 3 * 20)
        
        
        #OPTION 1 
        self.conf_5_0 = IntVar(self.root, hud_acceleration)

        self.conf_5_1 = tk.Label(self.root, text="""Show acceleration""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_5_1.place(x=314, y=44 + 4 * 20)

        self.conf_5_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_5_0,
            borderwidth=0, command=lambda:conf_toggle("hud_acceleration"))
        self.conf_5_2.place(x=310, y=44 + 4 * 20)
        
        
        #OPTION 1 
        self.conf_6_0 = IntVar(self.root, hud_angles)

        self.conf_6_1 = tk.Label(self.root, text="""Show angles""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_6_1.place(x=314, y=44 + 5 * 20)

        self.conf_6_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_6_0,
            borderwidth=0, command=lambda:conf_toggle("hud_angles"))
        self.conf_6_2.place(x=310, y=44 + 5 * 20)
        
        
        #OPTION 1 
        self.conf_7_0 = IntVar(self.root, hud_angles_bubbles)

        self.conf_7_1 = tk.Label(self.root, text="""Show angle orbs""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_7_1.place(x=314, y=44 + 6 * 20)

        self.conf_7_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_7_0,
            borderwidth=0, command=lambda:conf_toggle("hud_angles_bubbles"))
        self.conf_7_2.place(x=310, y=44 + 6 * 20)
        
        #OPTION 1 
        self.conf_8_0 = IntVar(self.root, hud_drift_hold)

        self.conf_8_1 = tk.Label(self.root, text="""Show drift hold""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_8_1.place(x=314, y=44 + 7 * 20)

        self.conf_8_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_8_0,
            borderwidth=0, command=lambda:conf_toggle("hud_drift_hold"))
        self.conf_8_2.place(x=310, y=44 + 7 * 20)
        
        
        #OPTION 1 
        self.conf_9_0 = IntVar(self.root, enable_livesplit_hotkey)

        self.conf_9_1 = tk.Label(self.root, text="""Enable livesplit hotkeys""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_9_1.place(x=314, y=44 + 8 * 20)

        self.conf_9_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_9_0,
            borderwidth=0, command=lambda:conf_toggle("enable_livesplit_hotkey"))
        self.conf_9_2.place(x=310, y=44 + 8 * 20)
        
        
        #OPTION 1 
        self.conf_10_0 = IntVar(self.root, enable_ghost_keys)

        self.conf_10_1 = tk.Label(self.root, text="""Enable ghost hotkeys""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_10_1.place(x=314, y=44 + 9 * 20)

        self.conf_10_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_10_0,
            borderwidth=0, command=lambda:conf_toggle("enable_ghost_keys"))
        self.conf_10_2.place(x=310, y=44 + 9 * 20)
        
        
        #OPTION 1 
        self.conf_11_0 = IntVar(self.root, speed_in_3D)

        self.conf_11_1 = tk.Label(self.root, text="""Measure speed in 3D""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_11_1.place(x=314, y=44 + 10 * 20)

        self.conf_11_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_11_0,
            borderwidth=0, command=lambda:conf_toggle("speed_in_3D"))
        self.conf_11_2.place(x=310, y=44 + 10 * 20)
        
        
        #OPTION 1 
        self.conf_12_0 = IntVar(self.root, log)

        self.conf_12_1 = tk.Label(self.root, text="""Log to file (need if want to upload)""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_12_1.place(x=314, y=44 + 11 * 20)

        self.conf_12_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_12_0,
            borderwidth=0, command=lambda:conf_toggle("log"))
        self.conf_12_2.place(x=310, y=44 + 11 * 20)

        #OPTION 1 
        self.conf_13_0 = IntVar(self.root, hud_angles_airboost)

        self.conf_13_1 = tk.Label(self.root, text="""Show airboost helper""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_13_1.place(x=314, y=44 + 12 * 20)

        self.conf_13_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_13_0,
            borderwidth=0, command=lambda:conf_toggle("hud_angles_airboost"))
        self.conf_13_2.place(x=310, y=44 + 12 * 20)

        #OPTION 1 
        self.conf_14_0 = IntVar(self.root, hud_max_speed)

        self.conf_14_1 = tk.Label(self.root, text="""Show max speed on gauge""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.conf_14_1.place(x=314, y=44 + 13 * 20)

        self.conf_14_2 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.conf_14_0,
            borderwidth=0, command=lambda:conf_toggle("hud_max_speed"))
        self.conf_14_2.place(x=310, y=44 + 13 * 20)

 


        self.conf_15_1 = tk.Label(self.root, text="■", justify = tk.LEFT, padx = 0, fg = player_color, bg=self.bg.get(), font=("Lucida Console", 15))
        self.conf_15_1.place(x=311, y=42 + 14 * 20)

        #SAVE OPTIONS
        self.conf_15_2 = tk.Button(self.root, text='Change color', command=lambda:choose_color() ,font=("Lucida Console", 10))
        self.conf_15_2.place(x=336, y=44 + 14 * 20, width=120, height=23)

        #SAVE OPTIONS
        self.conf_save = tk.Button(self.root, text='SAVE & RESTART', command=lambda:conf_save() ,font=("Lucida Console", 10))
        self.conf_save.place(x=320, y=44 + 16 * 20, width=120, height=27)


        def changeConfigVisibility():
            global show_config

            if show_config == 1:
                #mostrarlo
                self.conf_move.place(x=310, y=23, width=160, height=20)
                self.conf_1_1.place(x=314, y=44)
                self.conf_1_2.place(x=310, y=44)
                self.conf_2_1.place(x=314, y=44 + 1 * 20)
                self.conf_2_2.place(x=310, y=44 + 1 * 20 )
                self.conf_3_1.place(x=314, y=44 + 2 * 20)
                self.conf_3_2.place(x=310, y=44 + 2 * 20)
                self.conf_4_1.place(x=314, y=44 + 3 * 20)
                self.conf_4_2.place(x=310, y=44 + 3 * 20)
                self.conf_5_1.place(x=314, y=44 + 4 * 20)
                self.conf_5_2.place(x=310, y=44 + 4 * 20)
                self.conf_6_1.place(x=314, y=44 + 5 * 20)
                self.conf_6_2.place(x=310, y=44 + 5 * 20)
                self.conf_7_1.place(x=314, y=44 + 6 * 20)
                self.conf_7_2.place(x=310, y=44 + 6 * 20)
                self.conf_8_1.place(x=314, y=44 + 7 * 20)
                self.conf_8_2.place(x=310, y=44 + 7 * 20)
                self.conf_9_1.place(x=314, y=44 + 8 * 20)
                self.conf_9_2.place(x=310, y=44 + 8 * 20)
                self.conf_10_1.place(x=314, y=44 + 9 * 20)
                self.conf_10_2.place(x=310, y=44 + 9 * 20)
                self.conf_11_1.place(x=314, y=44 + 10 * 20)
                self.conf_11_2.place(x=310, y=44 + 10 * 20)
                self.conf_12_1.place(x=314, y=44 + 11 * 20)
                self.conf_12_2.place(x=310, y=44 + 11 * 20)
                self.conf_13_1.place(x=314, y=44 + 12 * 20)
                self.conf_13_2.place(x=310, y=44 + 12 * 20)
                self.conf_14_1.place(x=314, y=44 + 13 * 20)
                self.conf_14_2.place(x=310, y=44 + 13 * 20)
                self.conf_15_1.place(x=311, y=42 + 14 * 20)
                self.conf_15_2.place(x=336, y=44 + 14 * 20, width=120, height=23)
                self.conf_save.place(x=320, y=48 + 15 * 20, width=120, height=27)


                show_config = 0


            else:
                #ocultarlo
                self.conf_1_1.place_forget()
                self.conf_1_2.place_forget()
                self.conf_2_1.place_forget()
                self.conf_2_2.place_forget()
                self.conf_3_1.place_forget()
                self.conf_3_2.place_forget()
                self.conf_4_1.place_forget()
                self.conf_4_2.place_forget()
                self.conf_5_1.place_forget()
                self.conf_5_2.place_forget()
                self.conf_6_1.place_forget()
                self.conf_6_2.place_forget()
                self.conf_7_1.place_forget()
                self.conf_7_2.place_forget()
                self.conf_8_1.place_forget()
                self.conf_8_2.place_forget()
                self.conf_9_1.place_forget()
                self.conf_9_2.place_forget()
                self.conf_10_1.place_forget()
                self.conf_10_2.place_forget()
                self.conf_11_1.place_forget()
                self.conf_11_2.place_forget()
                self.conf_12_1.place_forget()
                self.conf_12_2.place_forget()
                self.conf_13_1.place_forget()
                self.conf_13_2.place_forget()
                self.conf_14_1.place_forget()
                self.conf_14_2.place_forget()
                self.conf_15_1.place_forget()
                self.conf_15_2.place_forget()
                self.conf_move.place_forget()
                self.conf_save.place_forget()

                show_config = 1

        self.conf = tk.Button(self.root, text='CONFIG', command=lambda:changeConfigVisibility(), font=("Lucida Console", 7))
        self.conf.place(x=239, y=44, width=60, height=15)


        self.t_3_6 = tk.Button(self.root, text='RESET', command=lambda:self.reset(),font=("Lucida Console", 10))
        self.t_3_6.place(x=239, y=60, width=60, height=27)

        changeConfigVisibility()

        self.status = StringVar(self.root)
        self.status.set("JOIN")

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

        self.t_4 = tk.Label(self.root, text="""Upload to ranking""", justify = tk.LEFT, padx = 10, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_4.place(x=151, y=100)
        self.t_4_4 = tk.Label(self.root, text="""Multiplayer""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_4_4.place(x=20, y=100)
        

        #tk.Label(self.root, text="""Join race:""", justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10)).place(x=0, y=110)
        
        self.t_5 = tk.Entry(self.root,textvariable=self.session_id ,show="*")
        self.t_5.place(x=20, y=120, height=28)
        self.t_6 = tk.Button(self.root, textvariable=self.status, command=self.joinRace,font=("Lucida Console", 10))
        self.t_6.place(x=120, y=120, width=80)
        #self.t_6_1 = tk.Button(self.root, text="MAP", command=self.open_multiplayer_map,font=("Lucida Console", 10))
        #self.t_6_1.place(x=120, y=148, width=80)

        #tk.Label(self.root, text="""Create new race:""", justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10)).pack()
        self.t_7 = tk.Button(self.root, text='START RACE', command=lambda:self.newRaceThread(),font=("Lucida Console", 10))
        self.t_7.place(x=200, y=120, width=100)
        self.t_7_1 = tk.Button(self.root, text='SURRENDER', command=lambda:self.surrender(),font=("Lucida Console", 10))
        self.t_7_1.place(x=200, y=176, width=100)
        self.t_7_2 = tk.Button(self.root, text='READY', command=lambda:self.ready(),font=("Lucida Console", 10))
        self.t_7_2.place(x=200, y=148, width=100)
        self.t_8 = tk.Label(self.root, text="""------""", justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_8.place(x=0, y=150)
        self.t_9 = tk.Label(self.root, textvariable=self.race_status, justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_9.place(x=0, y=175)
        self.t_10 = tk.Label(self.root, textvariable=self.ranking, justify = tk.LEFT, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_10.place(x=0, y=210)

        #ranking label
        self.map_ranking_var = StringVar(self.root)
        self.map_ranking_var.set("")

        self.map_ranking = tk.Label(self.root, textvariable=self.map_ranking_var, justify = tk.LEFT, padx = 0,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.map_ranking.place(x=20, y=130)


        def changeMultiVisibility(hide):
            if hide == 0:
                #mostrarlo
                self.t_6.place(x=120, y=120, width=80, height=27)
                #self.t_6_1.place(x=120, y=148, width=80, height=27)
                self.t_5.place(x=20, y=120, height=26)
                self.t_7.place(x=200, y=120, width=100, height=27)
                self.t_7_1.place(x=200, y=176, width=100, height=27)
                self.t_7_2.place(x=200, y=148, width=100, height=27)
                self.t_8.place(x=0, y=150)
                self.t_9.place(x=0, y=175)
                self.t_10.place(x=0, y=210)

                #ranking hide
                self.map_ranking.place_forget()


            else:
                #ocultarlo
                self.t_6.place_forget()
                #self.t_6_1.place_forget()
                self.t_5.place_forget()
                self.t_7.place_forget()
                self.t_7_1.place_forget()
                self.t_7_2.place_forget()
                self.t_8.place_forget()
                self.t_9.place_forget()
                self.t_10.place_forget()

                #ranking show
                self.map_ranking.place(x=20, y=130)




        self.multiplayer = IntVar(value=0)
        upload = IntVar(value=0)
        changeMultiVisibility(1)

        def onClickUpload():
            if upload.get() == 1:
                upload.set(0)
            else:
                upload.set(1)

        def onClick():
            if self.multiplayer.get() == 1:
                changeMultiVisibility(1)
                self.multiplayer.set(0)
                
            else:
                changeMultiVisibility(0)
                self.multiplayer.set(1)

        self.t_4_5 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=self.multiplayer,
            borderwidth=0, command=onClick)
        self.t_4_5.place(x=17, y=100)

        self.t_4_6 = tk.Checkbutton(self.root, font=("Lucida Console", 10),
            text = "",
            variable=upload, command=onClickUpload,
            borderwidth=0)
        self.t_4_6.place(x=139, y=100)
        if not log:
            self.t_4_6.configure(state=DISABLED)

        self.toggleTrans()

        self.setOnTopfullscreen()

    def listen_for_result(self):
        #update the timestamp result
        
        global guildhall_laps

        #self.timestamps = [{"name": "uno", "time": "2.1", "step": "1"},{"name": "dos", "time": "2.2", "step": "1"},{"name": "uno", "time": "4", "step": "2"}]
        
        #print(self.timestamps)

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
            top_time = sorted(filtered_list, key=lambda k: (-int(k['lap']), -int(k['step']), k['time']))

            out = [x for x in top_time if int(x['step']) >= 1000]
            if len(out) > 0:
                out_times.append(top_time[0])
            else:
                top_times.append(top_time[0])
                
        top_times = sorted(top_times, key=lambda k: (-int(k['lap']), -int(k['step']), float(k['time'])))

        rankingtxt = ""
        rankingindex = 1
        for u in top_times:
            steptime = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(u['time']), "%M:%S:%f")[:-3]
            if str(u['step']) == '999':
                rankingtxt = rankingtxt + str(rankingindex) + ": " + str(steptime) + " - FINISH > " + str(u['user']) + "\n"
            else:
                if str(u['step']) == '998':
                    rankingtxt = rankingtxt + str(rankingindex) + ": " + str(steptime) + " - L" + str(u['lap']) + "/" + str(guildhall_laps.get()[:1]) + " TF > " + str(u['user']) + "\n"
                else:
                    if str(u['step']) == '0':
                        rankingtxt = rankingtxt + str(rankingindex) + ": " + str(steptime) + " - L" + str(u['lap']) + "/" + str(guildhall_laps.get()[:1]) + " TS > " + str(u['user']) + "\n"
                    else:
                        rankingtxt = rankingtxt + str(rankingindex) + ": " + str(steptime) + " - L" + str(u['lap']) + "/" + str(guildhall_laps.get()[:1]) + " T" + str(u['step']) + " > " + str(u['user']) + "\n"

            rankingindex = rankingindex + 1
        
        out_rankingtxt = ""
        out_rankingindex = 1
        for u in out_times:
            steptime = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(u['time']), "%M:%S:%f")[:-3]
            if str(u['step']) == '1000':
                out_rankingtxt = out_rankingtxt + " OUT > " + str(u['user']) + "\n"
            if str(u['step']) == '1001':
                out_rankingtxt = out_rankingtxt + " RDY > " + str(u['user']) + "\n"
                
            out_rankingindex = out_rankingindex + 1
        
        self.ranking.set(rankingtxt + "---------\n" + out_rankingtxt )

        try:
            self.res = self.thread_queue.get(0)
            #self._print(self.res)
            self.race_status.set(self.res)
            self.root.after(100, self.listen_for_result)

        except queue.Empty:
            self.root.after(100, self.listen_for_result)

class Countdown():

    def setOnTopfullscreen(self):
        self.root.attributes('-topmost', 1)
        self.root.after(500, self.setOnTopfullscreen)

    def __init__(self):
        
        global countdowntxt

        self.move = True

        self.root = Tk()
        self.root.call('wm', 'attributes', '.', '-topmost', '1')

        self.color_trans_fg= "white"
        self.color_trans_bg= "#666666"
        self.color_normal_fg= "black"
        self.color_normal_bg= "#666666"

        self.fg = StringVar(self.root)
        self.bg = StringVar(self.root)
        self.fg.set(self.color_normal_fg)
        self.bg.set(self.color_normal_bg)

        windowWidth = 700
        windowHeight = 100
        positionRight = int(root.winfo_screenwidth()/2 - windowWidth/2)
        positionDown = int(root.winfo_screenheight()/2 - windowHeight/2)
        self.root.title("Countdown")
        self.root.geometry("{}x{}+{}+{}".format(windowWidth, windowHeight, positionRight, positionDown)) #Whatever size

        self.root.wm_attributes("-transparentcolor", "#666666")
        self.root.configure(bg='#666666')
        
        self.localcountdown = tk.StringVar(self.root,"")

        self.time = tk.Label(self.root, textvariable=self.localcountdown, justify = tk.CENTER, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 60, "bold"))
        self.time.place(x=0, y=0)

        self.toggleTrans()
        self.checkCountdowntxt()
        self.setOnTopfullscreen()

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
            self.time.configure(fg=self.color_trans_fg); self.time.configure(bg=self.color_trans_bg)
            self.root.configure(bg=self.color_trans_bg)
        else:
            self.root.overrideredirect(0)
            self.time.configure(fg=self.color_trans_fg); self.time.configure(bg=self.color_trans_bg)
            self.root.configure(bg=self.color_normal_bg)
            
        self.move = not self.move

    def checkCountdowntxt(self):
        global countdowntxt
        self.localcountdown.set(countdowntxt)
        countdowntxt = ""

        if countdowntxt == "Brr!":
            self.root.after(2500, self.checkCountdowntxt)
        else:
            self.root.after(500, self.checkCountdowntxt)

class Message():

    def setOnTopfullscreen(self):
        self.root.attributes('-topmost', 1)
        self.root.after(500, self.setOnTopfullscreen)

    def __init__(self):
        
        global countdowntxt

        self.move = True

        self.root = Tk()
        self.root.call('wm', 'attributes', '.', '-topmost', '1')

        self.color_trans_fg= "white"
        self.color_trans_bg= "#666666"
        self.color_normal_fg= "black"
        self.color_normal_bg= "#666666"

        self.fg = StringVar(self.root)
        self.bg = StringVar(self.root)
        self.fg.set(self.color_normal_fg)
        self.bg.set(self.color_normal_bg)

        windowWidth = 500
        windowHeight = 220
        positionRight = int(root.winfo_screenwidth()/2 - windowWidth/2)
        positionDown = int(root.winfo_screenheight()/2 - windowHeight/2)
        self.root.title("Message")
        self.root.geometry("{}x{}+{}+{}".format(windowWidth, windowHeight, positionRight, positionDown)) #Whatever size

        self.root.wm_attributes("-transparentcolor", "#666666")
        self.root.configure(bg='#666666')
        
        self.localcountdown = tk.StringVar(self.root,"")

        self.canvas = tk.Canvas(self.root, width=500, height=220,
                                borderwidth=0, highlightthickness=0,
                                bg='#222')
        self.outer_drifting_box = self.canvas.create_rectangle(1,1,499,219, outline="white", width="1")

        self.time = tk.Label(self.root, textvariable=self.localcountdown, justify = tk.CENTER, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console",20))
        #self.time.place(x=0, y=0)
        self.btn = tk.Button(self.root, text="Ok", padx= 20,font=("Lucida Console", 10),command=lambda:self.hide())
        self.time.pack(expand=True, padx=2)
        self.btn.pack(pady= 10)

        self.canvas.place(x = 0, y = 0)

        self.toggleTrans()
        self.hide()
        self.setOnTopfullscreen()
        #self.checkCountdowntxt()  y

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
            self.time.configure(fg=self.color_trans_fg); self.time.configure(bg="#222")
            self.btn.configure(fg=self.color_trans_fg); self.btn.configure(bg="#222222")
            self.root.configure(bg=self.color_trans_bg)
        else:
            self.root.overrideredirect(0)
            self.time.configure(fg=self.color_trans_fg); self.time.configure(bg=self.color_trans_bg)
            self.btn.configure(fg=self.color_normal_fg); self.btn.configure(bg=self.color_normal_bg)
            self.root.configure(bg=self.color_normal_bg)
            
        self.move = not self.move

    def hide(self):
        self.root.withdraw()
    
    def show(self):
        self.root.update()
        self.root.deiconify()

    def write(self,msg):
        self.localcountdown.set(msg)
        self.show()
        self.root.lift()
        #self.root.after(5000, self.hide)

if __name__ == '__main__':
 
    root = tk.Tk()
    root.call('wm', 'attributes', '.', '-topmost', '1')

    windowWidth = root.winfo_screenwidth()
    windowHeight = root.winfo_screenheight()
    root.title("Move Speedometer windows")
    root.geometry("170x50+{}+{}".format(windowWidth - 470, 0)) #Whatever size
    root.overrideredirect(1) #Remove border
    root.wm_attributes("-transparentcolor", "#666666")
    root.attributes('-topmost', 1)
    root.configure(bg='#666666')

    #root.withdraw()

    ml = MumbleLink()

    conf = Configuration()

    #Whatever buttons, etc 

    meter = Meter()

    if show_checkpoints_window:
        racer = Racer()
        countdownWidget = Countdown()
        message = Message()
    
    """
    def toggleAll():

        if not show_checkpoints_window:
                meter.toggleTrans()
        else:
            if meter.move == racer.move:
                meter.toggleTrans()
                racer.toggleTrans()
                countdownWidget.toggleTrans()
            else:
                if meter.move:
                    racer.toggleTrans()
                else:
                    meter.toggleTrans()

        

    t_11 = tk.Button(root, text='Move Speedometer windows', command=lambda:toggleAll() ,fg="white", bg="#222222", relief='flat')
    t_11.pack(anchor="ne")
    """

    meter.updateMeterTimer()

    root.mainloop()
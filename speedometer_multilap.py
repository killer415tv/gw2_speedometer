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
import websocket
from scipy.spatial import distance
import pynput.keyboard._win32 
import pynput.mouse._win32 
from pynput.keyboard import Key, Controller
from pynput import keyboard
import csv
import sys
from pathlib import Path
import numpy as np
from datetime import date
import json
import pandas as pd

import random

import paho.mqtt.client as mqtt #import the client1
import time

import threading
from threading import Thread
import queue

import requests

from configparser import RawConfigParser
import shlex, subprocess

from websocket import WebSocketConnectionClosedException

from mumblelink import MumbleLink

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
geometry_racer = "750x500+0+400"

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
#ghost_mode
enable_ghost_keys = 1
ghost_start = 't'
recalculate_ghost = 'y'

#show timer
hud_slope = 0 # 1 = on , 0 = off

#show timer
hud_speed = 1 # 1 = on , 0 = off

#show log distance in metres
hud_distance = 0 # 1 = on , 0 = off

#show velocity and colorarc
hud_gauge = 1 # 1 = on , 0 = off

#show acceleration, shows the acceleration number on hud
hud_acceleration = 0 # 1 = on , 0 = off

#show Angle meter, shows angles between velocity and mouse camera , and velocity and avatar angle 
hud_angles = 0 # 1 = on , 0 = off 
hud_angles_bubbles = 0 # 1 = on , 0 = off
hud_angles_airboost = 0
hud_max_speed = 0
magic_angle = 58 # angle for hud_angles_bubbles, to show a visual guide of the magic angle

#show drift hold meter
hud_drift_hold = 0
drift_key = 'c' # for special keys like ALT use 'Key.alt_l' more info https://pynput.readthedocs.io/en/latest/_modules/pynput/keyboard/_base.html#Key
#show race assistant window, map selection and multiplayer
show_checkpoints_window = 1 

player_color = "#333333"

game_focus = 0

client = ""
mapId = 0
lastMapId = 0

use_websocket = 1
websocket_host = "beetlerank.com"
websocket_port = 1234

websocket_client = None
websocket_client_thread = None

# workaround for using websocket on_message together with tkinter variables
websocket_countdown_received = False
websocket_countdown_active = False
websocket_countdown_ends_on = None

winh = 110
winw = 200

_3Dpos = [0,0,0]
_last3Dpos = [0,0,0]
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
slope = 0
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

map_angle = 0

checkpoints_list = []

#-----------------------------
#  END CONFIGURATION VARIABLES
#-----------------------------

from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
FR_PRIVATE  = 0x10
FR_NOT_ENUM = 0x20

def loadfont(fontpath: str, private=True, enumerable=False):
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

loadfont(str(Path(sys.argv[0]).parent / "font.ttf"))
loadfont(str(Path(sys.argv[0]).parent / "fonts/Montserrat-Regular.ttf"))

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
        global hud_angles
        global hud_angles_bubbles
        global magic_angle
        global hud_acceleration
        global hud_gauge
        global hud_speed
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
        global hud_slope
        global use_websocket
        global websocket_host
        global websocket_port

        cfg.add_section("general")

        cfg.set("general", "speed_in_3D", speed_in_3D)
        cfg.set("general", "hud_slope", hud_slope)
        cfg.set("general", "enable_livesplit_hotkey", enable_livesplit_hotkey)
        cfg.set("general", "live_start", live_start)
        cfg.set("general", "live_reset", live_reset)
        cfg.set("general", "log", log)
        cfg.set("general", "hud_angles", hud_angles)
        cfg.set("general", "hud_angles_bubbles", hud_angles_bubbles)
        cfg.set("general", "hud_angles_airboost", hud_angles_airboost)
        cfg.set("general", "hud_max_speed", hud_max_speed)
        cfg.set("general", "magic_angle", magic_angle)
        cfg.set("general", "hud_acceleration", hud_acceleration)
        cfg.set("general", "hud_gauge", hud_gauge)
        cfg.set("general", "hud_speed", hud_speed)
        cfg.set("general", "hud_distance", hud_distance)
        cfg.set("general", "enable_ghost_keys", enable_ghost_keys)
        cfg.set("general", "ghost_start", ghost_start)
        cfg.set("general", "recalculate_ghost", recalculate_ghost)
        cfg.set("general", "show_checkpoints_window", show_checkpoints_window)
        cfg.set("general", "hud_drift_hold", hud_drift_hold)
        cfg.set("general", "drift_key", drift_key)
        if player_color == None:
            player_color = '#333333'
        cfg.set("general", "player_color", player_color)
        cfg.set("general", "use_websocket", use_websocket)
        cfg.set("general", "websocket_host", websocket_host)
        cfg.set("general", "websocket_port", websocket_port)

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
        global hud_slope
        global enable_livesplit_hotkey
        global live_start
        global live_reset
        global log
        global hud_angles
        global hud_angles_bubbles
        global magic_angle
        global hud_acceleration
        global hud_gauge
        global hud_speed
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
        global use_websocket
        global websocket_host
        global websocket_port

        if cfg.read(["./config.txt"]):

            if cfg.has_option("general", "speed_in_3D"):
                speed_in_3D = int(cfg.get("general", "speed_in_3D"))
            if cfg.has_option("general", "hud_slope"):
                hud_slope = int(cfg.get("general", "hud_slope"))
            if cfg.has_option("general", "enable_livesplit_hotkey"):
                enable_livesplit_hotkey = int(cfg.get("general", "enable_livesplit_hotkey"))
            if cfg.has_option("general", "live_start"):
                live_start = cfg.get("general", "live_start")
            if cfg.has_option("general", "live_reset"):
                live_reset = cfg.get("general", "live_reset")
            if cfg.has_option("general", "log"):
                log = int(cfg.get("general", "log"))
            if cfg.has_option("general", "hud_angles"):
                hud_angles = int(cfg.get("general", "hud_angles"))
            if cfg.has_option("general", "hud_angles_bubbles"):
                hud_angles_bubbles = int(cfg.get("general", "hud_angles_bubbles"))
            if cfg.has_option("general", "hud_angles_airboost"):
                hud_angles_airboost = int(cfg.get("general", "hud_angles_airboost"))
            if cfg.has_option("general", "hud_max_speed"):
                hud_max_speed = int(cfg.get("general", "hud_max_speed"))
            if cfg.has_option("general", "magic_angle"):
                magic_angle = int(cfg.get("general", "magic_angle"))
            if cfg.has_option("general", "hud_acceleration"):
                hud_acceleration = int(cfg.get("general", "hud_acceleration"))
            if cfg.has_option("general", "hud_gauge"):
                hud_gauge = int(cfg.get("general", "hud_gauge"))
            if cfg.has_option("general", "hud_speed"):
                hud_speed = int(cfg.get("general", "hud_speed"))
            if cfg.has_option("general", "hud_distance"):
                hud_distance = int(cfg.get("general", "hud_distance"))
            if cfg.has_option("general", "enable_ghost_keys"):
                enable_ghost_keys = int(cfg.get("general", "enable_ghost_keys"))
            if cfg.has_option("general", "ghost_start"):
                ghost_start = cfg.get("general", "ghost_start")
            if cfg.has_option("general", "recalculate_ghost"):
                recalculate_ghost = cfg.get("general", "recalculate_ghost")
            if cfg.has_option("general", "show_checkpoints_window"):
                show_checkpoints_window = int(cfg.get("general", "show_checkpoints_window"))
            if cfg.has_option("general", "hud_drift_hold"):
                hud_drift_hold = int(cfg.get("general", "hud_drift_hold"))
            if cfg.has_option("general", "drift_key"):
                drift_key = (cfg.get("general", "drift_key"))
            if cfg.has_option("general", "player_color"):
                player_color = (cfg.get("general", "player_color"))
            if cfg.has_option("general", "geometry_speedometer"):
                geometry_speedometer = (cfg.get("general", "geometry_speedometer"))
            if cfg.has_option("general", "geometry_racer"):
                geometry_racer = (cfg.get("general", "geometry_racer"))
            if cfg.has_option("general", "use_websocket"):
                use_websocket = int(cfg.get("general", "use_websocket"))
            if cfg.has_option("general", "websocket_host"):
                websocket_host = (cfg.get("general", "websocket_host"))
            if cfg.has_option("general", "websocket_port"):
                websocket_port = (cfg.get("general", "websocket_port"))
        else:
            # Generate a default config file with default values
            self.saveConf()

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
        Thread.__init__(self, group, target, name, args, kwargs, daemon=daemon)

        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self):
        Thread.join(self)
        return self._return

class Meter():
    
    def angle_between360(self, v1, v2):
        dot = v1.dot(v2)
        det = v1[0]*v2[1] - v1[1]*v2[0]
        deg = np.rad2deg(np.arctan2(-det, -dot)) + 180
        return str(round(deg, 2))

    def uploadLog(self,guildhall,old_filename,ml):
        headers = {
            'Origin': 'null',
            'Referer': 'null'
        }
        response = requests.post('https://www.beetlerank.com/upload-log',
                                 data={'user': json.loads(ml.data.identity)["name"], 'guildhall': guildhall},
                                 files={'file': open(Path(sys.argv[0]).parent / "logs" / old_filename, 'rb')},
                                 headers=headers)
        print("Log uploaded to web")



        print(response.text)
        return response.text
        
    def setOnTopfullscreen(self):
        self.root.attributes('-topmost', 1)
        self.root.after(500, self.setOnTopfullscreen)

    def on_press(self,key):
        global filename_timer
        global drift_key

        try:
            if str(key).replace("'","") == str(drift_key).replace("'",""):
                if self.drifting == False:
                    self.drift_time = time.perf_counter() 
                self.drifting = True
                
            
        except AttributeError:
            None

    def on_release(self,key):
        global drift_key
        try:
            if str(key).replace("'","") == str(drift_key).replace("'",""):
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
        
        self.lastNonZero = 0
        self.lastNonZero_slope = 0
        self.lastNonZero_accel = 0

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
            
            self.outer_airdrift_box = self.canvas.create_rectangle(20 + 306, 80,30 + 306, 150, outline="#666666", width="1", tags="airdrift_meter_border")
            self.inner_airdrift_box = self.canvas.create_rectangle(23 + 306, 83,27 + 306, 147, outline="#666666", fill='#666666', width="5", tags="airdrift_meter")
            self.airdrift_label = tk.Label(self.root, textvariable = self.airdrift_angle_tk, fg = "white", bg="#666666", font=("Digital-7 Mono", 9)).place(x = 17 + 306, y = 152)

        if hud_acceleration:
            self.accelvar = tk.StringVar(self.root,0)
        if hud_slope:
            self.slopevar = tk.StringVar(self.root,0)
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

            self.outer_drifting_box = self.canvas.create_rectangle(20+45,80,30+45,150, outline="white", width="1", tags="drift_meter_border")
            self.inner_drifting_box = self.canvas.create_rectangle(23+45,83,27+45,147, outline="#ff5436", fill='#ff5436', width="5", tags="drift_meter")
            self.drifting_label = tk.Label(self.root, textvariable = self.drift_time_tk, fg = "white", bg="#666666", font=("Digital-7 Mono", 9)).place(x = 58, y = 152)

        if hud_angles:
            self.angletext = tk.Label(self.root, text="Cam    Beetle", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 166, y = 42)
            self.anglenum = tk.Label(self.root, textvariable = self.anglevar, fg = "white", bg="#666666", font=("Digital-7 Mono", 8, "bold")).place(x = 165, y = 54)
        
        if hud_acceleration:
            self.acceltext = tk.Label(self.root, text="Accel.", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 111, y = 94)
            self.accelnum = tk.Label(self.root, textvariable = self.accelvar, fg = "white", bg="#666666", font=("Digital-7 Mono", 8, "bold")).place(x = 111, y = 105)

        if hud_slope:
            self.acceltext = tk.Label(self.root, text="Slope", fg = "white", bg="#666666", font=("Lucida Console", 7)).place(x = 260, y = 94)
            self.accelnum = tk.Label(self.root, textvariable = self.slopevar, fg = "white", bg="#666666", font=("Digital-7 Mono", 8, "bold")).place(x = 260, y = 105)

        
        if hud_speed:
            #self.numero = tk.Label(self.root, textvariable = self.var100, fg = "white", bg="#666666", font=("Montserrat", 45, "")).place(relx = 1, x = -412, y = 73, anchor = 'ne')
            self.numero = tk.Label(self.root, textvariable = self.var100, fg = "white", bg="#666666", font=("Montserrat Regular", 49, "")).place(anchor="center", x = 200, y = 115)
        if hud_gauge:
            self.canvas.create_arc( 100,20,  300,220, extent=359, start=0,style='arc', outline="#666666", width="28", tags="arc")
            self.canvas.create_arc( 100,20,  300,220, extent=359, start=0,style='arc', outline="#333", width="16", tags="arcbg")
            self.canvas.create_arc( 100,20,  300,220, extent=359, start=0,style='arc', outline="#666666", width="14", tags="arcbg")

            #trans
            #self.canvas.create_arc(100,20,  300,220, extent=180, start=0,style='arc', outline="#666666", width="10", tags="arc1")
            ##azul
            #self.canvas.create_arc(100,20,  300,220, extent=10, start=260,style='arc', outline="#7897ff", width="10", tags="arc2")
            ##morado
            #self.canvas.create_arc(100,20,  300,220, extent=30, start=230,style='arc', outline="#c970cc", width="10", tags="arc3")
            ##amarillo
            #self.canvas.create_arc(100,20,  300,220, extent=50, start=180,style='arc', outline="#ff8a36", width="10", tags="arc4")
            ##rojo
            #self.canvas.create_arc(100,20,  300,220, extent=90, start=90,style='arc', outline="#ff5436", width="10", tags="arc5")

            #speed
            self.canvas.create_arc(100,20,  300,220, extent=0, start=90,style='arc', outline="#bb0", width="1", tags="maxspeedarc")
            self.canvas.create_arc(100,20,  300,220, extent=0, start=90,style='arc', outline="#ff0", width="5", tags="speedarc")

            if hud_max_speed:
                #self.max_meter_meter = self.canvas.create_line(winw, winw, 20, winw,fill='lime',width=4)
                self.max_speed.set(7250)
                self.updateMeterLine(0.5, "maxspeedarc")
                self.max_speed.trace_add('write', self.updateMeterMaxSpeed)

            #self.meter = self.canvas.create_line(200, 120, 200, 20,fill='white',width=4)
            self.angle = 0.2
            self.updateMeterLine(self.angle, "speedarc")   
        if hud_speed or hud_gauge:
            self.var.trace_add('write', self.updateMeter)  # if this line raises an error, change it to the old way of adding a trace: self.var.trace('w', self.updateMeter)



        #if hud_speed:
        self.vartime = tk.StringVar(self.root, "")
        self.timenum_label = tk.Label(self.root, textvariable = self.vartime, fg = "#eee", bg="#666666", font=("Digital-7 Mono", 20)).place(x = 144, y = 155)
        self.distance = tk.StringVar(self.root, "")
        self.distance_label = tk.Label(self.root, textvariable = self.distance, fg = "#eee", bg="#666666", font=("Digital-7 Mono", 15)).place(anchor="center",x = 200, y = 200)
        self.steps_txt = tk.StringVar(self.root, "")
        self.steps0 = tk.Label(self.root, textvariable = self.steps_txt, fg = "#fff", bg="#666666", font=("Lucida Console", 9, "bold")).place(anchor="center", x = 200, y = 242)
        self.step1_txt = tk.StringVar(self.root, "")
        self.steps1 = tk.Label(self.root, textvariable = self.step1_txt, fg = "#eeeeee", bg="#666666", font=("Digital-7 Mono", 10)).place(anchor="center",x = 200, y = 153)

        self.canvas.create_circle(200, 120, 96, fill="#666666", outline="#666666", width=2)

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

    def updateMeterLine(self, speed, line):
        """Draw a meter line"""

        i = self.canvas.find_withtag(line)

        #convert speeed to angle

        angle = speed * 359 / 100

        self.canvas.itemconfig(i, extent=angle)
        color = "#aaa"      
        if line == "speedarc": 
            if speed < -40:
                color = "#7897ff" #"#2294a8"
            if speed < -50:
                color = "#c970cc" #"#c970cc"
            if speed < -60:
                color = "#ff8a36" #"#edad18"
            if speed < -72:
                color = "#ff5436"

        self.canvas.itemconfig(i, outline=color)

        #x = 200 * cos(angle * pi)
        #y = 120 * sin(angle * pi)
        #self.canvas.coords(line, winw, winw, x, y)

    def updateMeter(self, name1, name2, op):
        global hud_gauge

        #print(self.var.get(), self.angle)
        if hud_gauge:
            self.updateMeterLine(-self.var.get(), "speedarc")

    def updateMeterMaxSpeed(self, name1, name2, op):
        """Convert variable to angle on trace"""

        self.updateMeterLine(-self.max_speed.get(), "maxspeedarc")

    def calculateAcceleration(self):
        global velocity
        global _lastVel

        global _time
        global _lastTime

        if (velocity and _lastVel):
            self.lastNonZero_accel = time.time()
            acceleration = round(((velocity - _lastVel) / (_time - _lastTime))/100)
            self.accelvar.set(acceleration);
            return acceleration
        else:
            if time.time() > self.lastNonZero_accel + 0.05:
                self.accelvar.set(0);
                return 0
    
    def calculateSlope(self, pos1, pos2):
        global _3Dpos
        global _last3Dpos
        global slope

        a = _3Dpos[1] - _last3Dpos[1]
        b = distance.euclidean([_3Dpos[0],_3Dpos[2]], [_last3Dpos[0],_last3Dpos[2]])

        if (b):
            slope = round(np.rad2deg(np.arctan(a/b)))
        else:
            slope = 0

        if slope:
            self.lastNonZero_slope = time.time()
            self.slopevar.set(slope);
        else:
            if time.time() > self.lastNonZero_slope + 0.05:
                None
                self.slopevar.set(slope);
            
            

        slope2 = round((_3Dpos[1] -_last3Dpos[1])*10000 )/100
        



    def updateMeterTimer(self):

        global _lastPos
        global _lastVel
        global _lastTick
        global _lastTime
        global velocity
        global _time
        global _pos
        global _3Dpos
        global _last3Dpos
        global _tick
        global timer
        global color
        global speed_in_3D


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
        global cup_name
        global guildhall_laps

        global racer
        global client
        global map_position_last_time_send

        global use_websocket
        global websocket_client

        global mapId
        global lastMapId

        global game_focus
        global hud_slope


        if hud_drift_hold:
            
            i = self.canvas.find_withtag("drift_meter")
            b = self.canvas.find_withtag("drift_meter_border")
            if self.drifting:
                seconds = round((time.perf_counter() - self.drift_time) * 100)/100
                self.drift_time_tk.set(round((time.perf_counter() - self.drift_time) * 10)/10)
                pixels = min(64,round(seconds * 64 / 1.2))
                self.canvas.coords(i, 23+45, 147-pixels , 27+45, 147)
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
                self.canvas.coords(i, 23+45, 147 , 27+45, 147)
                self.canvas.itemconfig(i, outline="white")
                self.canvas.itemconfig(i, fill="white")
                self.canvas.itemconfig(b, outline="#666")


        def different(v1,v2):
            if ( v1[0] == v2[0] and v1[1] == v2[1] and v1[2] == v2[2] ):
                return False
            else:
                return True

        def checkpoint(step, stepName, coords, radius):

            global checkpoints_list

            global last_checkpoint_position
            global _3Dpos
            global _last3Dpos
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
            global map_angle    

            global acceleration                                    

            #if csv checkpoints has no radius , default is 5 for reset and 15 for the rest
            if radius == 0:
                if step == -1:
                    radius = 5
                else: 
                    radius = 15

            if step == -1:
                arraystep = (ctypes.c_float * len(coords))(*coords)
                #la distancia de 5 es como si fuera una esfera de tamaño similar a una esfera de carreras de tiria
                if distance.euclidean(_3Dpos, arraystep) < radius and (pressedQ == 0 or different(last_checkpoint_position, arraystep)):
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
                    tmhud.write("")
                    self.distance.set("")
                    lap = 1
            

            total_laps = int(guildhall_laps.get()[:1])

            #only valid steps are the next one, or the first one
            if step == next_step or step == 0:

                step0 = coords
                arraystep0 = (ctypes.c_float * len(step0))(*step0)
                if distance.euclidean(_3Dpos, arraystep0) < radius and (pressedQ == 0 or different(last_checkpoint_position, arraystep0)):
                    
                    if 'racer' in globals():
                        if stepName == "end":
                            racer.saveCheckpoint(0)
                        else:
                            racer.saveCheckpoint(int(step) + 1)

                    last_checkpoint_position = arraystep0
                    if stepName == "start":
                        next_step = 1
                        
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
                            tmhud.write("")
                            self.distance.set("")
                            total_distance = 0
                            total_timer = _time
                            lap_timer = _time
                            #esta línea es la clave

                            #paso 1 - comprobar que existe la carpeta /logs
                            if not (Path(sys.argv[0]).parent / "logs").exists():
                                (Path(sys.argv[0]).parent / "logs").mkdir()



                            filename = guildhall_name.get() + "_log_" + str(_time) + ".csv"
                            if log:
                                #print("----------------------------------")
                                #print("NEW LOG FILE - " + filename)
                                #print("----------------------------------")
                                writer = open(Path(sys.argv[0]).parent / "logs" / filename, 'a', newline='', encoding='utf-8')
                                writer.seek(0,2)
                                writer.writelines( (',').join(["X","Y","Z","SPEED","ANGLE_CAM", "ANGLE_BEETLE","TIME", "ACCELERATION", "MAP_ANGLE"]))
                            if show_checkpoints_window and racer.session_id.get() != "":
                                #mqtt se manda el tiempo como inicio
                                racer.sendMQTT({"option": "s", "lap": lap, "time" : 0, "user": racer.username.get()})
                                #racer.sendWebsocket({"option": "s", "lap": lap, "time" : 0, "user": racer.username.get()})
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
                                writer = open(Path(sys.argv[0]).parent / "logs" / filename, 'a', newline='', encoding='utf-8')
                                writer.seek(0,2)
                                writer.writelines( (',').join(["X","Y","Z","SPEED","ANGLE_CAM", "ANGLE_BEETLE","TIME", "ACCELERATION", "MAP_ANGLE"]))
                            if show_checkpoints_window and racer.session_id.get() != "":
                                #mqtt se manda el tiempo como inicio
                                racer.sendMQTT({"option": "s", "lap": lap, "step": 0, "time" : steptime, "user": racer.username.get()})
                                #racer.sendWebsocket({"option": "s", "lap": lap, "step": 0, "time" : steptime, "user": racer.username.get()})

                        

                    if stepName == "end":
                        next_step = 0
                        steptime = _time - total_timer
                        steptime_lap = _time - lap_timer
                        pressedQ = 0.5
                        

                        if filename != "":
                            

                            #upload log to 

                            old_filename = filename
                            filename = ""

                            if upload.get() == 1:
                                if log:
                                    twrv = ThreadWithReturnValue(target=self.uploadLog, args=(guildhall_name.get(),old_filename, ml,))
                                    twrv.start()
                                    if int(total_laps) == 1:
                                        message.write(twrv.join())
                                    
                                    
                                    racer.saveGuildhall(guildhall_name.get())

                            if int(lap) == int(total_laps):
                                
                                last_filename_df = pd.DataFrame()
                                file_df = pd.read_csv(Path(sys.argv[0]).parent / "logs" / old_filename)
                                last_filename_df = last_filename_df.append(file_df)

                                current_time = last_filename_df.values[-1][6]                                
                                datefinish = datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(current_time), "%M:%S:%f")[:-3]
                                
                                if enable_livesplit_hotkey == 1:
                                    keyboard_.press(live_start)
                                    keyboard_.release(live_start)

                                #filename = ""
                                #print("----------------------------------")
                                #print("CHECKPOINT FINAL RACE: " + datefinish)
                                #print("----------------------------------")
                                newline = self.step1_txt.get() + "\n"
                                self.step1_txt.set(str(lap) + "/"+ str(total_laps) + " TF " + datefinish)
                                
                                self.vartime.set(datefinish)
                                tmhud.write(datefinish)
                                

                                if log:
                                    #store in file the record time of full track , today date and player name
                                    now = datetime.datetime.now()
                                    today_date = now.strftime("%d/%m/%Y %H:%M:%S")
                                    folder = str(Path(sys.argv[0]).parent / guildhall_name.get())
                                    writer = open(folder + "_records.csv", 'a', newline='', encoding='utf-8')
                                    writer.seek(0,2)
                                    writer.writelines("\r")
                                    writer.writelines( (',').join([datefinish, today_date, json.loads(ml.data.identity)["name"]]))

                                if show_checkpoints_window and racer.session_id.get() != "":
                                    #mqtt se manda el tiempo como inicio
                                    racer.sendMQTT({"option": "f", "lap":lap, "time": steptime, "step": 999, "user": racer.username.get()})
                                    #racer.sendWebsocket({"option": "f", "lap":lap, "time": steptime, "step": 999, "user": racer.username.get()})
                                
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
                                    #racer.sendWebsocket({"option": "f", "lap": lap, "step": 998, "time" : steptime, "user": racer.username.get()})
                                
                                lap = lap + 1

                            """ 
                            #stores in counterDone.txt number of total laps done
                            file = open(Path(sys.argv[0]).parent / "counterDone.txt")
                            global numero_contador
                            line = file.read()
                            if line == '':
                                line = "1"
                            numero_contador = int(line.strip()) + 1
                            file.close()
                            file = open(Path(sys.argv[0]).parent / "counterDone.txt", "w")
                            file.write(str(numero_contador))
                            file.close()
                            """

                            if enable_ghost_keys:
                                keyboard_.press(recalculate_ghost)
                                keyboard_.release(recalculate_ghost)

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
                        
                        if show_checkpoints_window and racer.session_id.get() != "":
                            #mqtt se manda el tiempo como inicio
                            racer.sendMQTT({"option": "c", "step": step, "lap": lap, "time": steptime, "user": racer.username.get()})
                            #racer.sendWebsocket({"option": "c", "step": step, "lap": lap, "time": steptime, "user": racer.username.get()})

        
        """Fade over time"""
        #print("actualiza", flush=True)
        #toma de datos nueva
        ml.read()

        game_status = '{0:08b}'.format(ml.context.uiState)
        game_focus = game_status[4]

        mapId = ml.context.mapId
        if (mapId != lastMapId):
            lastMapId = ml.context.mapId

            if (guildhall_name.get() != 'None, im free!'):
                if (ml.context.mapId == 54):
                    racer.changeCup("TYRIACUP")
                    racer.saveGuildhall("TYRIA BRISBAN WILD.")
                elif (ml.context.mapId == 39):
                    racer.changeCup("TYRIACUP")
                    racer.saveGuildhall("TYRIA INF.LEAP")
                elif (ml.context.mapId == 32):
                    racer.changeCup("TYRIACUP")
                    racer.saveGuildhall("TYRIA DIESSA PLATEAU")
                elif (ml.context.mapId == 31):
                    racer.changeCup("TYRIACUP")
                    racer.saveGuildhall("TYRIA SNOWDEN DRIFTS")
                elif (ml.context.mapId == 24):
                    racer.changeCup("TYRIACUP")
                    racer.saveGuildhall("TYRIA GENDARRAN")
                elif (ml.context.mapId == 1330):
                    racer.changeCup("TYRIACUP")
                    racer.saveGuildhall("TYRIA GROTHMAR VALLEY")
        
        if hud_slope:    
            self.calculateSlope(_3Dpos,_last3Dpos)

        _tick = ml.data.uiTick
        _time = time.time()
        _last3Dpos = _3Dpos
        _3Dpos = ml.data.fAvatarPosition

        if speed_in_3D:
            _pos = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[1],ml.data.fAvatarPosition[2]]
        else:
            _pos = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[2]]

        if show_checkpoints_window and 'racer' in globals():  
            if ml.data.identity != "":
                racer.username.set(json.loads(ml.data.identity).get("name"))
            else: 
                racer.username.set("anon")

        if _lastTime + timer <= _time:
            pressedQ = max(pressedQ - timer, 0)

            if show_checkpoints_window: 

                # check checkpoints
                if len(checkpoints_list):
                    for index, checkpoint_data in checkpoints_list.iterrows():
                        if "RADIUS" in checkpoint_data:
                            radius = checkpoint_data['RADIUS']
                        else:
                            radius = 0
                        #print(checkpoint_data['STEP'], checkpoint_data['STEPNAME'], [checkpoint_data['X'],checkpoint_data['Y'],checkpoint_data['Z']] )
                        checkpoint(checkpoint_data['STEP'], checkpoint_data['STEPNAME'], [checkpoint_data['X'],checkpoint_data['Y'],checkpoint_data['Z']], radius )

            #DEBUG
            #print(list(_pos) , flush=True)
            #dst = distance.euclidean(_pos, _lastPos)
            #print(_pos, _pos)
            #calculo de velocidad quitando eje Y (altura)

            dst = distance.euclidean(_pos, _lastPos)
            total_distance = total_distance + dst
            velocity = dst * 39.3700787 / timer
            
            #if velocity > 0.0:

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

                def angle_between360(v1, v2):
                    dot = v1.dot(v2)
                    det = v1[0]*v2[1] - v1[1]*v2[0]
                    deg = np.rad2deg(np.arctan2(-det, -dot)) + 180
                    return str(round(deg, 2))

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
                    global map_angle
                    map_angle = float(angle_between([0 , 1], uaf))+180
                    
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
                            self.canvas.coords(i, 23 + 306, 147-pixels , 27 + 306, 147)
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
                if hud_acceleration:
                    acceleration = self.calculateAcceleration()
                else:
                    acceleration = 0

                    
                #escribir velocidad,tiempo,x,y,z en fichero, solo si está abierto el fichero y si está habilitado el log
                
                def roundstr(a):
                    return str(round(a * 10000)/10000)

                if filename != "" and round((velocity*100/10000)*99/72) < 150:
                    #print([filename,str(_pos[0]),str(_pos[1]),str(_pos[2]),str(velocity), str(_time - total_timer)])
                    
                    self.vartime.set(datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - total_timer), "%M:%S:%f")[:-3])
                    tmhud.write(datetime.datetime.strftime(datetime.datetime.utcfromtimestamp(_time - total_timer), "%M:%S:%f")[:-3])
                    if hud_distance:
                        self.distance.set(str(round(total_distance)) + "m.")
                    if log and velocity > 0:
                        writer = open(Path(sys.argv[0]).parent / "logs" / filename, 'a', newline='', encoding='utf-8')
                        writer.seek(0,2)
                        writer.writelines("\r")
                        writer.writelines( (',').join([roundstr(_3Dpos[0]),roundstr(_3Dpos[1]),roundstr(_3Dpos[2]),str(round((velocity*100/10000)*99/72)),roundstr(angle_between_res1),roundstr(angle_between_res2), str(_time - lap_timer), roundstr(acceleration),roundstr(map_angle)]))

                
                if velocity > 0:
                    color = "#666666"                
                if velocity > 4000:
                    color = "#666666" #"#2294a8"
                if velocity > 5000:
                    color = "#666666" #"#c970cc"
                if velocity > 6000:
                    color = "#666666" #"#edad18"
                if velocity > 7250:
                    color = "#666666" #"#de1f18"

                if velocity > 0:
                    self.lastNonZero = time.time()
                    if round(velocity*100/10000) < 140:
                        self.var.set(round(velocity*100/10000))
                        self.var100.set(round((velocity*100/10000)*99/72))
                        i = self.canvas.find_withtag("arc")
                        self.canvas.itemconfig(i, outline=color)
                        _lastVel = velocity
                else:
                    if time.time() > self.lastNonZero + 0.05:
                        if round(velocity*100/10000) < 140:
                            self.var.set(round(velocity*100/10000))
                            self.var100.set(round((velocity*100/10000)*99/72))
                            i = self.canvas.find_withtag("arc")
                            self.canvas.itemconfig(i, outline=color)
                            _lastVel = velocity
                        
                                    
            _lastTime = _time
            _lastPos = _pos
            #_lastVel = velocity
            _lastTick = _tick


        if 'racer' in globals() and (client != "" or websocket_client):
            if map_position_last_time_send != round(_time * 10 / 2):
                map_position_last_time_send = round(_time * 10 / 2)
                if not (ml.data.fAvatarPosition[0] == 0 and ml.data.fAvatarPosition[1] == 0 and ml.data.fAvatarPosition[2] == 0):
                    if client != "":
                        racer.sendMQTT(
                            {
                                "option": "position", 
                                "x": ml.data.fAvatarPosition[0], 
                                "y": ml.data.fAvatarPosition[1],
                                "z": ml.data.fAvatarPosition[2], 
                                "user": racer.username.get(), 
                                "map": guildhall_name.get(),
                                "color": player_color
                            }
                        )

                    if websocket_client:
                        south = np.array([0, -1])
                        avatar_direction = np.array([ml.data.fAvatarFront[0], ml.data.fAvatarFront[2]])

                        event = {
                            "type": "position",
                            "option": "position",
                            "map": guildhall_name.get(),
                            "x": ml.data.fAvatarPosition[0],
                            "y": ml.data.fAvatarPosition[2],
                            "z": ml.data.fAvatarPosition[1],
                            "angle": self.angle_between360(avatar_direction, south),
                            "user": racer.username.get(),
                            "timestamp": time.time(),
                            "color": player_color
                        }
                        try:
                            websocket_client.send(json.dumps(event))
                        except WebSocketConnectionClosedException:
                            pass

        self.root.after(10, self.updateMeterTimer)


class Racer():

    def setOnTopfullscreen(self):
        global game_focus
        if game_focus == 1:
            self.root.attributes('-topmost', 1)
        self.root.after(5000, self.setOnTopfullscreen)

    def on_message_websocket(self, client, userdata, message):
        pass

    def on_message_MQTT(self, client, userdata, message):
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
            
            self.timestamps = []

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-3":
            #print("3!!")
            self.thread_queue.put("3...")
            countdowntxt = "3"
            
            self.timestamps = []

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-2":
            #print("2!!")
            self.thread_queue.put("2...")
            countdowntxt = "2!"
            

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-1":
            #print("1!!")
            self.thread_queue.put("1...")
            countdowntxt = "1!!"
            

            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1
        if received.get('option') == "321GO-GO":
            #print("GO GO GO!!")
            self.thread_queue.put("GOGOGOGO")
            countdowntxt = "Brr!"
            
            # limpiar ranking de partida
            # falta mostrar por pantalla el 3 2 1

    def sendMQTT(self, data):
        global client
        if client != "":
            client.publish(self.prefix_topic + self.session_id.get(), json.dumps(data))

    def sendWebsocket(self, data):
        global websocket_client

        print(websocket_client,data)
        try:
            if websocket_client != "":
                websocket_client.send(json.dumps(data))
        except WebSocketConnectionClosedException:
            print("error")

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
        #self.sendWebsocket({"option": "c", "step": 1000, "time": 0 ,"lap": 1, "user": self.username.get()})
        lap = 1
        countdowntxt = ""

    def ready(self):
        self.root.focus_set()
        global lap
        global countdowntxt
        self.sendMQTT({"option": "c", "step": 1001, "time": 0 ,"lap": 1, "user": self.username.get()})
        #self.sendWebsocket({"option": "c", "step": 1001, "time": 0 ,"lap": 1, "user": self.username.get()})
        lap = 1
        countdowntxt = ""
        #test message
        

    def newRace(self):
        self.countdown = self.countdown - 1
        if self.countdown == 0:
            self.sendMQTT({"option": "321GO-GO"})
            #self.sendWebsocket({"option": "321GO-GO"})
        
        if self.countdown > 0:
            self.sendMQTT({"option": "321GO-"+str(self.countdown)})
            #self.sendWebsocket({"option": "321GO-"+str(self.countdown)})
            self.root.after(1000, self.newRace)
        
    def ignore_message(self, client, userdata, message):
        pass

    def open_multiplayer_map(self):
        if not self.mapOpen:
            self.session_id.get()
            subprocess.Popen(["python", Path(sys.argv[0]).parent / "map_realtime_multiplayer.py", self.session_id.get()])
            self.mapOpen = True

    def websocket_countdown_watcher(self):
        global websocket_countdown_active
        global websocket_countdown_received

        if websocket_countdown_received:
            if not websocket_countdown_active:
                websocket_countdown_active = True
                self.update_countdown_label(first=True)
            websocket_countdown_received = False

        self.root.after(100, self.websocket_countdown_watcher)

    def set_countdown_text(self, text, final=False):
        if countdownWidget:
            #countdownWidget.localcountdown.set(text)
            if final:
                self.root.after(2500, lambda: countdownWidget.localcountdown.set(""))

    def update_countdown_label(self, first=False):
        global websocket_countdown_active

        if websocket_countdown_ends_on is None:
            websocket_countdown_active = False
            return

        seconds_remaining = websocket_countdown_ends_on / 1000 - time.time()
        if seconds_remaining > 1:

            self.set_countdown_text(math.ceil(seconds_remaining))
            delay = math.floor((seconds_remaining - math.floor(seconds_remaining)) * 1000) if first else 1000
            self.root.after(delay, self.update_countdown_label)
        elif seconds_remaining > 0:
            self.set_countdown_text("1")
            self.root.after(50, self.update_countdown_label)
        else:
            self.set_countdown_text("GO!", final=True)
            websocket_countdown_active = False

    def joinRace(self):
        global client
        self.root.focus_set()

        #if not use_websocket:
        #ignore old channel
        if client != "":
            client.on_message=self.ignore_message

        self.status.set("JOINED!")
        self.race_status.set("Waiting to start...")
        #print(self.username.get() + " JOINED RACE: " + self.session_id.get())
        #subscribición al topico
        broker_address="www.beetlerank.com"
        #broker_address="iot.eclipse.org"
        #print("creating new instance")
        client = mqtt.Client(client_id=self.username.get() + str(random.random())) #create new instance
        #client.tls_set("./chain.pem")
        #client.tls_insecure_set(True)
        client.on_message=self.on_message_MQTT #attach function to callback
        #print("connecting to broker")
        client.connect(broker_address) #connect to broker
        client.loop_start() #start the loop
        #print("Subscribing to topic",self.prefix_topic + str(self.session_id.get()))
        client.subscribe(self.prefix_topic + str(self.session_id.get()))

        #self.thread_queue.put('Waiting for start.')
        #else:
        global websocket_client
        global websocket_client_thread
        global websocket_host
        global websocket_port

        if websocket_client is not None:
            websocket_client.close()
            websocket_client = None
            websocket_client_thread.join()

        def on_message(ws, message):
            data = json.loads(message)

            global websocket_countdown_ends_on
            global websocket_countdown_received
            if data.get("type") == "countdown_start":
                websocket_countdown_ends_on = data.get("ends_on")
                websocket_countdown_received = True

        websocket_host = self.conf_websocket_host_entry.get()
        websocket_port = self.conf_websocket_port_entry.get()

        websocket_client = websocket.WebSocketApp(f"ws://{websocket_host}:{websocket_port}",
                                                    on_message=on_message)

        websocket_client_thread = Thread(target=websocket_client.run_forever)
        websocket_client_thread.daemon = True
        websocket_client_thread.start()

        if not websocket_client.sock:
            print("Failed to connect to websocket server")
            self.websocket_race_status.set("Error")
            return

        conn_timeout = 5
        while websocket_client.sock and not websocket_client.sock.connected and conn_timeout:
            time.sleep(1)
            conn_timeout -= 1

        if not websocket_client.sock or not websocket_client.sock.connected:
            print("Failed to connect to websocket server")
            self.websocket_race_status.set("Error")
            return

        init_packet = {
            "type": "init",
            "client": "speedometer",
            "room": self.session_id.get()
        }
        websocket_client.send(json.dumps(init_packet))
        self.websocket_race_status.set("Connected")

    def reset(self):

        self.root.focus_set()
        self.saveCheckpoint(0)

        global _3Dpos
        global _last3Dpos
        global _time

        global keyboard_
        global filename
        global total_timer
        global lap_timer
        global total_distance

        global lap
        global meter

        global game_focus

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
        tmhud.write("")
        meter.distance.set("")

        lap = 1
        total_distance = 0

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
            self.map_ranking.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.t_1.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.t_2.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.t_3.configure(fg=self.color_trans_fg, bg="#222222")
            self.t_3_2.configure(fg=self.color_trans_fg, bg="#222222")
            self.t_4.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.t_4_4.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.t_4_5.configure(fg="black", bg=self.color_trans_bg)
            self.t_4_6.configure(fg="black", bg=self.color_trans_bg)
            self.t_5.configure(fg=self.color_trans_fg, bg="#222222")
            self.t_6.configure(fg=self.color_trans_fg, bg="#222222")
            #self.t_6_1.configure(fg=self.color_trans_fg); self.t_6_1.configure(bg="#222222")
            self.t_7.configure(fg=self.color_trans_fg, bg="#222222")
            self.t_7_1.configure(fg=self.color_trans_fg, bg="#222222")
            self.t_7_2.configure(fg=self.color_trans_fg, bg="#222222")
            self.t_3_5.configure(fg=self.color_trans_fg, bg="#222222")
            self.t_3_6.configure(fg=self.color_trans_fg, bg="#222222")

            self.websocket_race_status_label.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)

            #self.t_8.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.t_9.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.t_10.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)

            def makeCheckboxTransparent(label, cb):
                label.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
                cb.configure(fg="black", bg=self.color_trans_bg)

            self.conf_move.configure(fg=self.color_trans_fg, bg="#222222")

            for (label, cb) in self.config_checkboxes:
                makeCheckboxTransparent(label, cb)

            self.conf_color_label.configure(bg=self.color_trans_bg)
            self.conf_color_btn.configure(fg=self.color_trans_fg, bg="#222222")
            makeCheckboxTransparent(self.conf_websocket_label, self.conf_websocket_cbtn)
            self.conf_websocket_host_entry.configure(fg=self.color_trans_fg, bg="#222222")
            self.conf_websocket_port_entry.configure(fg=self.color_trans_fg, bg="#222222")
            self.conf_save.configure(fg=self.color_trans_fg, bg="#222222")
            self.conf.configure(fg=self.color_trans_fg, bg="#222222")

            self.root.configure(bg=self.color_trans_bg)
        else:
            self.root.overrideredirect(0)
            self.map_ranking.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_1.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_2.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_3.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_3_2.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_4.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_4_4.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_4_5.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_4_6.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_5.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_6.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            #self.t_6_1.configure(fg=self.color_normal_fg); self.t_6_1.configure(bg=self.color_normal_bg)
            self.t_7.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_7_1.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_7_2.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_3_5.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_3_6.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)

            self.websocket_race_status_label.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)

            #self.t_8.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_9.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.t_10.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)

            def makeCheckboxNormal(label, cb):
                label.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
                cb.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)

            self.conf_move.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)

            for (label, cb) in self.config_checkboxes:
                makeCheckboxNormal(label, cb)

            self.conf_color_label.configure(bg=self.color_normal_bg)
            self.conf_color_btn.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            makeCheckboxNormal(self.conf_websocket_label, self.conf_websocket_cbtn)
            self.conf_websocket_host_entry.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.conf_websocket_port_entry.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.conf_save.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.conf.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)

            self.root.configure(bg=self.color_normal_bg)
            
        self.move = not self.move

    def saveCheckpoint(self,value):
        file = open(Path(sys.argv[0]).parent / "checkpoint.txt", "w")
        file.write(str(value))
        file.close()

    def changeCup(self,value):

        global cup_name

        cup_name.set(value)

        file = open(Path(sys.argv[0]).parent / "cup.txt", "w")
        file.write(str(cup_name.get()))
        file.close()

        guildhall_name.set('SELECT MAP')
        self.t_3_2['menu'].delete(0, 'end')

        # Insert list of new options (tk._setit hooks them up to var)
        path = Path(sys.argv[0]).parent / "maps" / value
        new_choices = [file.stem for file in path.glob('*.csv')]
        for choice in new_choices:
            self.t_3_2['menu'].add_command(label=choice, command=tk._setit(guildhall_name, choice, self.saveGuildhall))
        
        self.saveGuildhall('-')

    def saveGuildhall(self,value):

        global guildhall_name
        global checkpoints_list
        global cup_name
        global game_focus

        guildhall_name.set(value)

        if guildhall_name.get() == 'SELECT MAP': 
            return 
        if guildhall_name.get() == '-': 
            return 
        self.root.focus_set()

        #load checkpoints from file and save to variable

        self.checkpoints_file = Path(sys.argv[0]).parent / "maps" / cup_name.get() / (guildhall_name.get() + ".csv")

        print("-----------------------------------------------")
        print("- THE SELECTED MAP IS" , guildhall_name.get() )
        print("- CHECKPOINTS FILE" , self.checkpoints_file )

        checkpoints_list = pd.DataFrame()
        file_df = pd.read_csv(self.checkpoints_file)
        checkpoints_list = checkpoints_list.append(file_df)

        print("- "+ str(len(checkpoints_list)) + " checkpoints in this map")

        print("-----------------------------------------------")

        file = open(Path(sys.argv[0]).parent / "guildhall.txt", "w", encoding="utf-8")
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
                response = requests.get('https://www.beetlerank.com/rank/api/' + str(guildhall_name.get()) + "/" + self.username.get() , headers)
            
                self.map_ranking_var.set(response.text)

            except:
                self.map_ranking_var.set("")
    
    def __init__(self):
        global guildhall_name
        global guildhall_laps
        global cup_name
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

        #if not use_websocket:
        self.root.after(100, self.listen_for_result)

        cup_name = StringVar(self.root)
        cup_name.set('CUP')

        guildhall_name = StringVar(self.root)
        guildhall_name.set('-')

        guildhall_laps = StringVar(self.root)
        guildhall_laps.set("1 lap")

        self.t_1 = tk.Label(self.root, text="""Race Assistant v2.06.28""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 15))
        self.t_1.place(x=0, y=10)
        self.t_2 = tk.Label(self.root, text="""Choose map to race""", justify = tk.LEFT, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_2.place(x=0, y=40)
        
        #get all list of maps from the maps folder
        path = Path(sys.argv[0]).parent / "maps"
        self.cups = [directory.stem for directory in path.iterdir() if directory.is_dir()]
        self.maps = [file.stem for file in path.glob('*.csv')]
        if len(self.maps) == 0:
            self.maps = ['-']    
        
        self.t_3 = tk.OptionMenu(self.root, cup_name, *self.cups, command = self.changeCup)
        self.t_3.config(font=("Lucida Console", 8))
        self.t_3["highlightthickness"] = 0
        self.t_3["activebackground"] = "#222222"
        self.t_3["activeforeground"] = "white" 
        self.t_3.place(x=19, y=60, width=180, height=18)

        self.t_3_2 = tk.OptionMenu(self.root, guildhall_name, *self.maps, command = self.saveGuildhall)
        self.t_3_2.config(font=("Lucida Console", 8))
        self.t_3_2["highlightthickness"] = 0
        self.t_3_2["activebackground"] = "#222222"
        self.t_3_2["activeforeground"] = "white" 
        self.t_3_2.place(x=19, y=78, width=180, height=18)
        
        self.laps = ['1 lap', '2 laps', '3 laps', '4 laps', '5 laps', '6 laps', '7 laps']
        self.t_3_5 = OptionMenu(self.root, guildhall_laps, *self.laps)
        self.t_3_5["highlightthickness"] = 0
        self.t_3_5["activebackground"] = "#222222"
        self.t_3_5["activeforeground"] = "white"
        self.t_3_5.place(x=199, y=60, width=60, height=36)

        global hud_gauge
        global hud_speed
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
                self.conf_color_label.configure(fg=player_color)
                conf_save()

        def conf_save():
            print("saved and restart")
            global conf
            global websocket_host
            global websocket_port

            websocket_host = self.websocket_host.get()
            websocket_port = self.websocket_port.get()

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

        def createCheckboxLabel(text):
            return tk.Label(
                self.root,
                text=text,
                justify=tk.LEFT,
                padx=20,
                fg=self.fg.get(),
                bg=self.bg.get(),
                font=("Lucida Console", 10),
            )

        self.config_cb_vars = {}

        def createCheckbox(initValue, varName):
            self.config_cb_vars[varName] = IntVar(self.root, initValue)
            return tk.Checkbutton(
                self.root,
                variable=self.config_cb_vars[varName],
                command=lambda: conf_toggle(varName),
                font=("Lucida Console", 10),
                text="",
                borderwidth=0)

        checkboxes = [
            ("Show speed", hud_speed, "hud_speed"),
            ("Show gauge", hud_gauge, "hud_gauge"),
            ("Show slope", hud_slope, "hud_slope"),
            ("Show distance", hud_distance, "hud_distance"),
            ("Show acceleration", hud_acceleration, "hud_acceleration"),
            ("Show angles", hud_angles, "hud_angles"),
            ("Show angle orbs", hud_angles_bubbles, "hud_angles_bubbles"),
            ("Show drift hold", hud_drift_hold, "hud_drift_hold"),
            ("Show airboost helper", hud_angles_airboost, "hud_angles_airboost"),
            #("Enable livesplit hotkeys", enable_livesplit_hotkey, "enable_livesplit_hotkey"),
            ("Enable ghost hotkeys", enable_ghost_keys, "enable_ghost_keys"),
            ("Measure speed in 3D", speed_in_3D, "speed_in_3D"),
            ("Log to file (need if want to upload)", log, "log"),
            ("Show max speed on gauge", hud_max_speed, "hud_max_speed"),
        ]
        self.config_checkboxes = [(createCheckboxLabel(text), createCheckbox(init, varName)) for (text, init, varName) in checkboxes]

        # print(self.config_checkboxes[0][1].var)

        # COLOR
        self.conf_color_label = tk.Label(self.root, text="■", justify = tk.LEFT, padx = 0, fg = player_color, bg=self.bg.get(), font=("Lucida Console", 15))
        self.conf_color_btn = tk.Button(self.root, text='Change color', command=lambda:choose_color() ,font=("Lucida Console", 10))

        # WEBSOCKET OPTIONS
        self.use_websocket = IntVar(self.root, use_websocket)
        self.conf_websocket_label = createCheckboxLabel("Use websocket connection")

        self.websocket_host = StringVar(self.root, websocket_host)
        self.conf_websocket_host_entry = tk.Entry(self.root, textvariable=self.websocket_host, disabledbackground="#444444")
        self.websocket_port = StringVar(self.root, str(websocket_port))
        self.conf_websocket_port_entry = tk.Entry(self.root, textvariable=self.websocket_port, disabledbackground="#444444")

        def update_websocket_conf(toggle=False):
            if toggle:
                conf_toggle("use_websocket")
            state = tk.NORMAL if self.use_websocket.get() else tk.DISABLED
            self.conf_websocket_host_entry.configure(state=state)
            self.conf_websocket_port_entry.configure(state=state)

        self.conf_websocket_cbtn = tk.Checkbutton(
            self.root,
            font=("Lucida Console", 10),
            text="",
            variable=self.use_websocket,
            command=lambda: update_websocket_conf(toggle=True),
            borderwidth=0
        )

        update_websocket_conf()

        # SAVE OPTIONS
        self.conf_save = tk.Button(self.root, text='SAVE & RESTART', command=lambda:conf_save() ,font=("Lucida Console", 10))

        def changeConfigVisibility():
            global show_config

            # flip
            show_config = 0 if show_config else 1
            updateConfigVisibility()

        def updateConfigVisibility():
            global show_config

            if show_config:
                # mostrarlo
                self.conf_move.place(x=310, y=18, width=160, height=25)

                cb_counter = 0
                for (label, cb) in self.config_checkboxes:
                    label.place(x=314, y=44 + cb_counter * 20)
                    cb.place(x=310, y=44 + cb_counter * 20)
                    cb_counter += 1

                self.conf_color_label.place(x=311, y=42 + cb_counter * 20)
                self.conf_color_btn.place(x=336, y=44 + cb_counter * 20, width=120, height=23)
                cb_counter += 1

                #self.conf_websocket_label.place(x=314, y=44 + cb_counter * 20)
                #self.conf_websocket_cbtn.place(x=310, y=44 + cb_counter * 20)
                #cb_counter += 1

                #host_entry_width = 150
                #self.conf_websocket_host_entry.place(x=330, y=44 + cb_counter * 20, height=28, width=host_entry_width)
                #self.conf_websocket_port_entry.place(x=330 + host_entry_width, y=44 + cb_counter * 20, height=28, width=40)
                #cb_counter += 1

                self.conf_save.place(x=320, y=54 + cb_counter * 20, width=120, height=27)
                cb_counter += 1
            else:
                # ocultarlo
                self.conf_move.place_forget()

                for (label, cb) in self.config_checkboxes:
                    label.place_forget()
                    cb.place_forget()

                self.conf_color_label.place_forget()
                self.conf_color_btn.place_forget()

                self.conf_websocket_label.place_forget()
                self.conf_websocket_cbtn.place_forget()

                self.conf_websocket_host_entry.place_forget()
                self.conf_websocket_port_entry.place_forget()

                self.conf_save.place_forget()

        self.conf = tk.Button(self.root, text='CONFIG', command=lambda:changeConfigVisibility(), font=("Lucida Console", '7'))
        self.conf.place(x=259, y=44, width=45, height=15)

        self.t_3_6 = tk.Button(self.root, text='RESET', command=lambda:self.reset(),font=("Lucida Console", 9))
        self.t_3_6.place(x=259, y=60, width=45, height=36)

        updateConfigVisibility()

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
        self.t_6 = tk.Button(self.root, textvariable=self.status, command=lambda:self.joinRace(),font=("Lucida Console", 10))
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

        self.websocket_race_status = StringVar(self.root, "Not connected")
        self.websocket_race_status_label = tk.Label(self.root, textvariable=self.websocket_race_status,
                                                        justify=tk.LEFT, fg=self.fg.get(), bg=self.bg.get(),
                                                        font=("Lucida Console", 10), wraplength=165)

        #self.t_8 = tk.Label(self.root, text="""------""", justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_9 = tk.Label(self.root, textvariable=self.race_status, justify = tk.CENTER, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))
        self.t_10 = tk.Label(self.root, textvariable=self.ranking, justify = tk.LEFT, padx = 20,fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 10))

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

               # if use_websocket:
                self.websocket_race_status_label.place(x=20, y=148)

                #if not use_websocket:
                #self.t_8.place(x=0, y=150)
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

                self.websocket_race_status_label.place_forget()

                #self.t_8.place_forget()
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
        #self.websocket_countdown_watcher()
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

        self.time = tk.Label(self.root, textvariable=self.localcountdown, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console", 60, "bold"))
        self.time.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.toggleTrans()
        self.checkCountdowntxt()
        self.setOnTopfullscreen()

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
            self.time.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.root.configure(bg=self.color_trans_bg)
        else:
            self.root.overrideredirect(0)
            self.time.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
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

        self.timer = 0

        self.root = Tk()
        self.root.call('wm', 'attributes', '.', '-topmost', '1')

        self.color_trans_fg= "white"
        self.color_trans_bg= "#666666"
        self.color_normal_fg= "black"
        self.color_normal_bg= "#666666"

        self.timerStr = StringVar(self.root)
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
                                bg='#666666')
        self.outer_drifting_box = self.canvas.create_rectangle(1,1,499,219, outline="white", width="1")

        self.time = tk.Label(self.root, textvariable=self.localcountdown, justify = tk.CENTER, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Lucida Console",17))

        #self.time.place(x=0, y=0)
        self.btn = tk.Button(self.root, textvariable=self.timerStr , padx= 20,font=("Lucida Console", 10),command=lambda:self.hide())
        self.time.pack(expand=True, padx=2)
        

        self.btn.pack(pady= 10)

        self.canvas.place(x = 0, y = 0)

        self.toggleTrans()
        self.hide()
        self.setOnTopfullscreen()
        self.tictac()
        #self.checkCountdowntxt() 

    def toggleTrans(self):
        if (self.move):
            self.root.overrideredirect(1)
            self.time.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.btn.configure(fg=self.color_trans_fg, bg="#222")
            self.root.configure(bg=self.color_trans_bg)
        else:
            self.root.overrideredirect(0)
            self.time.configure(fg=self.color_trans_fg, bg=self.color_trans_bg)
            self.btn.configure(fg=self.color_normal_fg, bg=self.color_normal_bg)
            self.root.configure(bg=self.color_normal_bg)
            
        self.move = not self.move

    def hide(self):
        self.root.withdraw()
    
    def show(self):
        self.timer = 8
        self.root.update()
        self.root.deiconify()

    def write(self,msg):
        self.localcountdown.set(msg)
        self.show()
        self.root.lift()
        #self.root.after(5000, self.hide)

    def tictac(self):
        self.timer = max(0, self.timer - 1)
        self.timerStr.set("Ok (" + str(self.timer) + ")")
        if (self.timer == 0):
            self.hide()

        self.root.after(1000, self.tictac)

class TrackManiaHud():

    def setOnTopfullscreen(self):
        self.root.attributes('-topmost', 1)
        self.root.after(500, self.setOnTopfullscreen)

    def __init__(self):
        
        global countdowntxt
        global velocity
        global total_timer
        global lap_timer

        self.move = True

        self.timer = 0

        self.root = Tk()
        self.root.call('wm', 'attributes', '.', '-topmost', '1')

        self.color_trans_fg= "white"
        self.color_trans_bg= "#666666"
        self.color_normal_fg= "black"
        self.color_normal_bg= "#666666"

        self.timerStr = StringVar(self.root)
        self.fg = StringVar(self.root)
        self.bg = StringVar(self.root)
        self.fg.set(self.color_normal_fg)
        self.bg.set(self.color_normal_bg)

        windowWidth = root.winfo_screenwidth()
        windowHeight = root.winfo_screenheight()
        positionRight = 0
        positionDown = 0
        self.root.title("Trackmanía hud")
        self.root.geometry("{}x{}+{}+{}".format(windowWidth, windowHeight, positionRight, positionDown)) #Whatever size

        self.root.wm_attributes("-transparentcolor", "#666666")
        self.root.configure(bg='#666666')
        
        self.localcountdown = tk.StringVar(self.root,"")

        self.time = tk.Label(self.root, textvariable=self.localcountdown, justify = tk.CENTER, padx = 20, fg = self.fg.get(), bg=self.bg.get(), font=("Digital-7 Mono",40))

        self.time.place(x=windowWidth/2-127, y=windowHeight-180)
        #self.time.pack(expand=True, padx=2)

        self.toggleTrans()
        self.hide()
        self.setOnTopfullscreen()
        self.tictac()
        #self.checkCountdowntxt()  y

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

    def hide(self):
        self.root.withdraw()
    
    def show(self):
        self.timer = 8
        self.root.update()
        self.root.deiconify()

    def write(self,msg):
        return 
        self.localcountdown.set(msg)
        self.show()
        self.root.lift()
        #self.root.after(5000, self.hide)

    def tictac(self):
        #self.timer = max(0, self.timer - 1)
        #self.timerStr.set("Ok (" + str(self.timer) + ")")

        self.root.after(1000, self.tictac)


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

    tmhud = TrackManiaHud()
    tmhud.write("")

    if show_checkpoints_window:
        racer = Racer()
        countdownWidget = Countdown()
        message = Message()
        
        #check for updates
        try:
            headers = {
                'Origin': 'null',
                'Referer': 'null'
            }

            
            response = requests.get('https://www.beetlerank.com/api/info', headers)
        
            #"Welcome:\nNew event MMO B&T will start\non October 5th\nvisit beetlerank.com\nfor more details"
            if len(response.text):
                message.write(response.text)

        except:
            print("NO CONNECTION TO BEETLERANK.COM")

    
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
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
import glob
import pandas as pd

import random

import paho.mqtt.client as mqtt #import the client1
import time
from datetime import datetime

import threading
import queue


import PySide2
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl

import sys
from opensimplex import OpenSimplex
from pyqtgraph import Vector
from pynput import keyboard



try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # if your windows version >= 8.1
except:
    ctypes.windll.user32.SetProcessDPIAware() # win 8.0 or less 


np.seterr(divide='ignore', invalid='ignore')


fAvatarPosition = [57.30902862548828, 21.493343353271484, 49.639732360839844]
fAvatarFront = [-0.6651103496551514, 0.0, 0.7467450499534607]
fAvatarTop = [0.0, 0.0, 0.0]
fCameraPosition = [61.54618453979492, 26.199399948120117, 43.35494613647461]
fCameraFront = [-0.6211158633232117, -0.35765624046325684, 0.6973500847816467]

fov_var = 89.7
elevation_var = 63
distance_var = 1

timer = 0
guildhall_name = ""
checkpoint = 0
filename_timer = 99999
ghost_number = 1
forceFile = False

splitTime = 1  #check time diff each 1 secs

order = 0



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

class Ghost3d(object):
    def on_press(self,key):
        global filename_timer
        global fAvatarPosition
        global fCameraFront
        global order

        def unit_vector(a):
            return a/ np.linalg.norm(a)

        def angle_between(v1, v2):
            arg1 = np.cross(v1, v2)
            arg2 = np.dot(v1, v2)
            angle = np.arctan2(arg1, arg2)
            return np.degrees(angle)

        try:

            if key.char == "5":

                c = np.array([fCameraFront[0], fCameraFront[2]])
                uaf = unit_vector(c)
                map_angle = float(angle_between([0 , 1], uaf))+180

                order = 0
                self.best_file = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\maps\\NEW.csv"
                writer = open(self.best_file, 'w',newline='', encoding='utf-8')
                writer.seek(0,2)
                writer.writelines( (',').join(["STEP","STEPNAME","X","Y","Z","RADIUS","ANGLE"]))
                writer.writelines("\r")
                writer.writelines( (',').join([str(order),"start",str(fAvatarPosition[0]),str(fAvatarPosition[1]),str(fAvatarPosition[2]),"15",str(map_angle)]))
                order = order + 1
                writer.close()
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999
            
            if key.char == "6":
                c = np.array([fCameraFront[0], fCameraFront[2]])
                uaf = unit_vector(c)
                map_angle = float(angle_between([0 , 1], uaf))+180
                writer = open(self.best_file, 'a',newline='', encoding='utf-8')
                writer.seek(0,2)
                writer.writelines("\r")
                writer.writelines( (',').join([str(order),"*",str(fAvatarPosition[0]),str(fAvatarPosition[1]),str(fAvatarPosition[2]),"15",str(map_angle)]))
                order = order + 1
                writer.close()
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999
                

            if key.char == "7":
                c = np.array([fCameraFront[0], fCameraFront[2]])
                uaf = unit_vector(c)
                map_angle = float(angle_between([0 , 1], uaf))+180
                writer = open(self.best_file, 'a',newline='', encoding='utf-8')
                writer.seek(0,2)
                writer.writelines("\r")
                writer.writelines( (',').join([str(order),"end",str(fAvatarPosition[0]),str(fAvatarPosition[1]),str(fAvatarPosition[2]),"15",str(map_angle)]))
                writer.close()
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999

            if key.char == "1":
                order = 0
                map_angle = -1
                self.best_file = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\maps\\NEW.csv"
                writer = open(self.best_file, 'w',newline='', encoding='utf-8')
                writer.seek(0,2)
                writer.writelines( (',').join(["STEP","STEPNAME","X","Y","Z","RADIUS","ANGLE"]))
                writer.writelines("\r")
                writer.writelines( (',').join([str(order),"start",str(fAvatarPosition[0]),str(fAvatarPosition[1]),str(fAvatarPosition[2]),"15",str(map_angle)]))
                order = order + 1
                writer.close()
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999
               
            if key.char == "2":
                map_angle = -1
                writer = open(self.best_file, 'a',newline='', encoding='utf-8')
                writer.seek(0,2)
                writer.writelines("\r")
                writer.writelines( (',').join([str(order),"*",str(fAvatarPosition[0]),str(fAvatarPosition[1]),str(fAvatarPosition[2]),"15",str(map_angle)]))
                order = order + 1
                writer.close()
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999
                

            if key.char == "3":
                map_angle = -1
                writer = open(self.best_file, 'a',newline='', encoding='utf-8')
                writer.seek(0,2)
                writer.writelines("\r")
                writer.writelines( (',').join([str(order),"end",str(fAvatarPosition[0]),str(fAvatarPosition[1]),str(fAvatarPosition[2]),"15",str(map_angle)]))
                writer.close()
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999


            if key.char == "4":
                map_angle = -1
                writer = open(self.best_file, 'a',newline='', encoding='utf-8')
                writer.seek(0,2)
                writer.writelines("\r")
                writer.writelines( (',').join([str(-1), "reset", str(fAvatarPosition[0]),str(fAvatarPosition[1]),str(fAvatarPosition[2]),"5",str(map_angle)]))
                writer.close()
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999


            if key.char == "t":
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    
                    print("delete", first_value)
                    self.w.clear()

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999
        except AttributeError:
            None
        
    def on_release(self,key):
        try:
            if key.char == "y":
                print('RELOAD CHECKPOINTS')
        except AttributeError:
            None

    def searchGhost(self):
        
        global guildhall_name
        global forceFile
        global checkpoint

        self.best_file = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\maps\\NEW.csv"

        print("-----------------------------------------------")
        print("- CREATED NEW FILE ON maps/NEW.CSV ")
        print("- KEYBINDS TO CREATE CHECKPOINTS ")
        print("- KEY 1 - clean the file and place start ")
        print("- KEY 2 - place normal checkpoint ")
        print("- KEY 3 - place end checkpoint ")
        print("- KEY 4 - place a position to reset the timer ")
        print("-----------------------------------------------")
        print("- (NEW) key 5 - clean the file and place start vertically")
        print("- (NEW) key 6 - place a normal checkpoint vertically")
        print("- (NEW) key 7 - place end checkpoint vertically")
        print("-----------------------------------------------")
        print("- CHECKPOINTS FILE" , self.best_file )
        print("-----------------------------------------------")
        print("- ONCE YOU FINISH YOUR CREATION, RENAME -")
        print("- THE FILE TO SOMETHING DIFERENT THAT NEW.CSV -")
        print("-----------------------------------------------")

        self.df = pd.DataFrame()
        file_df = pd.read_csv(self.best_file)
        file_df['file_name'] = self.best_file
        self.df = self.df.append(file_df)


    def __init__(self):

        global fAvatarPosition
        global guildhall_name
        global timer

        self.file_ready = False

        """
        Initialize the graphics window and mesh
        """

        self.root = Tk()
        self.root.title("Checkpoints")

        # setup the view window
        self.app = QtGui.QApplication(sys.argv)

        #time viewer
        self.wtime = QtGui.QWidget()
        self.wtime.setStyleSheet("background-color: black;")


        layout = QtGui.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        self.wtime.setLayout(layout)

        #self.label = QtGui.QLabel(str(timer))
        #self.label.setFont(QtGui.QFont('Lucida Console', 20))
        #self.label.setStyleSheet("background: rgba(255, 0, 0, 0);");
        
        #my_font = QFont("Times New Roman", 12)
        #my_button.setFont(my_font)

        #self.wtime.layout().addWidget(self.label)


        


        windowWidth = self.root.winfo_screenwidth()
        windowHeight = 50
        self.wtime.setGeometry(0, 0, windowWidth, windowHeight)
        self.wtime.setWindowTitle('GhooOOoosst debug')

        self.wtime.setWindowFlags(self.wtime.windowFlags() |
            QtCore.Qt.WindowTransparentForInput |
            QtCore.Qt.X11BypassWindowManagerHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint)
        self.wtime.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.wtime.setWindowOpacity(0.7)
        #self.wtime.setBackgroundColor(0,0,0,1)

        def empty(ev):
            return None
        self.wtime.mouseMoveEvent = empty
        self.wtime.wheelEvent = empty
        
        self.wtime.show()
        
        #3d viewer
        self.w = gl.GLViewWidget()


        windowWidth = self.root.winfo_screenwidth()
        windowHeight = self.root.winfo_screenheight() -50
        print("Screen resolution:",windowHeight+10,"x",windowWidth)
        self.w.setGeometry(0, 50, windowWidth, windowHeight)
        self.w.setWindowTitle('GhooOOoosst')
        self.w.setCameraPosition(distance=100, elevation=8, azimuth=42)
        self.w.opts['center'] = Vector(0,0,0)

        self.w.setWindowFlags(self.w.windowFlags() |
            QtCore.Qt.WindowTransparentForInput |
            QtCore.Qt.X11BypassWindowManagerHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint)
        self.w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.w.setWindowOpacity(0.9)
        self.w.setBackgroundColor(0,0,0,1)

        def empty(ev):
            return None
        self.w.mouseMoveEvent = empty
        self.w.wheelEvent = empty
        
        self.w.show()

        self.best_file = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\maps\\NEW.csv"
        writer = open(self.best_file, 'w',newline='', encoding='utf-8')
        writer.seek(0,2)
        writer.writelines( (',').join(["STEP","STEPNAME","X","Y","Z","RADIUS"]))
        writer.close()


        self.searchGhost()
        self.file_ready = True


        self.balls = {}
        self.last_balls_positions = {}

        listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        listener.start()

        self.animation()


    def updateCam(self):
        
        global fAvatarPosition
        global fAvatarFront
        global fCameraFront
        global timer
        global ghost_number
        global filename_timer

        global fov_var
        global elevation_var
        global distance_var

        ml.read()

        if ml.data.uiVersion == 0:
            return

        fov = json.loads(ml.data.identity)["fov"]
        fAvatarPosition = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[1],ml.data.fAvatarPosition[2]]
        fAvatarFront = [ml.data.fAvatarFront[0],ml.data.fAvatarFront[1],ml.data.fAvatarFront[2]]
        fAvatarTop = [ml.data.fAvatarTop[0],ml.data.fAvatarTop[1],ml.data.fAvatarTop[2]]

        fCameraPosition = [ml.data.fCameraPosition[0],ml.data.fCameraPosition[1],ml.data.fCameraPosition[2]]
        fCameraFront = [ml.data.fCameraFront[0],ml.data.fCameraFront[1],ml.data.fCameraFront[2]]
        fCameraTop = [ml.data.fCameraTop[0],ml.data.fCameraTop[1],ml.data.fCameraTop[2]]

        #UPDATE CAMERA POSITION
        angle2 = math.atan2(fCameraFront[2], fCameraFront[0])  # ALWAYS USE THIS
        angle2 *= 180 / math.pi
        if angle2 < 0: angle2 += 360
        self.w.opts['elevation'] = -(float(fCameraFront[1]) * elevation_var) 
        self.w.opts['distance'] = distance.euclidean(fAvatarPosition, fCameraPosition) * distance_var
        self.w.opts['azimuth'] = angle2 + 180
        self.w.opts['center'] = Vector(fAvatarPosition[0],fAvatarPosition[2],fAvatarPosition[1]-2)
        self.w.opts['fov'] = fov * fov_var
        self.w.pan(0,0,3)

        #self.loop = self.root.after(1, self.updateCam)

    def update(self):

        global timer
        global ghost_number
        global filename_timer
        global splitTime
        global fAvatarPosition
        global checkpoint


        file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "checkpoint.txt")
        filedata = file.read()
        if filedata == '': 
            return 

        checkpoint = int(filedata)

        self.w.clear()

        #self.label.setText('<font color=\"white\">' + str(checkpoint) + '</font>')

        #for x in self.all_files[-ghost_number:]:
        if hasattr(self, 'df') and self.file_ready == True:
            #dibujo los checkpoints < checkpoint en gris
            data = self.df[(self.df['STEP'] < checkpoint) ]
            if len(data) > 0:

                points = list(self.df[(self.df['STEP'] < checkpoint) ].values)
                
                for p in points:

                    step = p[0]
                    stepname = p[1]
                    posx = p[2]
                    posy = p[3]
                    posz = p[4]
                    radius = p[5]
                    angle = p[6]
                    file = random.random()

                    step_index = str(file)
                 
                    if stepname == "reset":
                        speedcolor = [255, 182, 24]
                        radius = 5 * 0.666
                    else:
                        speedcolor = [40, 40, 40]
                        radius = 15 * 0.666

                    #print(vel, speedcolor)
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[radius,radius], length=0.4)

                    colors = np.ones((self.md.faceCount(), 4), dtype=float)
                    colors[::1,0] = 1
                    colors[::1,1] = 0
                    colors[::1,2] = 0
                    colors[:,1] = np.linspace(0, 1, colors.shape[0])
                    #self.md.setFaceColors(colors)

                    #if not file in self.balls:
                    self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=False, drawFaces=True, glOptions='additive', shader='shaded', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
                    self.balls[step_index].scale(1.5, 1.5, 1.5)
                    self.w.addItem(self.balls[step_index])

                    if self.last_balls_positions.get(step_index):
                        last_pos = self.last_balls_positions.get(step_index)
                    else: 
                        last_pos = [0,0,0]

                    transx = float(posx) - float(last_pos[0])
                    transy = float(posz) - float(last_pos[1])
                    transz = float(posy) - float(last_pos[2])

                    if (angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-angle,1,0,0,True)
                    self.balls[step_index].translate(transx,transy,transz)
                    

                    self.balls[step_index].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

                    self.last_balls_positions[step_index] = [posx,posz,posy]

            
            #dibujo el checkpoint = checkpoint en azul
            data = self.df[(self.df['STEP'] == checkpoint) ]
            if len(data) > 0:

                points = list(self.df[(self.df['STEP'] == checkpoint) ].values)
                for p in points:

                    step = p[0]
                    stepname = p[1]
                    posx = p[2]
                    posy = p[3]
                    posz = p[4]
                    radius = p[5]
                    angle = p[6]
                    file = random.random()

                    step_index = str(file)

                    speedcolor = [0, 0, 200]

                    #print(vel, speedcolor)
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[radius * 0.666,15 * 0.666], length=0.4)

                    colors = np.ones((self.md.faceCount(), 4), dtype=float)
                    colors[::1,0] = 1
                    colors[::1,1] = 0
                    colors[::1,2] = 0
                    colors[:,1] = np.linspace(0, 1, colors.shape[0])
                    #self.md.setFaceColors(colors)

                    #if not file in self.balls:
                    self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=False, drawFaces=True, glOptions='additive', shader='shaded', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
                    self.balls[step_index].scale(1.5, 1.5, 1.5)
                    self.w.addItem(self.balls[step_index])

                    if self.last_balls_positions.get(step_index):
                        last_pos = self.last_balls_positions.get(step_index)
                    else: 
                        last_pos = [0,0,0]

                    transx = float(posx) - float(last_pos[0])
                    transy = float(posz) - float(last_pos[1])
                    transz = float(posy) - float(last_pos[2])

                    #self.balls[step_index].resetTransform()
                    if (angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-angle,1,0,0,True)
                    self.balls[step_index].translate(transx,transy,transz)
                    
                    self.balls[step_index].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

                    self.last_balls_positions[step_index] = [posx,posz,posy]

            
            #dibujo los siguientes > checkpoint en blancos
            data = self.df[(self.df['STEP'] > checkpoint) ]
            if len(data) > 0:
                points = list(self.df[(self.df['STEP'] > checkpoint) ].values)
                
                for p in points:

                    step = p[0]
                    stepname = p[1]
                    posx = p[2]
                    posy = p[3]
                    posz = p[4]
                    radius = p[5]
                    angle = p[6]
                    file = random.random()

                    step_index = str(file)

                    speedcolor = [200, 200, 200]

                    #print(vel, speedcolor)
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[15 * 0.666,15 * 0.666], length=0.4)

                    colors = np.ones((self.md.faceCount(), 4), dtype=float)
                    colors[::1,0] = 1
                    colors[::1,1] = 0
                    colors[::1,2] = 0
                    colors[:,1] = np.linspace(0, 1, colors.shape[0])
                    #self.md.setFaceColors(colors)

                    #if not file in self.balls:
                    self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=False, drawFaces=True, glOptions='additive', shader='shaded', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
                    self.balls[step_index].scale(1.5, 1.5, 1.5)
                    self.w.addItem(self.balls[step_index])

                    if self.last_balls_positions.get(step_index):
                        last_pos = self.last_balls_positions.get(step_index)
                    else: 
                        last_pos = [0,0,0]

                    transx = float(posx) - float(last_pos[0])
                    transy = float(posz) - float(last_pos[1])
                    transz = float(posy) - float(last_pos[2])

                    if (angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-angle,1,0,0,True)
                    self.balls[step_index].translate(transx,transy,transz)
                    
                    self.balls[step_index].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

                    self.last_balls_positions[step_index] = [posx,posz,posy]

                            
  
    def start(self):
        """
        get the graphics window open and setup
        """
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

    def animation(self):
        """
        calls the update method to run in a loop
        """
        timer = QtCore.QTimer()
        timer.timeout.connect(self.updateCam)
        timer.start(0.5)

        timer2 = QtCore.QTimer()
        timer2.timeout.connect(self.update)
        timer2.start(1)

        self.start()


if __name__ == '__main__':

    #root.mainloop() 

    root = tk.Tk()
    root.call('wm', 'attributes', '.', '-topmost', '1')

    windowWidth = root.winfo_screenwidth()
    windowHeight = root.winfo_screenheight() - 10
    root.title("Move Speedometer windows")
    root.geometry("300x50+{}+{}".format(int(windowWidth/2) -150, 0)) #Whatever vel
    root.overrideredirect(0) #Remove border
    root.wm_attributes("-transparentcolor", "#666666")
    root.attributes('-topmost', 1)
    root.configure(bg='#666666')

    ml = MumbleLink()
    
    t = Ghost3d()
    root.mainloop()


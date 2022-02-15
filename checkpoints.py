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

import shlex, subprocess


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
cup_name = ""
checkpoint = 0
filename_timer = 99999
ghost_number = 1
forceFile = False

splitTime = 1  #check time diff each 1 secs



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
        try:
            if key.char == "y":
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    for element in balls:
                        self.w.removeItem(element)
                    
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
        global cup_name
        global forceFile
        global checkpoint

        forceFile = False
        #force file to the one you drag an drop on the script
        if len(sys.argv) > 1:
            forceFile = True
            file_ = sys.argv[1]

        if forceFile:
            self.df = pd.DataFrame()
            file_df = pd.read_csv(file_)
            file_df['file_name'] = file_
            self.df = self.df.append(file_df)
            min_time = 99999
            self.best_file = file_
            print("-----------------------------------------------")
            print("- FORCE LOAD LOG FILE" , self.best_file )
            print("- PRESS KEY 'T' TO REPLAY THAT FILE")
            print("- PRESS KEY 'Y' TO STOP THE GHOST AT START")
            print("-----------------------------------------------")

        else:

             #actualizamos el nombre del guildhall o mapa
            file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "guildhall.txt", "r", encoding="utf-8")
            guildhall_name = file.read()

            file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "cup.txt")
            cup_name = file.read()

            if guildhall_name != "None, im free!":

                file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "checkpoint.txt")
                checkpoint = int(file.read())

                self.best_file = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\maps\\" + cup_name + "\\" + guildhall_name + ".csv"

                print("-----------------------------------------------")
                print("- THE SELECTED CUP IS " , cup_name )
                print("- THE SELECTED MAP IS " , guildhall_name )
                print("- CHECKPOINTS FILE" , self.best_file )
                print("-----------------------------------------------")

                self.df = pd.DataFrame()
                file_df = pd.read_csv(self.best_file, encoding = 'utf8')
                file_df['file_name'] = self.best_file
                self.df = self.df.append(file_df)
                min_time = 99999
                print("-----------------------------------------------")
                print("- FILE LOADED" , self.best_file )
                print("-----------------------------------------------")


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


        if self.balls != {}:
            balls = self.balls.values()
            value_iterator = iter(balls)
            for element in balls:
                try:
                    self.w.removeItem(element)
                except:
                    print("")
            
        self.balls = {}
        self.last_balls_positions = {}

        #self.label.setText('<font color=\"white\">' + str(checkpoint) + '</font>')

        #for x in self.all_files[-ghost_number:]:
        if hasattr(self, 'df') and self.file_ready == True:
            
            data = self.df[(self.df['STEP'] == -1) & (self.df['file_name'] == self.best_file)]
            
            if len(data) > 0:

                points = list(self.df[(self.df['STEP'] == -1) & (self.df['file_name'] == self.best_file)].values)
                
                for p in points:

                    if len(p) == 6:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = 5 #default size for reset
                    else:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = p[5] * 0.666
                        angle = p[6]

                    if (len(p) == 7):
                        angle = -1
                    

                    step_index = str(step)
                
                    speedcolor = [255, 182, 24, 255]
                    #radius = 5
                    #print(vel, speedcolor)
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[radius,radius], length=0.4)

                    if not step_index in self.balls:
                        self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, glOptions='additive', shader='balloon', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
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
                    #self.balls[step_index].rotate(1,0,0,1,True)
                    if ('angle' in locals() and angle and angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-int(float(angle)),1,0,0,True)
                    self.balls[step_index].translate(transx,transy,transz)
                    self.balls[step_index].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

                    self.last_balls_positions[step_index] = [posx,posz,posy]
            #dibujo los checkpoints < checkpoint en gris

            """
            data = self.df[(self.df['STEP'] < checkpoint) & (self.df['STEP'] > -1) & (self.df['file_name'] == self.best_file)]
            if len(data) > 0:

                points = list(self.df[(self.df['STEP'] < checkpoint) & (self.df['STEP'] > -1) & (self.df['file_name'] == self.best_file)].values)
                
                for p in points:

                    if len(p) == 6:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = 10 #default size for reset
                    else:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = p[5] * 0.666
                        angle = p[6]

                    if (len(p) == 7):
                        angle = -1
                    


                    step_index = str(step)
                 
                    speedcolor = [40, 40, 40, 0]
                    #radius = 10

                    #print(vel, speedcolor)
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[radius,radius], length=0.4)

                    if not step_index in self.balls:
                        self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=False, glOptions='additive', shader='balloon', color=(speedcolor[0], speedcolor[1], speedcolor[2],0))
                        self.balls[step_index].scale(1.5, 1.5, 1.5)
                        self.w.addItem(self.balls[step_index])

                    if self.last_balls_positions.get(step_index):
                        last_pos = self.last_balls_positions.get(step_index)
                    else: 
                        last_pos = [0,0,0]

                    transx = float(posx) - float(last_pos[0])
                    transy = float(posz) - float(last_pos[1])
                    transz = float(posy) - float(last_pos[2])

                    if ('angle' in locals() and angle and angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-int(float(angle)),1,0,0,True)
                    self.balls[step_index].translate(transx,transy,transz)
                    self.balls[step_index].setColor((speedcolor[0], speedcolor[1], speedcolor[2], 0))

                    self.last_balls_positions[step_index] = [posx,posz,posy]
            """

            #dibujo el checkpoint = checkpoint en azul
            data = self.df[(self.df['STEP'] == checkpoint) & (self.df['file_name'] == self.best_file)]
            if len(data) > 0:

                points = list(self.df[(self.df['STEP'] == checkpoint) & (self.df['file_name'] == self.best_file)].values)
                
                subindex = 0
                for p in points:

                    if len(p) == 6:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = 10 #default size for reset
                    else:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = p[5] * 0.666
                        angle = p[6]

                    if (len(p) == 7):
                        angle = -1

                    


                    step_index = str(step) + "_" + str(subindex)
                    subindex = subindex + 1

                    speedcolor = [44, 44, 255]

                    #radius = 10

                    #print(vel, speedcolor)
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[radius,radius], length=0.4)

                    if not step_index in self.balls:
                        self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, glOptions='additive', shader='balloon', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
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
                    #self.balls[step_index].rotate(1,0,0,1,True)
                    if ('angle' in locals() and angle and angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-int(float(angle)),1,0,0,True)
                    self.balls[step_index].translate(transx,transy,transz)
                    

                    
                    self.balls[step_index].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

                    self.last_balls_positions[step_index] = [posx,posz,posy]

            #dibujo los siguientes > checkpoint en blancos
            data = self.df[(self.df['STEP'] == checkpoint + 1) & (self.df['file_name'] == self.best_file)]
            if len(data) > 0:

                points = list(self.df[(self.df['STEP'] == checkpoint + 1 ) & (self.df['file_name'] == self.best_file)].values)
                subindex = 0
                for p in points:

                    if len(p) == 6:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = 10 #default size for reset
                    else:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = p[5] * 0.666
                        angle = p[6]

                    if (len(p) == 7):
                        angle = -1
                    


                    step_index = str(step) + "_" + str(subindex)
                    subindex = subindex + 1

                    speedcolor = [44, 218, 235]

                    #print(vel, speedcolor)

                    #radius = 10
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[radius,radius], length=0.4)

                    if not step_index in self.balls:
                        self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, glOptions='additive', shader='balloon', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
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
                    #self.balls[step_index].rotate(1,0,0,1,True)
                    if ('angle' in locals() and angle and angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-int(float(angle)),1,0,0,True)
                    self.balls[step_index].translate(transx,transy,transz)
                    

                    
                    self.balls[step_index].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

                    self.last_balls_positions[step_index] = [posx,posz,posy]

                        #dibujo los siguientes > checkpoint en blancos
            
            data = self.df[(self.df['STEP'] == checkpoint + 2) & (self.df['file_name'] == self.best_file)]
            if len(data) > 0:

                points = list(self.df[(self.df['STEP'] == checkpoint + 2 ) & (self.df['file_name'] == self.best_file)].values)
                subindex = 0
                for p in points:

                    if len(p) == 6:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = 10 #default size for reset
                    else:
                        step = p[0]
                        stepname = p[1]
                        posx = p[2]
                        posy = p[3]
                        posz = p[4]
                        radius = p[5] * 0.666
                        angle = p[6]

                    if (len(p) == 7):
                        angle = -1
                    


                    step_index = str(step) + "_" + str(subindex)
                    subindex = subindex + 1

                    speedcolor = [200, 200, 200]

                    #print(vel, speedcolor)

                    #radius = 10
                    
                    self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[radius,radius], length=0.4)

                    if not step_index in self.balls:
                        self.balls[step_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, glOptions='additive', shader='balloon', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
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
                    #self.balls[step_index].rotate(1,0,0,1,True)
                    if ('angle' in locals() and angle and angle != -1):
                        self.balls[step_index].rotate(90,0,1,0,True)
                        self.balls[step_index].rotate(90-int(float(angle)),1,0,0,True)
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


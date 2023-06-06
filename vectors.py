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

import paho.mqtt.client as mqtt #import the client1



try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # if your windows version >= 8.1
except:
    ctypes.windll.user32.SetProcessDPIAware() # win 8.0 or less 


np.seterr(divide='ignore', invalid='ignore')


fAvatarPosition = [57.30902862548828, 21.493343353271484, 49.639732360839844]
lastfAvatarPosition = [57.30902862548828, 21.493343353271484, 49.639732360839844]
fAvatarFront = [-0.6651103496551514, 0.0, 0.7467450499534607]
fAvatarTop = [0.0, 0.0, 0.0]
fCameraPosition = [61.54618453979492, 26.199399948120117, 43.35494613647461]
fCameraFront = [-0.6211158633232117, -0.35765624046325684, 0.6973500847816467]

angle_camera = 0
angle_beetle = 0
angle_speed = 0

fov_var = 89.7
elevation_var = 63
distance_var = 1

timer = 0
guildhall_name = ""
cup_name = ""
checkpoint = 0
ghost_number = 1
forceFile = False

splitTime = 1  #check time diff each 1 secs

client = ""
session_id = ""
tag_username = ""
tag_colddown = 0

tagged = "U Killer U"

posx = 0
posy = 0
posz = 0

tag_game_subscription = ''


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

    def __init__(self):

        global fAvatarPosition
        global guildhall_name
        global timer


        """
        Initialize the graphics window and mesh
        """

        self.root = Tk()
        self.root.title("Vectors")

        # setup the view window
        self.app = QtGui.QApplication(sys.argv)

        #time viewer
        self.wtime = QtGui.QWidget()
        self.wtime.setStyleSheet("background-color: black;")


        layout = QtGui.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        self.wtime.setLayout(layout)

        windowWidth = self.root.winfo_screenwidth()
        windowHeight = 50
        self.wtime.setGeometry(0, 0, windowWidth, windowHeight)
        self.wtime.setWindowTitle('Vectors debug')

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
        self.w.setWindowTitle('Vectors')
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
        self.balls = {}
        self.animation()

    def updateCam(self):
        
        global fAvatarPosition
        global lastfAvatarPosition
        global timer
        global ghost_number

        global fov_var
        global elevation_var
        global distance_var

        global posx
        global posy
        global posz

        global angle_camera
        global angle_beetle
        global angle_speed

        global tag_username

        ml.read()

        if ml.data.uiVersion == 0:
            return

        tag_username = json.loads(ml.data.identity).get("name")
        fov = json.loads(ml.data.identity)["fov"]
        fAvatarPosition = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[1],ml.data.fAvatarPosition[2]]
        fAvatarFront = [ml.data.fAvatarFront[0],ml.data.fAvatarFront[1],ml.data.fAvatarFront[2]]
        fAvatarTop = [ml.data.fAvatarTop[0],ml.data.fAvatarTop[1],ml.data.fAvatarTop[2]]

        posx = fAvatarPosition[0]
        posy = fAvatarPosition[1] -3
        posz = fAvatarPosition[2] 

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

        #GET PLAYER ANGLES
        def unit_vector(a):
            return a/ np.linalg.norm(a)

        def angle_between(v1, v2):
            arg1 = np.cross(v1, v2)
            arg2 = np.dot(v1, v2)
            angle = np.arctan2(arg1, arg2)
            return np.degrees(angle)

        a = np.array([fAvatarPosition[0] - lastfAvatarPosition[0], fAvatarPosition[2] - lastfAvatarPosition[2]])
        b = np.array([ml.data.fCameraFront[0], ml.data.fCameraFront[2]])
        c = np.array([ml.data.fAvatarFront[0], ml.data.fAvatarFront[2]])    

        if fAvatarPosition[0] - lastfAvatarPosition[0] == 0 or fAvatarPosition[2] - lastfAvatarPosition[2] == 0:
            stop = 1
        else:
            # si nos estamos moviendo, calculamos el vector unitario del vector velocidad
            uv = unit_vector(a)
            # calculamos el vector unitario del angulo de camara
            uc = unit_vector(b)
            # calculamos el vector unitario del angulo de beetle (avatarFront)
            uaf = unit_vector(c)
            global map_angle
            map_angle = float(angle_between([0 , 1], uc))+180
            
            angle_camera = float(angle_between(uc, uv))
            angle_beetle = float(angle_between(uaf, uv))
            
            angle_speed = map_angle

            
        lastfAvatarPosition = fAvatarPosition


    def viewAngleTick(self,angle,index):
        global fAvatarPosition

        global posx
        global posy
        global posz

        global angle_speed
        
        graycolor = [222,222,222,255]
        
        self.md = gl.MeshData.cylinder(rows=1, cols=4, radius=[0.07,0.01], length=10)

        if not index in self.balls:
            self.balls[index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, shader='balloon', color=(QtGui.QColor(graycolor[0], graycolor[1], graycolor[2])))
            self.balls[index].scale(1.5, 1.5, 1.5)
            self.w.addItem(self.balls[index])

        self.balls[index].resetTransform()

        temp_speed_angle = 90-int(float(angle_speed + angle_camera)) + angle
    
        self.balls[index].rotate(90,0,1,0,True)
        self.balls[index].rotate(temp_speed_angle,1,0,0,True)

        self.balls[index].translate(posx,posz,posy)
        self.balls[index].setColor(QtGui.QColor(graycolor[0], graycolor[1], graycolor[2]))


    def update(self):
        global timer
        global ghost_number
        global splitTime
        global fAvatarPosition
        global checkpoint

        global posx
        global posy
        global posz

        global angle_camera
        global angle_beetle
        global angle_speed

        area_index = 1 #area
        beetle_index = 2 
        camera_index = 3
        speed_index = 4

        graycolor = [255,100,0,255]
        cameracolor = [111,111,111,255]
        beetlecolor = [100, 255, 100, 255]
        speedcolor = [222, 222, 222, 255]




        self.viewAngleTick(90,5)
        self.viewAngleTick(-90,6)
        self.viewAngleTick(45,7)
        self.viewAngleTick(-45,8)
        self.viewAngleTick(0,9)

        # speed
        self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[0.29,0], length=10)

        if not camera_index in self.balls:
            self.balls[camera_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, shader='balloon', color=(QtGui.QColor(cameracolor[0], cameracolor[1], cameracolor[2])))
            self.balls[camera_index].scale(1.5, 1.5, 1.5)
            self.w.addItem(self.balls[camera_index])

        self.balls[camera_index].resetTransform()

        self.balls[camera_index].rotate(90,0,1,0,True)
        self.balls[camera_index].rotate(90-int(float(angle_speed)),1,0,0,True)

        self.balls[camera_index].translate(posx,posz,posy)
        self.balls[camera_index].setColor(QtGui.QColor(cameracolor[0], cameracolor[1], cameracolor[2]))

        # camera
        self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[0.29,0], length=10)

        if not speed_index in self.balls:
            self.balls[speed_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, shader='balloon', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
            self.balls[speed_index].scale(1.5, 1.5, 1.5)
            self.w.addItem(self.balls[speed_index])

        self.balls[speed_index].resetTransform()

        self.balls[speed_index].rotate(90,0,1,0,True)
        self.balls[speed_index].rotate(90-int(float(angle_speed + angle_camera)),1,0,0,True)

        self.balls[speed_index].translate(posx,posz,posy)
        self.balls[speed_index].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

        # beetle

        beetleRED = 0
        beetleGREEN = 0
        beetleBLUE = 0

        angle_beetle_abs = abs(angle_beetle)


        # 0     255,0,0
        if angle_beetle_abs > 0 and angle_beetle_abs <=30:
            beetleRED = 255
            beetleGREEN = abs(angle_beetle_abs * 255 / 30)
        # 30    255,255,0
        if angle_beetle_abs > 30 and angle_beetle_abs <=45:
            beetleGREEN = 255
            beetleRED = abs(((angle_beetle_abs - 30) * 255 / 15 ) - 255)
        # 45    0,255,0
        if angle_beetle_abs > 45 and angle_beetle_abs <=60:
            beetleGREEN = 255
            beetleRED = abs(((angle_beetle_abs - 45) * 255 / 15 ))
        # 60    255,255,0
        if angle_beetle_abs > 60 and angle_beetle_abs <= 90:
            beetleRED = 255
            beetleGREEN = abs(((angle_beetle_abs - 60) * 255 / 30) - 255)
        # 90    255,0,0
        if angle_beetle_abs > 90:
            beetleRED = 255
            beetleGREEN = 0

        beetle_final_angle = int(float((angle_speed + angle_camera) - angle_beetle))

        self.md = gl.MeshData.cylinder(rows=1, cols=40, radius=[0.3,0], length=10)

        if not beetle_index in self.balls:
            self.balls[beetle_index] = gl.GLMeshItem(meshdata=self.md, drawEdges=False, smooth=True, drawFaces=True, shader='balloon', color=(QtGui.QColor(beetleRED, beetleGREEN, beetleBLUE)))
            self.balls[beetle_index].scale(1.5, 1.5, 1.5)
            self.w.addItem(self.balls[beetle_index])

        self.balls[beetle_index].resetTransform()

        self.balls[beetle_index].rotate(90,0,1,0,True)
        self.balls[beetle_index].rotate(90-beetle_final_angle,1,0,0,True)

        self.balls[beetle_index].translate(posx,posz,posy)
        self.balls[beetle_index].setColor(QtGui.QColor(beetleRED, beetleGREEN, beetleBLUE))



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

    print("***************************************************")
    print("* This program display the vectors of your beetle *")
    print("***************************************************")
    print("***  COLOR ARROW  = beetle angle green with 45º red with 0 and 90  *****")
    print("***  WHITE ARROW = speed direction with marks on 45 and 90º ************")
    print("***  GRAY ARROW = camera direction  ************************************")
    print("************************************************************************")


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


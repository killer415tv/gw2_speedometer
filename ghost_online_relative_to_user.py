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

from PySide2.QtWidgets import QApplication, QDialog, QLineEdit, QPushButton, QWidget, QVBoxLayout, QLabel, QFileDialog, QCheckBox
from PySide2.QtCore import Qt

import sys
from opensimplex import OpenSimplex
from pyqtgraph import Vector
from pynput import keyboard

import io 
import requests 

# import urllib library
from urllib.request import urlopen  
from urllib.parse import quote
# import json
import json



try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # if your windows version >= 8.1
except:
    ctypes.windll.user32.SetProcessDPIAware() # win 8.0 or less 

np.seterr(divide='ignore', invalid='ignore')

fAvatarPosition = [0.0, 0.0, 0.0]
fAvatarFront =    [0.0, 0.0, 0.0]
fAvatarTop =      [0.0, 0.0, 0.0]
fCameraPosition = [0.0, 0.0, 0.0]
fCameraFront =    [0.0, 0.0, 0.0]

app = 0
map_angle = 0

fov_var = 89.7
elevation_var = 63
distance_var = 1

game_focus = 0
chosen_option = False

file_url = ""
forceFile_online = False

stop = False
timer = 0
guildhall_name = ""
cup_name = ""
check_guildhall_change = ""
filename_timer = 99999
ghost_number = 1
forceFile = False
min_time = 99999

firstTime = True
firstLoad = True

splitTime = 1  #check time diff each 1 secs

from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
FR_PRIVATE  = 0x10
FR_NOT_ENUM = 0x20

show3D = True

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

class Ghost3d():

    # EVENTS

    def read_guildhall(self):

        global guildhall_name
        global cup_name
        global check_guildhall_change

        #check the actual guildhall name from guildhall.txt
        file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "guildhall.txt", "r", encoding="utf-8")
        guildhall_name = file.read()

        #check the actual guildhall name from guildhall.txt
        file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "cup.txt")
        cup_name = file.read()
        
        if check_guildhall_change == "":
            check_guildhall_change = guildhall_name
            return False
        else:
            #print(check_guildhall_change, guildhall_name)
            if check_guildhall_change != guildhall_name:
                #print("++++++++++++ CAMBIAMOS MAPA")
                check_guildhall_change = guildhall_name
                return True
            else:
                #print("++++++++++++ MISMO MAPA")
                return False

    def on_press(self,key):
        global filename_timer
        global game_focus
        global forceFile
        global firstTime
        global stop
        global map_angle
        global show3D
        
        #if game_focus == '0':
        #    return
        try:
            if key.char.lower() == "t":
                print('START GHOST')
                filename_timer = time.perf_counter()
            if key.char.lower() == "y":
                map_change = self.read_guildhall()
                stop = True
                map_angle = 0
                self.last_map_angle = 0
                firstTime = True

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    if show3D:
                        self.w.removeItem(first_value)
                #only force search again if change map
                if not forceFile:
                    if map_change:
                        self.searchGhost(file_url)
                self.balls = {}
                self.last_balls_positions = {}

                filename_timer = 99999
                stop = False
            if key.char.lower() == "u":
                stop = True
                map_angle = 0
                self.last_map_angle = 0
                firstTime = True
                self.read_guildhall()
                
                if forceFile:
                    filename_timer = 99999
                    stop = False
                    return 
                print('SEARCH BETTER LOG')
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)
                    if show3D:
                        self.w.removeItem(first_value)
                    firstTime = True

                self.searchGhost(False)
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999
                stop = False
        except AttributeError:
            None
        
    def on_release(self,key):
        try:
            if key.char.lower() == "t":
                return
            if key.char.lower() == "y":
                return
            if key.char.lower() == "u":
                return
        except AttributeError:
            None

    # INITIALIZERS

    def searchGhost(self, forceUrl):
        
        global guildhall_name
        global cup_name
        global check_guildhall_change
        global forceFile
        global min_time
        global file_url
        global forceFile_online

        forceFile = False
        #force file to the one you drag an drop on the script
        if len(sys.argv) > 1:
            forceFile = True
            file_url = sys.argv[1]

        if forceUrl:
            if forceUrl == 'search':
                #option to search on local files
                forceFile = False
            else:
                # you selected url file
                forceFile = True
                file_url = forceUrl

        if forceFile:

            #online 
            self.df = pd.DataFrame()

            if forceFile_online:
                s=requests.get(file_url).content 
                file_df=pd.read_csv(io.StringIO(s.decode('utf-8'))) 
            else:
                #offline
                file_df = pd.read_csv(file_url)

            file_df['file_name'] = file_url
            self.df = self.df.append(file_df)
            min_time = 99999
            self.best_file = file_url


            min_time = list(self.df.values[-1])[6]

            print("-----------------------------------------------")
            print("- FORCE LOAD LOG FILE" , self.best_file )
            print("- TIME",datetime.strftime(datetime.utcfromtimestamp(min_time), "%M:%S:%f")[:-3] )
            print("-----------------------------------------------")
            print("- PRESS KEY 'T' TO REPLAY THAT FILE")
            print("- PRESS KEY 'Y' TO STOP THE GHOST AT START")
            print("-----------------------------------------------")

        else:

            
            
            print("-----------------------------------------------")
            print("---------- ZONE:", guildhall_name, "------------")
                    
            #get all available csv logfiles from that guildhall
            path = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\logs\\"
            self.all_files = glob.glob(os.path.join(path, guildhall_name+"_log*.csv"))

            #get the checkpoint file for that guildhall
            
            if cup_name == "OWN MAPS FOLDER":
                self.checkpoints_file = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\maps\\" + cup_name + "\\" + guildhall_name + ".csv"
            else:
                self.checkpoints_file = requests.utils.requote_uri('https://www.beetlerank.com/uploads/checkpoints/'+guildhall_name+'.csv')

            checkpoints_list_temp = pd.DataFrame()
            file_df = pd.read_csv(self.checkpoints_file)
            checkpoints_list = checkpoints_list_temp.append(file_df)

            print("-----------------------------------------------")
            print("- THE SELECTED MAP IS" , guildhall_name )
            print("- CHECKPOINTS FILE" , self.checkpoints_file )

            if len(self.all_files) > 0:
                
                self.df = pd.DataFrame()
                for file_ in self.all_files:
                    file_df = pd.read_csv(file_)
                    file_df['file_name'] = file_
                    self.df = self.df.append(file_df)

                #aquí tenemos que quedarnos solo con el mejor tiempo

                min_time = 99999
                self.best_file = ''

                for x in self.all_files:
                    data = self.df[(self.df['file_name'] == x)]
                    #print(list(data.values[-1]))
                    last_elem = [list(data.values[-1])[0],list(data.values[-1])[1],list(data.values[-1])[2]]
                    #print(last_elem)
                    try:
                        finish_logfile_position = (ctypes.c_float * len(last_elem))(*last_elem)
                        finish_logfile_position = [finish_logfile_position[0],finish_logfile_position[1],finish_logfile_position[2]]

                        #CHECK POSITION TO RESTART THE GHOST

                        finish_checkpoint_position = [checkpoints_list.loc[checkpoints_list['STEPNAME'] == 'end'].X.values,checkpoints_list.loc[checkpoints_list['STEPNAME'] == 'end'].Y.values,checkpoints_list.loc[checkpoints_list['STEPNAME'] == 'end'].Z.values]

                        try:
                            # if distance between last position on log and last checkpoint is lower than 40, then , its a valid logfile
                            # to add more verification , we could check if all checkpoints has at least 1 point with that distance,
                            # but probably its going to be slower
                            if distance.euclidean(finish_checkpoint_position, finish_logfile_position) < 40:
                                # valid logfile
                                time = data['TIME'].values[-1]
                                if time < min_time:
                                    min_time = time
                                    self.best_file = x
                        except:
                            print("File",x,"is corrupted, you can delete it 1")

                    except:
                        print("File",x,"is corrupted, you can delete it 2")

                if min_time == 99999:
                    print("-----------------------------------------------")
                    print("- NO TIMES YET, YOU NEED TO RACE WITH SPEEDOMETER TO CREATE NEW ONE" )
                    print("-----------------------------------------------")
                else:
                    print("-----------------------------------------------")
                    print("- AUTO SEARCH MODE LAUNCHED ")
                    print("- YOUR BEST TIME IS" , datetime.strftime(datetime.utcfromtimestamp(min_time), "%M:%S:%f")[:-3] )
                    print("- LOG FILE" , self.best_file )
                    print("- PRESS KEY 'T' TO REPLAY THAT FILE")
                    print("- PRESS KEY 'Y' TO RECALCULATE THE BEST FILE")
                    print("- PRESS KEY 'U' SEARCH YOUR BEST LOG ON /LOGS FOLDER")
                    print("- Speedometer program will automatically press 't' and 'y' each time you start or finish a timed track")
                    print("- You will have to press 'u' manually if want to update the best log found")
                    print("-----------------------------------------------")

                    self.df = pd.DataFrame()
                    file_df = pd.read_csv(self.best_file)
                    file_df['file_name'] = self.best_file
                    self.df = self.df.append(file_df)
                    print("-----------------------------------------------")
                    print("- LOAD LOG FILE" , self.best_file )
                    print("-----------------------------------------------")
                        
            else:
                print("- THERE IS NO LOG FILES YET")
                print("- YOU NEED TO RACE WITH SPEEDOMETER TO CREATE NEW ONE" )
                print("-----------------------------------------------")
                exit()

    # SECTIONS
    """
    def fov_var_add_clicked(self):
        global fov_var
        fov_var = fov_var + 1
        print("fov_var_add_clicked to ", fov_var)

    def elevation_var_add_clicked(self):
        global elevation_var
        elevation_var = elevation_var + 1
        print("elevation_var_add_clicked to ", elevation_var)

    def distance_var_add_clicked(self):
        global distance_var
        distance_var = distance_var + 0.1
        print("distance_var_add_clicked to ", distance_var)

    def fov_var_less_clicked(self):
        global fov_var
        fov_var = fov_var - 1
        print("fov_var_less_clicked to ", fov_var)

    def elevation_var_less_clicked(self):
        global elevation_var
        elevation_var = elevation_var - 1
        print("elevation_var_less_clicked to ", elevation_var)

    def distance_var_less_clicked(self):
        global distance_var
        distance_var = distance_var - 0.1
        print("distance_var_less_clicked to ", distance_var)    
    """
    

    def create_top_section(self):
        self.wtime = QtGui.QWidget()
        self.wtime.setStyleSheet("background-color: black;")

        layout = QtGui.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignCenter)
        self.wtime.setLayout(layout)

        self.label = QtGui.QLabel(str(timer))
        self.label.setFont(QtGui.QFont("Digital-7 Mono", 25))
        self.label.setStyleSheet("background: rgba(255, 0, 0, 0);");

        self.labelspeed = QtGui.QLabel("Initial Speed: 000")
        self.labelspeed.setFont(QtGui.QFont("Digital-7 Mono", 23))
        self.labelspeed.setStyleSheet("background: rgba(255, 0, 0, 0);");
        
        
        """ # add buttons

        self.buttonfov_var_add = QtGui.QPushButton(self.wtime)
        self.buttonfov_var_add.setText("+ more")

        self.buttonelevation_var_add = QtGui.QPushButton(self.wtime)
        self.buttonelevation_var_add.setText("+ more")

        self.buttondistance_var_add = QtGui.QPushButton(self.wtime)
        self.buttondistance_var_add.setText("+ more")

        self.buttonfov_var_add.clicked.connect(self.fov_var_add_clicked)
        self.buttonelevation_var_add.clicked.connect(self.elevation_var_add_clicked)
        self.buttondistance_var_add.clicked.connect(self.distance_var_add_clicked)
        
        # less buttons

        self.buttonfov_var_less = QtGui.QPushButton(self.wtime)
        self.buttonfov_var_less.setText("+ more")

        self.buttonelevation_var_less = QtGui.QPushButton(self.wtime)
        self.buttonelevation_var_less.setText("+ more")

        self.buttondistance_var_less = QtGui.QPushButton(self.wtime)
        self.buttondistance_var_less.setText("+ more")

        self.buttonfov_var_less.clicked.connect(self.fov_var_less_clicked)
        self.buttonelevation_var_less.clicked.connect(self.elevation_var_less_clicked)
        self.buttondistance_var_less.clicked.connect(self.distance_var_less_clicked)

        self.wtime.layout().addWidget(self.buttonfov_var_add)
        self.wtime.layout().addWidget(self.buttonelevation_var_add)
        self.wtime.layout().addWidget(self.buttondistance_var_add)
        self.wtime.layout().addWidget(self.buttonfov_var_less)
        self.wtime.layout().addWidget(self.buttonelevation_var_less)
        self.wtime.layout().addWidget(self.buttondistance_var_less)
        """

        self.wtime.layout().addWidget(self.label)
        self.wtime.layout().addWidget(self.labelspeed)
        

        # window size is 1920 x 50
        windowWidth = self.size.width() 
        windowHeight = 50 

        self.wtime.setGeometry(0, 0, self.size.width(), windowHeight)
        self.wtime.setWindowTitle('Time difference section')

        self.wtime.setWindowFlags(self.wtime.windowFlags() |
            QtCore.Qt.WindowTransparentForInput |
            QtCore.Qt.X11BypassWindowManagerHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint)
        self.wtime.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.wtime.setWindowOpacity(1)
        #self.wtime.setBackgroundColor(0,0,0,1)

        def empty(ev):
            return None
        self.wtime.mouseMoveEvent = empty
        self.wtime.wheelEvent = empty
        
        self.wtime.show()

    def create_3d_viewer(self):
        self.w = gl.GLViewWidget()

        windowWidth = self.size.width()
        windowHeight = self.size.height() -50

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

    # UPDATERS

    def updateCam(self):
        
        global fAvatarPosition
        global timer
        global ghost_number
        global filename_timer

        global fov_var
        global elevation_var
        global distance_var

        global game_focus

        global stop
        
        if stop:
            return

        ml.read()

        if ml.data.uiVersion == 0:
            return
        game_status = '{0:08b}'.format(ml.context.uiState)
        game_focus = game_status[4]

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
        global min_time
        global map_angle

        global firstTime
        global firstLoad
        global show3D
        global game_focus

        global stop
        
        if stop:
            return

        if show3D == False:
            ml.read()

            if ml.data.uiVersion == 0:
                return
            game_status = '{0:08b}'.format(ml.context.uiState)
            game_focus = game_status[4]

            fAvatarPosition = [ml.data.fAvatarPosition[0],ml.data.fAvatarPosition[1],ml.data.fAvatarPosition[2]]


        timer = time.perf_counter() - filename_timer

        #here we are going to check the time diff
        if hasattr(self, 'df') and self.file_ready == True:

            xy = ['X', 'Y', 'Z']
            self.df[xy] = self.df[xy].astype(float)
            distance_array = np.sum((self.df[xy].values - fAvatarPosition)**2, axis=1)

            ghostTimer = float(self.df["TIME"].values[distance_array.argmin()])
            ownTimer = timer
            diffTimer = ownTimer - ghostTimer

            if diffTimer < -1000:
                diffTimer = 0
            
            # el tiempo datetime.strftime(datetime.utcfromtimestamp(timer), "%M:%S:%f")[:-3]

            #print( str(round(diffTimer)) + " segs" )

            if timer < 0:
                self.label.setText('<font color=\"white\">Ghost is waiting to start - ' + datetime.strftime(datetime.utcfromtimestamp(min_time), "%M:%S:%f")[:-3] +'</font>')
            else:
                if diffTimer > 0:
                    self.label.setText('<font color=\"red\">+' + datetime.strftime(datetime.utcfromtimestamp(abs(diffTimer)), "%M:%S:%f")[:-3] + '</font>')
                else:
                    self.label.setText('<font color=\"Lime\">-' + datetime.strftime(datetime.utcfromtimestamp(abs(diffTimer)), "%M:%S:%f")[:-3] +  '</font>')
                
        #draw polygon
        if hasattr(self, 'df') and self.file_ready == True:
            data = self.df[(self.df['TIME'] > timer) & (self.df['file_name'] == self.best_file)]

            ##print("duro ",len(data))
            if len(data) > 0:

                userpos = list(self.df[(self.df['TIME'] > timer) & (self.df['file_name'] == self.best_file)].values[0])
                
                posx = userpos[0]
                posy = userpos[1]
                posz = userpos[2]
                vel = userpos[3]
                # logs sin map_angle
                if len(userpos) == 9:
                    file = userpos[8]
                    map_angle = 0
                # logs con map_angle
                else:
                    file = userpos[9]
                    if firstLoad:
                        map_angle = 0
                        firstLoad = False
                    else:
                        map_angle = userpos[8]
                

                strvel = str(vel)
                strvel = strvel.zfill(3)
                if self.labelspeed:
                    if (timer < 0):
                        self.labelspeed.setText('<font color=\"white\">Initial Speed : ' + str(strvel) +'</font>')
                    else:
                        self.labelspeed.setText('<font color=\"white\">Speed : ' + str(strvel) +'</font>')


                if show3D:
                    #self.createMarker(posx+900,posy+500,posz,vel,30,datetime.fromtimestamp(int(file.split("\\")[4][:-4].split("_")[2].split(".")[0])))

                    #dibujamos un marcador por lectura , hay que cambiar para no crear muchos
                    speedcolor = [120, 152, 255]

                    if vel > 65 :
                        speedcolor = [201, 112, 204]
                    if vel > 80 :
                        speedcolor = [255, 138, 54]
                    if vel > 99 :
                        speedcolor = [235, 55, 52]

                    #print(vel, speedcolor)
                
                    # self.md = gl.MeshData.sphere(rows=2, cols=4, radius=1.0)
                    self.md = gl.MeshData.cylinder(rows=2, cols=20, radius=[1.5, 1.5], length=1)

                    colors = np.ones((self.md.faceCount(), 4), dtype=float)
                    colors[::1,0] = 1
                    colors[::1,1] = 0
                    colors[::1,2] = 0
                    colors[:,1] = np.linspace(0, 1, colors.shape[0])
                    #self.md.setFaceColors(colors)
                    if not file in self.balls:
                        self.balls[file] = gl.GLMeshItem(meshdata=self.md, smooth=True, drawFaces=True, glOptions='additive', shader='shaded', color=(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2])))
                        self.balls[file].scale(1.5, 1.5, 1.5)
                        self.w.addItem(self.balls[file])

                    if self.last_balls_positions.get(file):
                        last_pos = self.last_balls_positions.get(file)
                    else: 
                        last_pos = [0,0,0]

                    if firstTime:
                        map_angle = 0

                    transx = float(posx) - float(last_pos[0])
                    transy = float(posz) - float(last_pos[1])
                    transz = float(posy) - float(last_pos[2])
                    rotate = float(map_angle) - float(self.last_map_angle)
                    
                    # rotation = float()
                    if firstTime:
                        self.balls[file].resetTransform()
                        self.balls[file].rotate(90,0,1,0,True)
                        self.balls[file].rotate(map_angle,1,0,0,True)
                        #self.balls[file].rotate(-53,1,0,0,True)
                        firstTime = False

                    #self.balls[file].resetTransform()
                    self.balls[file].rotate(-float(rotate),1,0,0,True)

                    self.balls[file].translate(transx,transy,transz)

                    self.balls[file].setColor(QtGui.QColor(speedcolor[0], speedcolor[1], speedcolor[2]))

                    self.last_balls_positions[file] = [posx,posz,posy]
                    self.last_map_angle = map_angle

        #self.loop = self.root.after(1, self.update)

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
        global show3D

        if show3D:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self.updateCam)
            self.timer.start(0.5)

        self.timer2 = QtCore.QTimer()
        self.timer2.timeout.connect(self.update)
        self.timer2.start(1)

        self.start()
    
    def launchGhost(self,option):
        #load ghost
        self.searchGhost(option)
        self.file_ready = True

        self.balls = {}
        self.last_balls_positions = {}
        self.last_map_angle = 0

        listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        listener.start()
        
        self.animation()

    def __init__(self,option):

        # options
        # False - nothing selected close all
        # url - force file
        # 'search' - force auto search on local

        if option == False:
            exit()

        global app
        global fAvatarPosition
        global guildhall_name
        global timer
        global min_time
        global show3D

        self.file_ready = False

        # setup the view window
        ##app = QtGui.QApplication(sys.argv)

        # get resolution values to create full screen application
        screen = app.primaryScreen()
        self.size = screen.size()
        print('Size: %d x %d' % (self.size.width(), self.size.height()))

        #create top section to view the time diff
        self.create_top_section()
        
        #3d viewer
        if show3D:
            self.create_3d_viewer()

        #launch the ghost system
        self.launchGhost(option)
        
class Menu():

    def rank1_click(self):
        global chosen_option
        global forceFile_online

        forceFile_online = True
        chosen_option = self.rank1_file
        self.window.close()
        return 

    def rank2_click(self):
        global chosen_option
        global forceFile_online

        forceFile_online = True
        chosen_option = self.rank2_file
        self.window.close()
        return 

    def rank3_click(self):
        global chosen_option
        global forceFile_online

        forceFile_online = True
        chosen_option = self.rank3_file
        self.window.close()
        return 

    def rank4_click(self):
        global chosen_option
        global forceFile_online

        forceFile_online = False
        chosen_option = 'search'
        self.window.close()
        return 
    
    def open(self):
        global chosen_option
        global forceFile_online

        forceFile_online = False
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        chosen_option, _ = QFileDialog.getOpenFileName(
            None,
            "QFileDialog.getOpenFileName()",
            "",
            "All Files (*);;Python Files (*.py)",
            options=options,
        )
        self.window.close()
        return

    def medalPos(self,pos):
        if (pos == 1):
            return "🥇"
        if (pos == 2):
            return "🥈"
        if (pos == 3):
            return "🥉"
        if (pos > 3):
            return "#"+str(pos)
        

    def readAPI(self,map,user):
        url = "https://www.beetlerank.com/api/top3/"+quote(map)+"/"+quote(user)
  
        print(url)

        # store the response of URL
        response = requests.get(url, verify=True)
        
        # storing the JSON response 
        # from url in data
        data_json = json.loads(response.text)
        
        # print the json response
        if (user):
            return data_json['you']
        else:
            return data_json['ranking']



    def checkBoxChange(self, state):
        global show3D

        if state == Qt.Checked:
            show3D = True
        else:
            show3D = False

    def __init__(self):
        
        global app 
        global guildhall_name
        global cup_name
        global chosen_option 

        ml.read()
        if (ml.data.identity):
            user = json.loads(ml.data.identity)["name"]
        else:
            user = ""

        #check the actual guildhall name from guildhall.txt
        file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "guildhall.txt", "r", encoding="utf-8")
        guildhall_name = file.read()

        file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "cup.txt")
        cup_name = file.read()

        self.window = QWidget()
        self.window.setWindowTitle("Ghost Loader v0.1")

        layout = QVBoxLayout()
        
        layout.addWidget(QLabel('Ghost loader'))
        layout.addWidget(QLabel('Map: '+ guildhall_name))

        ranking = self.readAPI(guildhall_name, user)


        if len(ranking)>0:
            self.rank1_label = 'Online: ' +  self.medalPos(ranking[0]['pos']) + " :" + ranking[0]['time'] + " by " +ranking[0]['name']

        if len(ranking)>1:
            self.rank2_label = 'Online: ' +  self.medalPos(ranking[1]['pos']) + " :" + ranking[1]['time'] + " by " +ranking[1]['name']

        if len(ranking)>2:
            self.rank3_label = 'Online: ' +  self.medalPos(ranking[2]['pos']) + " :" + ranking[2]['time'] + " by " +ranking[2]['name']


        if len(ranking)>0:
            self.rank1_file = ranking[0]['file']

        if len(ranking)>1:
            self.rank2_file = ranking[1]['file']
        
        if len(ranking)>2:
            self.rank3_file = ranking[2]['file']


        if len(ranking)>0:
            rank1 = QPushButton(self.rank1_label)
            rank1.setStyleSheet("text-align:left;")

        if len(ranking)>1:
            rank2 = QPushButton(self.rank2_label)
            rank2.setStyleSheet("text-align:left;")
        
        if len(ranking)>2:
            rank3 = QPushButton(self.rank3_label)
            rank3.setStyleSheet("text-align:left;")
        
        
        rank4 = QPushButton('Offline: Search best on /logs folder')
        rank4.setStyleSheet("text-align:left;")
        rank5 = QPushButton('Offline: Load manually a log file')
        rank5.setStyleSheet("text-align:left;")

        if len(ranking)>0:
            rank1.clicked.connect(self.rank1_click)
        if len(ranking)>1:
            rank2.clicked.connect(self.rank2_click)
        if len(ranking)>2:
            rank3.clicked.connect(self.rank3_click)

        rank4.clicked.connect(self.rank4_click)
        rank5.clicked.connect(self.open)

        layout.addWidget(QLabel('Select a rival'))
        
        if len(ranking)>0:
            layout.addWidget(rank1)
        if len(ranking)>1:
            layout.addWidget(rank2)
        if len(ranking)>2:
            layout.addWidget(rank3)
        
        layout.addWidget(rank4)
        layout.addWidget(rank5)

        check = QCheckBox("Show 3D ghost")
        check.stateChanged.connect(self.checkBoxChange)
        check.toggle()
 
        layout.addWidget(check)



        
        self.window.setLayout(layout)
        self.window.show()
        app.exec_()
        

if __name__ == '__main__':

    ml = MumbleLink()
    app = QApplication(sys.argv)
    a = Menu() 

    t = Ghost3d(chosen_option)


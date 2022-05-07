import tkinter as tk
from tkinter import *
import ctypes
import datetime
from scipy.spatial import distance

import os
import json
import glob
import pandas as pd
import hashlib

import random

import paho.mqtt.client as mqtt  # import the client1
import time
from datetime import datetime

import numpy as np
import PySide2
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl

import sys
from opensimplex import OpenSimplex
from pyqtgraph import Vector
from pynput import keyboard

from mumblelink import MumbleLink
from websocket_util import WebsocketClient

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # if your windows version >= 8.1
except:
    ctypes.windll.user32.SetProcessDPIAware()  # win 8.0 or less

np.seterr(divide='ignore', invalid='ignore')

fAvatarPosition = [57.30902862548828, 21.493343353271484, 49.639732360839844]
fAvatarFront = [-0.6651103496551514, 0.0, 0.7467450499534607]
fAvatarTop = [0.0, 0.0, 0.0]
fCameraPosition = [61.54618453979492, 26.199399948120117, 43.35494613647461]
fCameraFront = [-0.6211158633232117, -0.35765624046325684, 0.6973500847816467]

timer = 0
guildhall_name = ""
cup_name = ""
filename_timer = 99999
ghost_number = 1
forceFile = False

client = ""
tag_game_subscription = ''

HOSTNAME = "localhost"
PORT = 30200


class Ghost3d(object):
    ws_client = None;

    def on_press(self, key):
        global filename_timer
        try:
            if key.char == "t":
                filename_timer = time.perf_counter()
            if key.char == "y":
                self.file_ready = False

                if self.balls != {}:
                    balls = self.balls.values()
                    value_iterator = iter(balls)
                    first_value = next(value_iterator)

                    self.w.removeItem(first_value)

                self.searchGhost()
                self.balls = {}
                self.last_balls_positions = {}
                self.file_ready = True
                filename_timer = 99999
                self.drawMap()
        except AttributeError:
            pass

    def on_release(self, key):
        try:
            if key.char == "t":
                # print('GHOST RESET')
                return
            if key.char == "y":
                print('SEARCH BEST LOG FILE')
        except AttributeError:
            pass

    def searchGhost(self):

        global guildhall_name
        global cup_name
        global forceFile

        forceFile = False
        # force file to the one you drag an drop on the script
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
            print("- FORCE LOAD MAP LOG FILE", self.best_file)
            print("-----------------------------------------------")

        else:

            # actualizamos el nombre del guildhall o mapa
            file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "guildhall.txt", "r", encoding="utf-8")
            guildhall_name = file.read()

            file = open(os.path.dirname(os.path.abspath(sys.argv[0])) + "\\" + "cup.txt")
            cup_name = file.read()

            print("-----------------------------------------------")
            print("---------- ZONE:", guildhall_name, "------------")

            # obtener los ficheros de replay
            path = os.path.dirname(os.path.abspath(sys.argv[0])) + "\\logs\\"
            self.all_files = glob.glob(os.path.join(path, guildhall_name + "_log*.csv"))

            self.checkpoints_file = os.path.dirname(
                os.path.abspath(sys.argv[0])) + "\\maps\\" + cup_name + "\\" + guildhall_name + ".csv"

            print("-----------------------------------------------")
            print("- THE SELECTED CUP IS", cup_name)
            print("- THE SELECTED MAP IS", guildhall_name)
            print("- CHECKPOINTS FILE", self.checkpoints_file)

            checkpoints_list = pd.DataFrame()
            file_df = pd.read_csv(self.checkpoints_file)
            checkpoints_list = checkpoints_list.append(file_df)

            if len(self.all_files) > 0:
                self.df = pd.DataFrame()
                for file_ in self.all_files:
                    file_df = pd.read_csv(file_)
                    file_df['file_name'] = file_
                    self.df = self.df.append(file_df)

                # aquí tenemos que quedarnos solo con el mejor tiempo

                min_time = 99999
                self.best_file = ''

                for x in self.all_files:
                    data = self.df[(self.df['file_name'] == x)]
                    print("x", x, len(data.values))
                    if len(data.values) == 0:
                        continue
                    # print(list(data.values[-1]))
                    last_elem = [list(data.values[-1])[0], list(data.values[-1])[1], list(data.values[-1])[2]]
                    # print(last_elem)
                    try:
                        last_elem_array = (ctypes.c_float * len(last_elem))(*last_elem)

                        # CHECK POSITION TO RESTART THE GHOST
                        endpoint = [checkpoints_list.loc[checkpoints_list['STEPNAME'] == 'end'].X.values,
                                    checkpoints_list.loc[checkpoints_list['STEPNAME'] == 'end'].Y.values,
                                    checkpoints_list.loc[checkpoints_list['STEPNAME'] == 'end'].Z.values]

                        try:
                            if distance.euclidean(endpoint, last_elem_array) < 20:
                                # candidato a válido
                                time = list(data.values[-1])[6]
                                if time < min_time:
                                    min_time = time
                                    self.best_file = x
                        except:
                            print("File", x, "is corrupted, you can delete it")

                    except:
                        print("File", x, "is corrupted, you can delete it")

                if min_time == 99999:
                    print("-----------------------------------------------")
                    print("- NO TIMES YET, YOU NEED TO RACE WITH SPEEDOMETER TO CREATE NEW ONE")
                    print("-----------------------------------------------")
                else:
                    print("-----------------------------------------------")
                    print("- YOUR BEST TIME IS",
                          datetime.strftime(datetime.utcfromtimestamp(min_time), "%M:%S:%f")[:-3])
                    print("- LOG FILE FOR DRAW MAP ", self.best_file)
                    print("- PRESS KEY 'Y' TO RECALCULATE THE BEST FILE")
                    print(
                        "- Speedometer program will automatically press 'y' each time you start or finish a timed track")
                    print("-----------------------------------------------")

                    self.df = pd.DataFrame()
                    file_df = pd.read_csv(self.best_file)
                    file_df['file_name'] = self.best_file
                    self.df = self.df.append(file_df)
                    min_time = 99999
                    print("-----------------------------------------------")
                    print("- LOAD LOG FILE", self.best_file)
                    print("-----------------------------------------------")
            else:
                print("THERE IS NO LOG FILES YET")

    def on_message(self, client_, userdata, message):
        global client
        # print("message received " ,json.loads(str(message.payload.decode("utf-8"))))
        received = json.loads(str(message.payload.decode("utf-8")))

        # {"option": "position", "x": ml.data.fAvatarPosition[0], "y": ml.data.fAvatarPosition[1], "z": ml.data.fAvatarPosition[2], "user": racer.username.get(), "map": guildhall_name.get(), "color": player_color}

        # receive player position
        if received.get('option') == 'position':
            self.paintPlayer(received.get('user'), received.get('x'), received.get('z'), received.get('color'))

    def joinRace(self):
        # global client
        # global session_id
        # global tag_game_subscription
        #
        # # ignore old channel
        # if client != "":
        #     client.on_message = self.ignore_message
        #
        #     # subscribición al topico
        # broker_address = "www.beetlerank.com"
        # # print("creating new instance")
        # client = mqtt.Client(client_id=str(random.random()))  # create new instance
        # # client.tls_set("./chain.pem")
        # # client.tls_insecure_set(True)
        # client.on_message = self.on_message  # attach function to callback
        # # print("connecting to broker")
        # client.connect(broker_address)  # connect to broker
        # client.loop_start()  # start the loop
        # # print("Subscribing to topic","/gw2/speedometer/race/" + str(self.session_id.get()))
        # client.subscribe("/gw2/speedometer/race/" + tag_game_subscription)
        # print("+ connected")
        # # self.thread_queue.put('Waiting for start.')

        ws_client = WebsocketClient(HOSTNAME, PORT)

    def __init__(self):

        global fAvatarPosition
        global guildhall_name

        self.file_ready = False

        self.root = Tk()
        self.root.title("Map")
        self.root.geometry("1000x1000+20+20")  # Whatever size
        self.root.overrideredirect(1)  # Remove border
        self.root.wm_attributes("-transparentcolor", "#666666")
        self.root.attributes('-topmost', 1)
        self.root.configure(bg='#f0f0f0')
        """
        def disable_event():
            self.toggleTrans()
        self.root.protocol("WM_DELETE_WINDOW", disable_event)
        
        """
        self.canvas = tk.Canvas(self.root, width=800, height=800,
                                borderwidth=0, highlightthickness=0,
                                bg='#666666')

        self.canvas.pack(side='top', fill='both', expand='yes')

        self.searchGhost()
        self.file_ready = True

        self.balls = {}
        self.last_balls_positions = {}

        listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        listener.start()

        ml.read()

        self.drawMap()
        # self.updateOwnPosition()
        self.joinRace()

        self.root.mainloop()

    def drawMap(self):

        global guildhall_name
        timer = time.perf_counter() - filename_timer

        # for x in self.all_files[-ghost_number:]:
        if hasattr(self, 'df') and self.file_ready == True:
            data = self.df[self.df['file_name'] == self.best_file]

            self.color1 = "#6f6f6f"
            self.color2 = "#cfcfcf"

            self.scale = 1 / 2
            if guildhall_name == "VAW Left path":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "VAW Right path":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "GeeK":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "INDI":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "GWTC":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "RACE Downhill":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "RACE Full Mountain Run":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "RACE Hillclimb":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "EQE":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "SoTD":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "UAoT":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "LRS":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "HUR":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"
            elif guildhall_name == "TYRIA INF.LEAP":
                self.scale = 1 / 2.5
                self.color1 = "#714227"
                self.color2 = "#af4242"
            elif guildhall_name == "TYRIA DIESSA PLATEAU":
                self.scale = 1 / 3
                self.color1 = "#716127"
                self.color2 = "#af8942"
            elif guildhall_name == "TYRIA SNOWDEN DRIFTS":
                self.scale = 1 / 1.2
                self.color1 = "#6f6f6f"
                self.color2 = "#cfcfcf"
            elif guildhall_name == "TYRIA GENDARRAN":
                self.scale = 1 / 3
                self.color1 = "#27716d"
                self.color2 = "#3db4a2"
            elif guildhall_name == "TYRIA BRISBAN WILD.":
                self.scale = 1 / 4
                self.color1 = "#4c7127"
                self.color2 = "#7db43d"
            elif guildhall_name == "TYRIA GROTHMAR VALLEY":
                self.scale = 1 / 3
                self.color1 = "#714227"
                self.color2 = "#c85224"
            elif guildhall_name == "OLLO Akina":
                self.scale = 1 / 2
                self.color1 = "#714227"
                self.color2 = "#936140"

            ##print("duro ",len(data))
            if len(data) > 0:

                track = data
                # print("track", track)
                # dibujar mapa
                points = []

                self.minX = data['X'].min()
                self.maxX = data['X'].max()
                self.minZ = data['Z'].min()

                for index, row in data.iterrows():
                    # print(float(row['X']) + float(minX))
                    points.append((float(-row['X']) + abs(float(self.maxX)) + 90) * self.scale)
                    points.append((float(row['Z']) + abs(float(self.minZ)) + 90) * self.scale)

                self.canvas.delete("map2")
                self.canvas.create_line(points, width=7, fill=self.color1, tags="map2")
                self.canvas.delete("map")
                self.canvas.create_line(points, width=4, fill=self.color2, tags="map")

                points = [
                    (float(-data['X'].values[-1]) + abs(float(self.maxX)) + 90) * self.scale,
                    (float(data['Z'].values[-1]) + abs(float(self.minZ)) + 90) * self.scale,
                    (float(-data['X'].values[0]) + abs(float(self.maxX)) + 90) * self.scale,
                    (float(data['Z'].values[0]) + abs(float(self.minZ)) + 90) * self.scale]

                self.canvas.delete("startline")
                self.canvas.create_line(points, width=4, fill=self.color2, tags="startline", dash="4")

    def updateOwnPosition(self):

        global fAvatarPosition
        global timer
        global filename_timer

        ml.read()

        if ml.data.uiVersion == 0:
            return

        fAvatarPosition2D = [ml.data.fAvatarPosition[0], ml.data.fAvatarPosition[2]]

        if not hasattr(self, 'maxX'):
            return

        self.paintPlayer(json.loads(ml.data.identity)["name"], fAvatarPosition2D[0], fAvatarPosition2D[1])

        self.root.after(50, self.updateOwnPosition)

    def paintPlayer(self, name, x, y, color):

        if not hasattr(self, 'maxX'):
            return

        if not hasattr(ml, 'data'):
            return

        positionX = (-x + abs(float(self.maxX)) + 90) * self.scale
        positionY = (y + abs(float(self.minZ)) + 90) * self.scale

        namemd5 = str(hashlib.md5(name.encode()).hexdigest())

        self.canvas.delete(namemd5 + "label")
        self.canvas.create_text(positionX + 40, positionY + 5, fill="#fff", text=name, tags=namemd5 + "label")
        self.canvas.delete(namemd5 + "marker")
        self.canvas.create_oval(positionX + 0, positionY + 0, positionX + 10, positionY + 10, outline=color, fill=color,
                                width=1, tags=namemd5 + "marker")


if __name__ == '__main__':
    print("*****************************************************************")
    print("*             REALTIME MAP - MULTIPLAYER VERSION                *")
    print("*    IMPORTANT: write your multiplayer code and press enter     *")
    print("*****************************************************************")

    tag_game_subscription = input("Type your multiplayer code:")

    print("+ code: ", tag_game_subscription, " written")
    print("+ connecting....")

    ml = MumbleLink()
    t = Ghost3d()

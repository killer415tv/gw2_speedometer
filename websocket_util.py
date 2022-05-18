import asyncio
import json
import logging

import websockets


class WebsocketClient:
    def __init__(self, hostname, port):
        self.server_url = f"ws://{hostname}:{port}"

    async def consumer_handler(self, ws, consumer):
        async for msg in ws:
            await consumer(msg)

    async def producer_handler(self, ws, producer):
        while True:
            msg = await producer()
            await ws.send(msg)

    async def combined_handler(self, ws, consumer, producer):
        await asyncio.gather(
            self.consumer_handler(ws, consumer),
            self.producer_handler(ws, producer),
        )

    async def _start(self, handler, *args, **kwargs):
        init_packet = kwargs.get("init_packet")

        async for ws in websockets.connect(self.server_url):
            try:
                if init_packet is not None:
                    await ws.send(json.dumps(init_packet))
                await handler(ws, *args)
            except websockets.ConnectionClosed:
                continue

    async def start_combined(self, consumer, producer):
        await self._start(self.combined_handler, consumer, producer)

    async def start_map(self, consumer, room):
        init_packet = {
            "type": "init",
            "client": "map",
            "room": room
        }
        await self._start(self.consumer_handler, consumer, init_packet=init_packet)

    async def start_speedometer(self, producer, room):
        init_packet = {
            "type": "init",
            "client": "speedometer",
            "room": room
        }
        await self._start(self.producer_handler, producer, init_packet=init_packet)


class WebsocketServer:
    rooms = dict()

    async def speedometer_handler(self, ws, room):
        logging.info(f"Speedometer joined [{room}]")
        if room not in self.rooms:
            self.rooms[room] = {
                "maps": set(),
                "speedometer": set()
            }
        self.rooms[room]["speedometer"].add(ws)

        try:
            async for msg in ws:
                if room in self.rooms:
                    websockets.broadcast(self.rooms[room]["maps"], msg)
        except websockets.ConnectionClosedError:
            pass

        # connection closed
        if len(self.rooms[room]["speedometer"]) > 1 or self.rooms[room]["maps"]:
            self.rooms[room]["speedometer"].remove(ws)
        else:
            del self.rooms[room]

    async def map_handler(self, ws, room):
        logging.info(f"Map joined [{room}]")

        # create room if necessary
        if room not in self.rooms:
            self.rooms[room] = {
                "maps": set(),
                "speedometer": set()
            }
        self.rooms[room]["maps"].add(ws)

        try:
            async for msg in ws:
                websockets.broadcast(self.rooms[room]["speedometer"], msg)
        except websockets.ConnectionClosedError:
            pass

        # connection closed
        if len(self.rooms[room]["maps"]) > 1 or self.rooms[room]["speedometer"]:
            self.rooms[room]["maps"].remove(ws)
        else:
            del self.rooms[room]

    async def handler(self, ws):
        logging.info(f"Connection opened: {ws.id}")

        try:
            msg = await ws.recv()
        except websockets.ConnectionClosedError:
            return

        event = json.loads(msg)

        assert event["type"] == "init"
        client = event["client"]
        room = str(event["room"])

        if client == "speedometer":
            await self.speedometer_handler(ws, room)
        elif client == "map":
            await self.map_handler(ws, room)
        else:
            return

        logging.info(f"Connection closed: {ws.id}")

    async def start(self, hostname, port):
        async with websockets.serve(self.handler, hostname, port):
            await asyncio.Future()

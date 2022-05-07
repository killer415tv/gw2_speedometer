import asyncio
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

    async def combined_handler(self, ws, consumer, handler):
        await asyncio.gather(
            self.consumer_handler(ws, consumer),
            self.producer_handler(ws, handler),
        )

    async def start(self, consumer, producer):
        async for ws in websockets.connect(self.server_url):
            try:
                await self.combined_handler(ws, consumer, producer)
            except websockets.ConnectionClosed:
                continue


class WebsocketServer:
    connections = set()

    async def handler(self, ws):
        print(f"con opened: {ws.id}")
        self.connections.add(ws)

        async for msg in ws:
            websockets.broadcast(self.connections, msg)
            logging.info(msg)

        self.connections.remove(ws)
        print(f"con closed: {ws.id}")

    async def start(self, hostname, port):
        async with websockets.serve(self.handler, hostname, port):
            await asyncio.Future()

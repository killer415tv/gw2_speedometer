import asyncio
import websockets
import logging

from websocket_util import WebsocketServer

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    ws_server = WebsocketServer()
    asyncio.run(ws_server.start("", 30200))

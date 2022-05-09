import asyncio
import json
import random
import time

import websockets
import logging

from websocket_util import WebsocketClient

ID = random.randint(1, 500)


async def consume(msg):
    logging.info(msg)


async def produce():
    await asyncio.sleep(0.2)
    # return f"[{ID}] pog  {time.strftime('%X')}"

    event = {
        "type": "position",
        "user": f"test{ID}",
        "x": random.randrange(-115, 400, 1),
        "y": random.randrange(-1010, -500, 1),
    }
    return json.dumps(event)


async def server_test():
    print(f"started at {time.strftime('%X')}")

    ws_client = WebsocketClient("localhost", 30200)
    # await ws_client.start_map(consume, 111)
    await ws_client.start_speedometer(produce, 333)

    print(f"finished at {time.strftime('%X')}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    asyncio.run(server_test())

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

    event = {
        "type": "position",
        "user": f"{ID}",
        "x": random.randrange(-115, 400, 1),
        "y": random.randrange(-1010, -500, 1),
        "timestamp": time.time()
    }
    return json.dumps(event)


async def server_test():
    print(f"started at {time.strftime('%X')}")

    ws_client = WebsocketClient("beetlerank.com", 1234)
    # await ws_client.start_map(consume, 111)
    await ws_client.start_speedometer(produce, 333)

    print(f"finished at {time.strftime('%X')}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    asyncio.run(server_test())

import json
from enum import IntEnum

import aiohttp
from aiohttp import web

from blockchain import Blockchain


class MessageTypes(IntEnum):
    QUERY_LATEST = 0
    QUERY_ALL = 1
    RESPONSE_BLOCKCHAIN = 2


blockchain = Blockchain()


async def blocks(request):
    return web.Response(text=blockchain.json(), content_type='application/json')


async def mine_block(request):
    data = (await request.read()).decode('utf-8')
    new_block = blockchain.generate_new_block(data)
    blockchain.add_block(new_block)
    print('block added ', new_block.json())
    return web.Response(text=new_block.json(), content_type='application/json')


async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = json.loads(msg.data)

            if 'type' not in data:
                raise ValueError('Wrong message format')

            if data['type'] == MessageTypes.QUERY_LATEST:
                ws.send_str(json.dumps({'type': MessageTypes.RESPONSE_BLOCKCHAIN,
                                        'data': blockchain.latest_block.dict()}))
            elif data['type'] == MessageTypes.QUERY_ALL:
                ws.send_str(json.dumps({'type': MessageTypes.RESPONSE_BLOCKCHAIN,
                                        'data': blockchain.dict()}))

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception ', ws.exception())

    return ws


def get_app(loop=None):
    app = web.Application(loop=loop)
    app.router.add_get('/blocks', blocks)
    app.router.add_post('/mineBlock', mine_block)
    app.router.add_get('/ws', ws_handler)
    return app


if __name__ == '__main__':
    web.run_app(get_app())

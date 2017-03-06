import json
from enum import IntEnum

import aiohttp
from aiohttp import web

from blockchain import Blockchain, Block


class MessageTypes(IntEnum):
    QUERY_LATEST = 0
    QUERY_ALL = 1
    RESPONSE_BLOCKCHAIN = 2


class Server(object):
    def __init__(self, app):
        self.blockchain = Blockchain()
        self.app = app

        self.app.router.add_get('/blocks', self.blocks)
        self.app.router.add_post('/mineBlock', self.mine_block)
        self.app.router.add_get('/ws', self.ws_handler)

    async def blocks(self, request):
        return web.Response(text=self.blockchain.json(), content_type='application/json')

    async def mine_block(self, request):
        data = (await request.read()).decode('utf-8')
        new_block = self.blockchain.generate_new_block(data)
        self.blockchain.add_block(new_block)
        print('block added ', new_block.json())
        return web.Response(text=new_block.json(), content_type='application/json')

    async def handle_query_all(self, ws):
        ws.send_str(json.dumps({'type': MessageTypes.RESPONSE_BLOCKCHAIN,
                                'data': self.blockchain.dict()}))

    async def handle_query_latest(self, ws):
        ws.send_str(json.dumps({'type': MessageTypes.RESPONSE_BLOCKCHAIN,
                                'data': self.blockchain.latest_block.dict()}))

    async def handle_response_blockchain(self, ws, msg):
        received_blocks = json.loads(msg.data)['data']
        latest_block_received = received_blocks[-1]

        if len(received_blocks) > self.blockchain.length:
            print(
                'blockchain possibly behind. We got: {} Peer got: {}'.format(self.blockchain.length, len(received_blocks)))

            if self.blockchain.latest_block.hash == latest_block_received['previous_hash']:
                print('We can append received block to our chain')
                self.blockchain.add_block(Block(**latest_block_received))
            ws.send_str(msg.data)
        else:
            ws.send_str(None)

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)

                if 'type' not in data:
                    raise ValueError('Wrong message format')

                if data['type'] == MessageTypes.QUERY_LATEST:
                    await self.handle_query_latest(ws)
                elif data['type'] == MessageTypes.QUERY_ALL:
                    await self.handle_query_all(ws)
                elif data['type'] == MessageTypes.RESPONSE_BLOCKCHAIN:
                    await self.handle_response_blockchain(ws, msg)
                else:
                    raise ValueError('Unknown message type')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print('ws connection closed with exception ', ws.exception())

        return ws


def get_server(loop=None):
    return Server(web.Application(loop=loop))


if __name__ == '__main__':
    server = get_server()
    web.run_app(server.app)

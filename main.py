import json
import os
from enum import IntEnum
from typing import List

import aiohttp
from aiohttp import web

from blockchain import Blockchain, Block


class MessageTypes(IntEnum):
    QUERY_LATEST = 0
    QUERY_ALL = 1
    RESPONSE_BLOCKCHAIN = 2


class Server(object):
    def __init__(self, loop, initial_peers=None):
        self.blockchain = Blockchain()
        self.peer_connections = []
        self.session = None
        self.app = web.Application(loop=loop)
        self.loop = loop

        if initial_peers:
            self.connect_to_peers(initial_peers)

        self.app.router.add_get('/blocks', self.blocks)
        self.app.router.add_post('/mineBlock', self.mine_block)
        self.app.router.add_post('/addPeer', self.add_peer)
        self.app.router.add_get('/ws', self.ws_handler)

    async def connect_to_peers(self, peers: List[str]):
        async with aiohttp.ClientSession(loop=self.loop) as session:
            for peer in peers:
                connection = await session.ws_connect(peer)
                self.peer_connections.append(connection)

    async def broadcast(self, msg: str):
        for peer_connection in self.peer_connections:
            await peer_connection.send_str(msg)

    async def blocks(self, request):
        return web.Response(text=self.blockchain.json(), content_type='application/json')

    async def mine_block(self, request):
        data = json.loads((await request.read()).decode('utf-8'))['data']
        new_block = self.blockchain.generate_new_block(data)
        self.blockchain.add_block(new_block)
        print('block added ', new_block.json())
        return web.Response(text=new_block.json(), content_type='application/json')

    async def add_peer(self, request):
        peer = json.loads((await request.read()).decode('utf-8'))['peer']
        await self.connect_to_peers([peer])
        return web.Response(text='', content_type='application/json')

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
            print('blockchain possibly behind. We got: {} Peer got: {}'.format(self.blockchain.length,
                                                                               len(received_blocks)))

            if self.blockchain.latest_block.hash == latest_block_received['previous_hash']:
                print('We can append received block to our chain')
                self.blockchain.add_block(Block(**latest_block_received))
                await self.broadcast(self.get_response_latest_msg())
            elif len(received_blocks) == 1:
                print('We have to query the chain from our peer')
                await self.broadcast(self.get_query_all_msg())
            else:
                print('Received blockchain is longer than current blockchain')
                self.blockchain.replace_chain(received_blocks)
                await self.broadcast(self.get_response_latest_msg())
            ws.send_str(msg.data)
        else:
            ws.send_str(None)

    def get_response_latest_msg(self) -> str:
        return json.dumps({'type': MessageTypes.RESPONSE_BLOCKCHAIN,
                           'data': [self.blockchain.latest_block.dict()]})

    def get_query_all_msg(self) -> str:
        return json.dumps({'type': MessageTypes.QUERY_ALL})

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


def get_server(loop=None, initial_peers=list()):
    return Server(loop, initial_peers)


if __name__ == '__main__':
    port = os.environ.get('HTTP_PORT', 3001)
    initial_peers = os.environ.get('PEERS', [])

    if initial_peers:
        initial_peers = initial_peers.split(',')

    server = get_server(initial_peers=initial_peers)

    web.run_app(server.app, port=int(port))

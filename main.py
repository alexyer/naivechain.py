from aiohttp import web

from blockchain import Blockchain


blockchain = Blockchain()


async def blocks(request):
    return web.Response(text=blockchain.json(), content_type='application/json')


async def mine_block(request):
    data = (await request.read()).decode('utf-8')
    new_block = blockchain.generate_new_block(data)
    blockchain.add_block(new_block)
    print('block added ', new_block.json())
    return web.Response(text=new_block.json(), content_type='application/json')


def get_app(loop=None):
    app = web.Application(loop=loop)
    app.router.add_get('/blocks', blocks)
    app.router.add_post('/mineBlock', mine_block)
    return app


if __name__ == '__main__':
    web.run_app(get_app())

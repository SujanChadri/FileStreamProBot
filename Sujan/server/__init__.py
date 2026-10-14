# © agrprojects

import os
from aiohttp import web
from .stream_routes import routes


async def web_server():
    web_app = web.Application(client_max_size=30000000)
    static_dir = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
    )
    if os.path.isdir(static_dir):
        # Must be registered before the catch-all stream route
        web_app.router.add_static("/static", static_dir, show_index=False)
    web_app.add_routes(routes)
    return web_app

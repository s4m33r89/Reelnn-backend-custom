from config import PORT


def get_app():
    from web.main import app

    return app


async def serve():
    import uvicorn
    from web.main import app

    config = uvicorn.Config(app, host="0.0.0.0", port=PORT)
    server = uvicorn.Server(config)
    await server.serve()

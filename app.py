import asyncio
import logging

from quart import Quart

from common.app_init import cyoda_token
from common.auth.auth import authenticate
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)

logging.basicConfig(level=logging.INFO)

@app.before_serving
async def startup():
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))
    init_cyoda(cyoda_token)

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

#put_application_code_here

if __name__ == '__main__':
    app.run()

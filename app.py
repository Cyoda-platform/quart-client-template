import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.user.api import api_bp_user
from entity.post.api import api_bp_post
from entity.comment.api import api_bp_comment

from entity.comment.api import api_bp_comment

from entity.post.api import api_bp_post
from entity.comment.api import api_bp_comment


logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_user, url_prefix='/api/user')
app.register_blueprint(api_bp_post, url_prefix='/api/post')
app.register_blueprint(api_bp_comment, url_prefix='/api/comment')

app.register_blueprint(api_bp_comment, url_prefix='/api/comment')

app.register_blueprint(api_bp_post, url_prefix='/api/post')
app.register_blueprint(api_bp_comment, url_prefix='/api/comment')


@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))


@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

#put_application_code_here

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
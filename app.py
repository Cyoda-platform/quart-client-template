import asyncio
import logging

from quart import Quart
from quart_schema import QuartSchema
from common.grpc_client.grpc_client import grpc_stream
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token
#please update this line to your entity
from entity.aggregate.api import api_bp_aggregate
from entity.send_report.api import api_bp_send_report
from entity.products.api import api_bp_products
from entity.report.api import api_bp_report


logging.basicConfig(level=logging.INFO)

app = Quart(__name__)
QuartSchema(app)
app.register_blueprint(api_bp_aggregate, url_prefix='/api/aggregate')
app.register_blueprint(api_bp_send_report, url_prefix='/api/send_report')
app.register_blueprint(api_bp_products, url_prefix='/api/products')
app.register_blueprint(api_bp_report, url_prefix='/api/report')


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
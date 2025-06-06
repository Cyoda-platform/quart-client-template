import logging
import uuid
import json
import asyncio
import grpc

from cloudevents_pb2 import CloudEvent
from common.config import config
from common.config.config import GRPC_PROCESSOR_TAG
from cyoda_cloud_api_pb2_grpc import CloudEventsServiceStub
from entity.workflow import process_dispatch, process_event

# These tags/configs from your original snippet
TAGS = [GRPC_PROCESSOR_TAG]
OWNER = "PLAY"
SPEC_VERSION = "1.0"
SOURCE = "SimpleSample"
JOIN_EVENT_TYPE = "CalculationMemberJoinEvent"
CALC_RESP_EVENT_TYPE = "EntityProcessorCalculationResponse"
CALC_REQ_EVENT_TYPE = "EntityProcessorCalculationRequest"
CRITERIA_CALC_REQ_EVENT_TYPE = "EntityCriteriaCalculationRequest"
CRITERIA_CALC_RESP_EVENT_TYPE = "EntityCriteriaCalculationResponse"
GREET_EVENT_TYPE = "CalculationMemberGreetEvent"
KEEP_ALIVE_EVENT_TYPE = "CalculationMemberKeepAliveEvent"
EVENT_ACK_TYPE = "EventAckResponse"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrpcClient:
    def __init__(self, auth):
        self.auth = auth

    def metadata_callback(self, context, callback):
        """
        gRPC metadata provider that attaches a fresh Bearer token.
        If retrieving the token fails, it invalidates and retries once.
        """
        try:
            token = self.auth.get_access_token()
        except Exception as e:
            logger.warning("Access‑token fetch failed, invalidating and retrying", exc_info=e)
            self.auth.invalidate_tokens()
            token = self.auth.get_access_token()

        callback([('authorization', f'Bearer {token}')], None)

    def get_grpc_credentials(self) -> grpc.ChannelCredentials:
        """
        Create composite credentials: SSL + per‑call metadata token.
        """
        call_creds = grpc.metadata_call_credentials(self.metadata_callback)
        ssl_creds = grpc.ssl_channel_credentials()
        return grpc.composite_channel_credentials(ssl_creds, call_creds)

    def create_cloud_event(self, event_id: str, source: str, event_type: str, data: dict) -> CloudEvent:
        return CloudEvent(
            id=event_id,
            source=source,
            spec_version=SPEC_VERSION,
            type=event_type,
            text_data=json.dumps(data),
        )

    def create_join_event(self) -> CloudEvent:
        return self.create_cloud_event(
            event_id=str(uuid.uuid4()),
            source=SOURCE,
            event_type=JOIN_EVENT_TYPE,
            data={"owner": OWNER, "tags": TAGS},
        )

    def create_notification_event(self, data: dict, type: str, response=None) -> CloudEvent:
        if type == CALC_REQ_EVENT_TYPE:
            return self.create_cloud_event(
                event_id=str(uuid.uuid4()),
                source=SOURCE,
                event_type=CALC_RESP_EVENT_TYPE,
                data={
                    "requestId": data.get('requestId'),
                    "entityId": data.get('entityId'),
                    "owner": OWNER,
                    "payload": data.get('payload'),
                    "success": True
                }
            )
        elif type == CRITERIA_CALC_REQ_EVENT_TYPE:
            return self.create_cloud_event(
                event_id=str(uuid.uuid4()),
                source=SOURCE,
                event_type=CRITERIA_CALC_RESP_EVENT_TYPE,
                data={
                    "requestId": data.get('requestId'),
                    "entityId": data.get('entityId'),
                    "owner": OWNER,
                    "matches": response,
                    "success": True
                }
            )
        else:
            raise ValueError(f"Unsupported notification type: {type}")

    async def event_generator(self, queue: asyncio.Queue):
        yield self.create_join_event()
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
            queue.task_done()

    async def handle_keep_alive_event(self, response, queue: asyncio.Queue):
        data = json.loads(response.text_data)
        ack = self.create_cloud_event(
            event_id=str(uuid.uuid4()),
            source=SOURCE,
            event_type=EVENT_ACK_TYPE,
            data={
                "sourceEventId": data.get('id'),
                "owner": OWNER,
                "payload": None,
                "success": True,
            },
        )
        await queue.put(ack)

    async def process_calc_req_event(self, data: dict, queue: asyncio.Queue, type: str):
        processor_name = data.get('processorName')
        try:
            # Process the first or subsequent versions of the entity
            if processor_name in process_dispatch:
                logger.debug(f"Processing notification entity: {data}")
                await process_event(data=data, processor_name=processor_name)

        except Exception as e:
            logger.error(e)
        #Create notification event and put it in the queue
        notification_event = self.create_notification_event(data=data, type=type)
        await queue.put(notification_event)

    async def consume_stream(self):
        backoff = 1
        while True:
            creds = self.get_grpc_credentials()
            queue = asyncio.Queue()

            try:
                async with grpc.aio.secure_channel(config.GRPC_ADDRESS, creds) as channel:
                    stub = CloudEventsServiceStub(channel)
                    call = stub.startStreaming(self.event_generator(queue))

                    async for response in call:
                        if response.type == KEEP_ALIVE_EVENT_TYPE:
                            asyncio.create_task(self.handle_keep_alive_event(response, queue))
                        elif response.type == EVENT_ACK_TYPE:
                            logger.debug(response)
                        elif response.type in (CALC_REQ_EVENT_TYPE, CRITERIA_CALC_REQ_EVENT_TYPE):
                            logger.info(f"Calc request: {response.type}")
                            data = json.loads(response.text_data)
                            asyncio.create_task(self.process_calc_req_event(data, queue, response.type))
                        elif response.type == GREET_EVENT_TYPE:
                            logger.info("Greet event received")
                        else:
                            logger.error(f"Unhandled event type: {response.type}")

                # If we exit the stream cleanly, break out of the retry loop
                return

            except grpc.RpcError as e:
                # UNAUTHENTICATED → invalidate tokens, then retry with fresh creds
                if getattr(e, "code", lambda: None)() == grpc.StatusCode.UNAUTHENTICATED:
                    logger.warning(
                        "Stream got UNAUTHENTICATED—invalidating tokens and retrying",
                        exc_info=e,
                    )
                    self.auth.invalidate_tokens()
                else:
                    # Log everything else and retry
                    logger.exception("gRPC RpcError in consume_stream", exc_info=e)


            except Exception as e:
                # Catch-all for anything unexpected
                logger.exception("Unexpected error in consume_stream", exc_info=e)

            # back off and retry
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)  # exponential backoff up to 30s

    async def grpc_stream(self):
        """
        Entry point: keeps the bidirectional stream alive, reconnecting on token revocations.
        """
        await self.consume_stream()

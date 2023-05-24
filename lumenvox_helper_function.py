import os.path
import queue
import threading
import typing
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

import grpc

from enum import IntEnum
from google.protobuf.json_format import MessageToJson

# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats
# common.proto messages
import lumenvox.api.common_pb2 as common_msg
# global.proto message
import lumenvox.api.global_pb2 as global_msg
# interaction.proto messages
import lumenvox.api.interaction_pb2 as interaction_msg
# results.proto messages
import lumenvox.api.results_pb2 as results_msg
# session.proto messages
import lumenvox.api.session_pb2 as session_msg
# settings.proto messages
import lumenvox.api.settings_pb2 as settings_msg
# optional_values.proto messages
import lumenvox.api.optional_values_pb2 as optional_values
# LumenVox API protocol buffer messages and stub
from lumenvox.api.lumenvox_pb2_grpc import LumenVoxStub

extra_parameters_broken = True
extra_parameters_reason = "Sending extra parameters is not supported by gRPC."

# Define your target machine here
LUMENVOX_API_SERVICE = 'lumenvox-api.testmachine.com'
# Use this to enable TLS connectivity to your service
ENABLE_TLS = True
# This is used to specify the maximum message length handled by GRPC (do not change unless you understand the impact)
MAX_GRPC_MESSAGE_MB = 4
# This should be changed to match the deployment_id assigned to your system
deploymentid = 'd80b9d9b-086f-42f0-a728-d95f39dc2229'
operatorid = 'a69c7ee5-ac2d-40c2-9524-8fb0f5e5e7fd'

save_tts_test_audio_flag = True


class StreamType(IntEnum):
    """
    Used to determine which type of stream gets created
    Specific to these tests only
    """
    STREAM_TYPE_SESSION = 0
    STREAM_TYPE_GLOBAL = 1
    STREAM_TYPE_BATCH = 2


class ResponseQueues:
    """
    Provides a set of queues to store SessionResponse messages in
    """

    def __init__(self):
        self.vad_event_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.partial_result_queue = asyncio.Queue()
        self.session_event_queue = asyncio.Queue()
        self.general_response_queue = asyncio.Queue()


class GlobalResponseQueues:
    """
    Provides a set of queues to store GlobalResponse messages in
    """

    def __init__(self):
        self.global_event_queue = asyncio.Queue()
        self.global_settings_queue = asyncio.Queue()


class NotificationEvents:
    def __init__(self):
        self.result_event = asyncio.Event()
        self.partial_result_event = asyncio.Event()
        self.audio_complete_event = asyncio.Event()


class ResponseHandler:
    def __init__(self, session_callback_stream):
        self.session_callback_stream = session_callback_stream
        self.callback_loop = asyncio.get_event_loop()


class AudioBuffer:
    def __init__(self, audio_data, chunk_bytes=200):
        # This audio_data buffer assigned during constructor can be referenced later
        self.audio_data = audio_data

        # During creation, users can specify a different chunk size, or use the default
        self.chunk_bytes = chunk_bytes

        self.read_location = 0
        self.bytes_remaining = 0
        # Note bytes remaining cannot easily be converted to milliseconds here, since we don't know audio format!
        self.total_audio_bytes = len(audio_data)

    def get_next_chunk(self):
        self.bytes_remaining = self.total_audio_bytes - self.read_location
        if self.bytes_remaining < 0:
            self.bytes_remaining = 0
        if self.bytes_remaining > 0:
            if self.bytes_remaining >= self.chunk_bytes:
                bytes_to_send = self.chunk_bytes
            else:
                bytes_to_send = self.bytes_remaining

            result_chunk = self.audio_data[self.read_location:self.read_location + bytes_to_send]
            self.read_location += bytes_to_send
            return result_chunk
        else:
            return None


class LumenVoxApiClient:
    """
    A class strictly for core LumenVox api functions used by example code.
    Handles streams, requests, and message definitions.
    Example code of each type of interaction is in its own file.
    """

    session_stream_set = set()  # store references to session streams
    global_stream_set = set()  # store references to global streams
    queue_map = {}  # Map of session streams to queues
    event_map = {}  # Map of session streams to events
    session_id_map = {}  # map of session streams to session ids
    cancel_event = None
    session_id_queue = None
    stream_reader_task = None
    global_reader_task = None
    reader_task_cancel = asyncio.Event()
    reader_task_cancel_2 = asyncio.Event()
    loop = None

    response_handler_queue = None  # Queue of callback ResponseHandler objects

    result_ready = False

    def __init__(self):
        super().__init__()
        self.test_stub = None

    def optional_bool(self, value: bool) -> optional_values.OptionalBool:
        """
        Returns OptionalBool message containing the given value
        """
        return optional_values.OptionalBool(value=value)

    def optional_string(self, value: str) -> optional_values.OptionalString:
        """
        Returns OptionalString message containing the given value
        """
        return optional_values.OptionalString(value=value)

    def optional_int32(self, value: int) -> optional_values.OptionalInt32:
        """
        Returns OptionalInt32 message containing the given value
        """
        return optional_values.OptionalInt32(value=value)

    async def create_channel_and_init_stream(self, stream_type: int = StreamType.STREAM_TYPE_SESSION) \
            -> grpc.aio._call.StreamStreamCall:
        """
        Initializes gRPC channel and returns a newly created stream

        The stream_type parameter will determine if a Session (0) or Global (1) stream is returned
        """
        grpc_channel = self.get_grpc_channel_for_service(service_name='lumenvox_api_service', is_async=True)
        stub = LumenVoxStub(channel=grpc_channel)

        if stream_type == StreamType.STREAM_TYPE_SESSION:
            stream = stub.Session()
        elif stream_type == StreamType.STREAM_TYPE_GLOBAL:
            stream = stub.Global()
        else:
            stream = stub.Session()

        return stream

    def init_session_stream_maps(self, session_stream):
        self.queue_map[session_stream] = ResponseQueues()
        self.event_map[session_stream] = NotificationEvents()

    def init_global_stream_maps(self, global_stream):
        self.queue_map[global_stream] = GlobalResponseQueues()

    async def get_global_event_callback(self, global_stream, wait: int = 1):
        """
        Given global stream, attempt to receive a global_event response from the respective queue
        """
        if global_stream not in self.queue_map:
            return None

        return await self.get_from_queue(aio_queue=self.queue_map[global_stream].global_event_queue, wait=wait)

    def initialize_lumenvox_api(self):
        # Initialize the channel and stub (using defined service endpoint)
        if ENABLE_TLS:
            with open('./server.crt', 'rb') as f:
                credentials = grpc.ssl_channel_credentials(root_certificates=f.read())
            self.channel = grpc.secure_channel(LUMENVOX_API_SERVICE, credentials=credentials)
        else:
            self.channel = grpc.insecure_channel(LUMENVOX_API_SERVICE,
                                                 options=[
                                                     ('grpc.max_send_message_length', MAX_GRPC_MESSAGE_MB * 1048576),
                                                     ('grpc.max_receive_message_length', MAX_GRPC_MESSAGE_MB * 1048576),
                                                 ])
        self.stub = LumenVoxStub(self.channel)

        # Initialize threading
        self._peer_responded = threading.Event()
        self.executor = ThreadPoolExecutor()
        self.cancel_event = threading.Event()

        self.session_id_queue = queue.SimpleQueue()

    def shutdown_lumenvox_api_client(self):
        self.cancel_event.set()
        self.executor.shutdown(wait=False)

        # iterate through all response handlers and stop their loops and streams
        while self.response_handler_queue.qsize():
            response_handler = typing.cast(ResponseHandler, self.response_handler_queue.get())
            response_handler.callback_loop.stop()
            response_handler.session_callback_stream.cancel()  # Cancel the stream

    async def task_read_session_streams(self):
        """
        Iterates through set of session streams and process responses
        """
        while not self.reader_task_cancel.is_set():
            if self.session_stream_set is None:
                return
            for stream in self.session_stream_set:
                # for each stream in the set, check for certain response types to put into their own queues
                if 'terminated' not in str(stream):  # don't attempt to read if the stream's been terminated
                    r = await stream.read()
                    if r:
                        if r.session_id.value:
                            self.session_id_queue.put_nowait(r.session_id.value)
                            self.session_id_map[stream] = r.session_id.value
                        response_type = r.WhichOneof("response_type")

                        # handle notification responses
                        if response_type == 'session_event':

                            # if we receive a status_message with an error code, raise exception here to be handled
                            # later
                            if r.session_event.status_message.code:
                                raise Exception(r.session_event.status_message.code,
                                                r.session_event.status_message.message)

                            self.queue_map[stream].session_event_queue.put_nowait(r.session_event)
                        elif response_type == 'vad_event':
                            self.queue_map[stream].vad_event_queue.put_nowait(r.vad_event)
                        elif response_type == 'partial_result':
                            # put partial result message into queue and set event
                            print('>> task_read_session_streams: partial_result\n', r)
                            self.queue_map[stream].partial_result_queue.put_nowait(r.partial_result)
                            self.event_map[stream].partial_result_event.set()
                        elif response_type == 'final_result':
                            # put final result message into queue and set event
                            print('>> task_read_session_streams: final_result\n', r)
                            self.queue_map[stream].result_queue.put_nowait(r.final_result)
                            self.event_map[stream].result_event.set()
                        else:
                            self.queue_map[stream].general_response_queue.put_nowait(r)

            await asyncio.sleep(0)
        return

    async def task_read_global_streams(self):
        """
        Iterates through set of global streams and process responses
        """
        while not self.reader_task_cancel_2.is_set():
            if self.global_stream_set is None:
                return
            for stream in self.global_stream_set:
                # for each stream in the set, check for certain response types to put into their own queues
                if 'terminated' not in str(stream):  # don't attempt to read if the stream's been terminated
                    r = await stream.read()
                    if r:
                        response_type = r.WhichOneof("response")

                        if response_type == 'global_event':
                            if r.global_event.status_message.code:
                                raise Exception(r.global_event.status_message.code,
                                                r.global_event.status_message.message)

                            self.queue_map[stream].global_event_queue.put_nowait(r.global_event)
                        elif response_type == 'global_settings':
                            self.queue_map[stream].global_settings_queue.put_nowait(r.global_settings)
                        else:
                            pass
            await asyncio.sleep(0)
        return

    def empty_queue(self, q: asyncio.Queue):
        for _ in range(q.qsize()):
            q.get_nowait()
            q.task_done()

    def empty_all_stream_queues(self):
        """
        Empty all queues related session streams
        """
        if not self.session_stream_set:
            return

        for stream in self.session_stream_set:
            self.empty_queue(self.queue_map[stream].session_event_queue)
            self.empty_queue(self.queue_map[stream].general_response_queue)
            self.empty_queue(self.queue_map[stream].partial_result_queue)
            self.empty_queue(self.queue_map[stream].result_queue)
            self.empty_queue(self.queue_map[stream].vad_event_queue)

    def empty_global_queues(self):
        """
        Empty all queues related to global streams
        """
        if not self.global_stream_set:
            return

        for stream in self.global_stream_set:
            self.empty_queue(self.queue_map[stream].global_event_queue)
            self.empty_queue(self.queue_map[stream].global_settings_queue)

    def empty_all_queues(self):
        self.empty_all_stream_queues()
        self.empty_global_queues()

        self.empty_queue(self.session_id_queue)
        self.empty_queue(self.response_handler_queue)

    async def get_from_queue(self, aio_queue: asyncio.Queue, wait: int):
        """
        General queue get helper
        """
        try:
            if not wait:
                return aio_queue.get_nowait()
            else:
                try:
                    return await asyncio.wait_for(aio_queue.get(), wait)
                except asyncio.TimeoutError:
                    # asyncio.wait_for will raise a TimeoutError if it doesn't retrieve anything in the specified time,
                    # but here we'll just return None and handle the case within the tests
                    return None
        except queue.Empty as e:
            return None
        except asyncio.QueueEmpty as e:
            return None

    async def get_session_general_response(self, session_stream, wait: int = 3):
        """
        Given session stream, attempt to receive a general (non-notification) response from the respective queue
        """
        if session_stream not in self.queue_map:
            return None

        return await self.get_from_queue(aio_queue=self.queue_map[session_stream].general_response_queue, wait=wait)

    async def get_session_final_result(self, session_stream, wait: int = 3):
        """
        Retrieve the final result response of the given session stream if available; otherwise, return None.
        """
        if session_stream not in self.queue_map:
            return None

        return await self.get_from_queue(aio_queue=self.queue_map[session_stream].result_queue, wait=wait)

    async def set_session_stream_for_reader_task(self, session_stream):
        """
        Add session stream to set so that it can be read from response-reading task
        """
        self.session_stream_set.add(session_stream)

    async def set_global_stream_for_reader_task(self, global_stream):
        """
        Add global stream to set so that it can be read from response-reading task
        """
        self.global_stream_set.add(global_stream)

    def set_streams_sets_to_none(self):
        """
        Set both session and global stream sets to None (to quit response handling flags)
        """
        self.session_stream_set = None
        self.global_stream_set = None

    def run_user_coroutine(self, user_coroutine, expected_rpc_error_status_code: int = 0,
                           expected_rpc_error_message: str = None):
        """
        The Lumenvox gRPC API works with asynchronous message in both directions
        This function sets up needed event loop and message queues to support that
        The user supplied coroutine is the "program" to run with Lumenvox API support
        
        @param user_coroutine: The async-defined coroutine to run as the main task
        """
        self.session_stream_set = set()
        self.global_stream_set = set()

        # Set event loop policy on Windows
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        if (self.loop is None) or (not self.loop.is_running()):
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.session_id_queue = asyncio.Queue()
        self.response_handler_queue = asyncio.Queue()

        self.reader_task_cancel = asyncio.Event()
        self.reader_task_cancel_2 = asyncio.Event()

        self.stream_reader_task = self.loop.create_task(self.task_read_session_streams())
        self.global_reader_task = self.loop.create_task(self.task_read_global_streams())

        main_task = self.loop.create_task(user_coroutine)
        tasks = asyncio.gather(main_task, self.stream_reader_task, self.global_reader_task)

        # Here we run tasks and handle any testing error that may occur and that we may want to check for.
        # Should a test throw an error type that isn't represented, it should be added and accounted for here.
        try:
            self.loop.run_until_complete(tasks)
        # prevent tests from closing should a task be cancelled
        except asyncio.CancelledError:
            print("run_user_coroutine: Tasks have been cancelled.")
            tasks.exception()
        # set stream sets to None before raising errors
        except AssertionError as e:
            tasks.exception()
            self.set_streams_sets_to_none()
            raise e
        except AttributeError as e:
            tasks.exception()
            self.set_streams_sets_to_none()
            raise e
        except KeyError as e:
            tasks.exception()
            self.set_streams_sets_to_none()
            raise e
        except Exception as e:
            tasks.exception()
            self.set_streams_sets_to_none()

            # raise the error if neither expected code nor message is provided
            if not (expected_rpc_error_status_code or expected_rpc_error_message):
                raise

            if expected_rpc_error_status_code:
                self.assertEqual(e.args[0], expected_rpc_error_status_code,
                                 msg='Different RPC error status code received than what was expected.')
            if expected_rpc_error_message:
                self.assertEqual(e.args[1], expected_rpc_error_message,
                                 msg='Different RPC error status message received than what was expected.')
        finally:
            self.empty_all_queues()
            # self.cancel_all_tasks()
            if self.loop.is_running():
                self.loop.close()

    async def session_stream_write(self, session_stream, correlation_id: str = None,
                                   session_request_msg: session_msg.SessionRequestMessage = None,
                                   audio_request_msg: common_msg.AudioRequestMessage = None,
                                   interaction_request_msg: interaction_msg.InteractionRequestMessage = None,
                                   dtmf_push_req: common_msg.DtmfPushRequest = None):
        """
        Takes a stream, correlation ID and one of the 'oneof' request types: SessionRequestMessage (NOT
        SessionRequest), AudioRequestMessage, InteractionRequestMessage, DtmfPushRequest to construct a SessionRequest
        with.
        Sends the SessionRequest message to the stream
        """

        # provided random correlation ID if a string for it is not provided.
        correlation_id = optional_values.OptionalString(value=correlation_id if correlation_id else str(uuid.uuid4()))

        # print("# session_stream_write:"
        #      " Sending SessionRequest to Session stream [correlation ID:", correlation_id.value, "]")
        session_request = None

        if session_request_msg:
            session_request = \
                session_msg.SessionRequest(correlation_id=correlation_id, session_request=session_request_msg)
        elif audio_request_msg:
            session_request = \
                session_msg.SessionRequest(correlation_id=correlation_id, audio_request=audio_request_msg)
        elif interaction_request_msg:
            session_request = \
                session_msg.SessionRequest(correlation_id=correlation_id, interaction_request=interaction_request_msg)
        elif dtmf_push_req:
            session_request = \
                session_msg.SessionRequest(correlation_id=correlation_id, dtmf_request=dtmf_push_req)

        # print('# session_stream_write: The following SessionRequest will be sent to the stream:\n', session_request)
        await session_stream.write(session_request)

    async def global_stream_write(self, global_stream,
                                  deployment_id: str, operator_id: str, correlation_id: str = None,
                                  global_load_grammar_request: global_msg.GlobalLoadGrammarRequest = None,
                                  global_load_phrase_list: global_msg.GlobalLoadPhraseList = None,
                                  global_get_settings_request: global_msg.GlobalGetSettingsRequest = None,
                                  session_settings: settings_msg.SessionSettings = None,
                                  interaction_settings: settings_msg.InteractionSettings = None,
                                  grammar_settings: settings_msg.GrammarSettings = None,
                                  recognition_settings: settings_msg.RecognitionSettings = None,
                                  normalization_settings: settings_msg.NormalizationSettings = None,
                                  vad_settings: settings_msg.VadSettings = None,
                                  cpa_settings: settings_msg.CpaSettings = None,
                                  amd_settings: settings_msg.AmdSettings = None,
                                  audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                  logging_settings: settings_msg.LoggingSettings = None,
                                  reset_settings: settings_msg.ResetSettings = None):
        """
        Takes a global stream, correlation ID, deployment ID, operator ID and one of the 'oneof' message types
        Sends the GlobalRequest message to the stream

        Unlike session stream requests, deployment and operator IDs will have to be specified for each request that goes
        into the global stream.
        """

        correlation_id = optional_values.OptionalString(value=correlation_id if correlation_id else str(uuid.uuid4()))

        # initial parameter setup
        global_request = global_msg.GlobalRequest(correlation_id=correlation_id,
                                                  deployment_id=deployment_id,
                                                  operator_id=operator_id,
                                                  global_load_grammar_request=global_load_grammar_request,
                                                  global_load_phrase_list=global_load_phrase_list,
                                                  global_get_settings_request=global_get_settings_request,
                                                  session_settings=session_settings,
                                                  interaction_settings=interaction_settings,
                                                  grammar_settings=grammar_settings,
                                                  recognition_settings=recognition_settings,
                                                  normalization_settings=normalization_settings,
                                                  vad_settings=vad_settings,
                                                  cpa_settings=cpa_settings,
                                                  amd_settings=amd_settings,
                                                  audio_consume_settings=audio_consume_settings,
                                                  logging_settings=logging_settings,
                                                  reset_settings=reset_settings)

        await global_stream.write(global_request)

    async def session_stream_read(self, session_stream, timeout: float = 0.5) -> \
            session_msg.SessionResponse:
        """
        Retrieve SessionResponse from session stream with a timeout
        Generally , trying to read() from a stream that doesn't have any new output will cause a hangup.
        asyncio.wait_for will wait for output to be provided, otherwise this will return None
        """
        try:
            print('session_stream_read: Reading from Session stream with a timeout of', timeout)
            return await asyncio.wait_for(session_stream.read(), timeout=timeout)
        except asyncio.TimeoutError:
            print('session_stream_read: Timeout reached, returning nothing.')
            return None

    async def session_create(self, session_stream, session_id: str = None,
                             deployment_id: str = None,
                             operator_id: str = None,
                             correlation_id: str = None):
        """
        Given a stream, it creates a new session and returns the ID of the new session

        @param session_stream: A previously created stream to and from which we write and read messages
        @param session_id: unique UUID with which the create session will be referenced
        @param deployment_id: unique UUID of the deployment to use for the session
        @param operator_id: optional unique UUID can be used to track who is making API calls
        @param correlation_id: optional UUID can be used to track individual API calls

        """
        if not deployment_id:
            deployment_id = deploymentid

        if not operator_id:
            operator_id = operatorid

        # custom optional_values defined in optional_values.proto need their 'value' field set specifically
        session_id = optional_values.OptionalString(value=session_id) if session_id else None

        # message setup
        session_create_request = session_msg.SessionCreateRequest(deployment_id=deployment_id,
                                                                  operator_id=operator_id, session_id=session_id)
        session_request_msg = session_msg.SessionRequestMessage(session_create=session_create_request)

        # write messages to stream
        print("session_create: Writing session request to stream.")
        await self.session_stream_write(session_stream=session_stream, session_request_msg=session_request_msg,
                                        correlation_id=correlation_id)

        await asyncio.sleep(0.1)

    async def session_close(self, session_stream, correlation_id: str = None):
        """
        Close Session given a stream
        session_stream: A previously created stream to and from which we write and read messages
        """

        # message setup
        session_close_request = session_msg.SessionCloseRequest(**{})
        session_request_msg = session_msg.SessionRequestMessage(session_close=session_close_request)

        print("session_close: Writing session request to stream.")
        await self.session_stream_write(session_stream=session_stream, session_request_msg=session_request_msg,
                                        correlation_id=correlation_id)

    async def session_set_inbound_audio_format(self, session_stream, correlation_id: str = None,
                                               audio_format: int =
                                               audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW,
                                               sample_rate_hertz: int = 8000):
        """
        Specify Audio Format to be used within the session (stream)
        The defaults for audio format (int) and sample rate are set with the parameters
        """

        if audio_format is None:
            audio_format = audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW

        if sample_rate_hertz is None:
            sample_rate_hertz = 8000

        audio_format_msg = audio_formats.AudioFormat(standard_audio_format=audio_format,
                                                     sample_rate_hertz=optional_values.OptionalInt32(
                                                         value=sample_rate_hertz))

        session_inbound_audio_format_request = \
            session_msg.SessionInboundAudioFormatRequest(audio_format=audio_format_msg)
        session_request_msg = \
            session_msg.SessionRequestMessage(session_audio_format=session_inbound_audio_format_request)

        await self.session_stream_write(session_stream=session_stream, session_request_msg=session_request_msg,
                                        correlation_id=correlation_id)

        # session_response = await self.session_stream_read(session_stream=session_stream)
        # return session_response

    async def session_audio_push(self, session_stream, correlation_id: str = None, audio_data: bytes = None):
        """
        Wrapping over AudioPushRequest (common.proto)
        Takes audio_data as bytes and sends the data within a protobuf message over gRPC
        Currently no response to be had
        """

        audio_push_request = common_msg.AudioPushRequest(audio_data=audio_data)
        audio_request_msg = common_msg.AudioRequestMessage(audio_push=audio_push_request)

        await self.session_stream_write(session_stream=session_stream, correlation_id=correlation_id,
                                        audio_request_msg=audio_request_msg)

    async def session_audio_pull(self, session_stream, audio_id: str, correlation_id: str = None,
                                 audio_channel: int = None, audio_start: int = None, audio_length: int = None,
                                 expected_exception_code=None, expected_exception_details=None):
        """
        Wrapping over AudioPullRequest (common.proto)
        Returns AudioPullResponse (which would contain bytes of audio data)

        audio_id: id of the audio requested (Note that this could be session_id to request the inbound audio resource)
        audio_channel: For multichannel audio, this is the channel number being referenced. Range is from 0 to N.
            Default channel 0 will be used if not specified
        audio_start: Number of milliseconds from the beginning of the audio to return (default is from the beginning)
        audio_length: Maximum number of milliseconds to return. A zero value returns all available audio (from requested
            start point). (default is all audio, from start point)
        """

        audio_channel_option = optional_values.OptionalInt32(value=audio_channel) if audio_channel else None
        audio_start_option = optional_values.OptionalInt32(value=audio_start) if audio_start else None
        audio_length_option = optional_values.OptionalInt32(value=audio_length) if audio_length else None
        audio_pull_request = common_msg.AudioPullRequest(audio_id=audio_id,
                                                         audio_channel=audio_channel_option,
                                                         audio_start=audio_start_option,
                                                         audio_length=audio_length_option)

        audio_request_msg = common_msg.AudioRequestMessage(audio_pull=audio_pull_request)

        await self.session_stream_write(session_stream=session_stream, correlation_id=correlation_id,
                                        audio_request_msg=audio_request_msg)

    def define_amd_settings(self, amd_enable: bool = True,
                            fax_enable: bool = True,
                            sit_enable: bool = True,
                            busy_enable: bool = True,
                            tone_detect_timeout_ms: int = None) -> settings_msg.AmdSettings:
        """
        Construct an AmdSettings message (settings.proto)
        The defaults are set in the function definition
        """
        amd_settings = settings_msg.AmdSettings(
            amd_enable=self.optional_bool(amd_enable),
            fax_enable=self.optional_bool(fax_enable),
            sit_enable=self.optional_bool(sit_enable),
            busy_enable=self.optional_bool(busy_enable),
            tone_detect_timeout_ms=self.optional_int32(tone_detect_timeout_ms)
            if (tone_detect_timeout_ms or tone_detect_timeout_ms == 0) else None
        )

        return amd_settings

    def define_cpa_settings(self, human_residence_time_ms: int = 1800, human_business_time_ms: int = 3000,
                            unknown_silence_timeout_ms: int = 5000, max_time_from_connect_ms: int = 0) \
            -> settings_msg.CpaSettings:
        """
        Construct a CpaSettings message (settings.proto)
        The defaults are set in the function definition
        """

        cpa_settings = settings_msg.CpaSettings(
            human_residence_time_ms=self.optional_int32(human_residence_time_ms),
            human_business_time_ms=self.optional_int32(human_business_time_ms),
            unknown_silence_timeout_ms=self.optional_int32(unknown_silence_timeout_ms),
            max_time_from_connect_ms=self.optional_int32(max_time_from_connect_ms)
        )

        return cpa_settings

    def define_audio_consume_settings(self, audio_channel: int = 0,
                                      audio_consume_mode: int =
                                      settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING,
                                      stream_start_location: int =
                                      settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_STREAM_BEGIN,
                                      start_offset_ms: int = 0, audio_consume_max_ms: int = 0) \
            -> settings_msg.AudioConsumeSettings:
        """
        Construct an AudioConsumeSettings message (settings.proto)
        The defaults are set in the function definition

        @param audio_channel: For multi-channel audio, this is the channel number being referenced (Default: 0)
        @param audio_consume_mode: Which audio mode to use
        @param stream_start_location: Specify where audio consume starts when "streaming" mode is used
        @param start_offset_ms: Optional offset in milliseconds to adjust the audio start point. (Default: 0)
        @param audio_consume_max_ms: Optional maximum audio to process. Value of 0 means process all audio sent
        @return: AudioConsumeSettings protobuf message (settings.proto)
        """
        audio_consume_settings = settings_msg.AudioConsumeSettings(
            audio_channel=self.optional_int32(audio_channel),
            audio_consume_mode=audio_consume_mode,
            stream_start_location=stream_start_location,
            start_offset_ms=self.optional_int32(start_offset_ms),
            audio_consume_max_ms=self.optional_int32(audio_consume_max_ms)
        )

        return audio_consume_settings

    def define_vad_settings(self, use_vad: bool = True,
                            barge_in_timeout_ms: int = 3000, end_of_speech_timeout_ms: int = 20000,
                            noise_reduction_mode: int = settings_msg.VadSettings.NoiseReductionMode.NOISE_REDUCTION_MODE_DEFAULT,
                            bargein_threshold: int = 50, eos_delay_ms: int = 800, snr_sensitivity: int = 50,
                            stream_init_delay: int = 100, volume_sensitivity: int = 50,
                            wind_back_ms: int = 480) -> settings_msg.VadSettings:
        """
        Construct a VadSettings message (settings.proto)
        Most settings are optional, defaults are set for the parameters
        """

        vad_settings = settings_msg.VadSettings(
            use_vad=self.optional_bool(use_vad),
            barge_in_timeout_ms=self.optional_int32(barge_in_timeout_ms),
            bargein_threshold=self.optional_int32(bargein_threshold),
            noise_reduction_mode=noise_reduction_mode,
            end_of_speech_timeout_ms=self.optional_int32(end_of_speech_timeout_ms),
            eos_delay_ms=self.optional_int32(eos_delay_ms),
            snr_sensitivity=self.optional_int32(snr_sensitivity),
            stream_init_delay=self.optional_int32(stream_init_delay),
            volume_sensitivity=self.optional_int32(volume_sensitivity),
            wind_back_ms=self.optional_int32(wind_back_ms)
        )

        return vad_settings

    def define_recognition_settings(self, max_alternatives: int = 1,
                                    trim_silence_value: int = 970,
                                    enable_partial_results: bool = True,
                                    confidence_threshold: int = 0) -> settings_msg.RecognitionSettings:
        """
        Construct an RecognitionSettings message (settings.proto)
        The defaults are set in the function definition

        @param max_alternatives: Maximum number of recognition hypotheses to be returned. Default: 1
        @param trim_silence_value: how aggressively the ASR trims leading silence from input audio
        @param enable_partial_results: When true, partial results callbacks will be enabled for the interaction
        @param confidence_threshold: onfidence threshold. Range 0 to 1000; applies to grammar based asr interactions
        @return: RecognitionSettings protobuf message (settings.proto)
        """
        recognition_settings = settings_msg.RecognitionSettings(
            max_alternatives=self.optional_int32(max_alternatives),
            trim_silence_value=self.optional_int32(trim_silence_value),
            enable_partial_results=self.optional_bool(enable_partial_results),
            confidence_threshold=self.optional_int32(confidence_threshold)
        )

        return recognition_settings

    def define_grammar_settings(self,
                                default_tag_format: int = settings_msg.GrammarSettings.TagFormat.TAG_FORMAT_SEMANTICS_1_2006,
                                ssl_verify_peer: bool = True,
                                load_grammar_timeout_ms: int = 200000) -> settings_msg.GrammarSettings:
        """
        Construct an GrammarSettings message (settings.proto)
        The defaults are set in the function definition

        @param default_tag_format: The tag-format for loaded grammars. default: TagFormat.TAG_FORMAT_SEMANTICS_1_2006
        @param ssl_verify_peer: If true, https grammar url must have a valid certificate.  default: True
        @param load_grammar_timeout_ms: Timeout to wait for gramamr load.  default: 200000ms
        @return: GrammarSettings protobuf message (settings.proto)
        """

        grammar_settings = settings_msg.GrammarSettings(
            default_tag_format=default_tag_format,
            ssl_verify_peer=self.optional_bool(ssl_verify_peer),
            load_grammar_timeout_ms=self.optional_int32(load_grammar_timeout_ms)
        )

        return grammar_settings

    def define_tts_inline_synthesis_settings(self, voice: str = None, synth_emphasis_level: str = None,
                                             synth_prosody_pitch: str = None, synth_prosody_contour: str = None,
                                             synth_prosody_rate: str = None, synth_prosody_duration: str = None,
                                             synth_prosody_volume: str = None, synth_voice_age: str = None,
                                             synth_voice_gender: str = None) -> settings_msg.TtsInlineSynthesisSettings:
        """
        Construct a TtsInlineSynthesisSetting
        """

        tts_inline_synthesis_settings = settings_msg.TtsInlineSynthesisSettings(
            voice=self.optional_string(voice) if voice else None,
            synth_emphasis_level=self.optional_string(synth_emphasis_level) if synth_emphasis_level else None,
            synth_prosody_pitch=self.optional_string(synth_prosody_pitch) if synth_prosody_pitch else None,
            synth_prosody_contour=self.optional_string(synth_prosody_contour) if synth_prosody_contour else None,
            synth_prosody_rate=self.optional_string(synth_prosody_rate) if synth_prosody_rate else None,
            synth_prosody_duration=self.optional_string(synth_prosody_duration) if synth_prosody_duration else None,
            synth_prosody_volume=self.optional_string(synth_prosody_volume) if synth_prosody_volume else None,
            synth_voice_age=self.optional_string(synth_voice_age) if synth_voice_age else None,
            synth_voice_gender=self.optional_string(synth_voice_gender) if synth_voice_gender else None
        )

        return tts_inline_synthesis_settings

    def define_grammar(self, grammar_url: str = None, inline_grammar_text: str = None,
                       global_grammar_label: str = None, session_grammar_label: str = None,
                       builtin_voice_grammar: int = None,
                       builtin_dtmf_grammar: int = None,
                       label: str = None) -> common_msg.Grammar:
        """
        Build a grammar message (defined in common.proto)
        Returns grammar message

        grammar_url: A grammar URL to be loaded
        inline_grammar_text: A string containing the raw grammar text
        global_grammar_label: Reference to a previously defined "global" grammar
        session_grammar_label: Reference to a previously defined "session" grammar
        builtin_voice_grammar: Reference to a "builtin" voice grammar
        builtin_dtmf_grammar: Reference to a "builtin" DTMF grammar
        label: Optional label assigned to grammar, used for error reporting
        """

        grammar_msg = common_msg.Grammar()

        if grammar_url:
            grammar_msg.grammar_url = grammar_url
        elif inline_grammar_text:
            grammar_msg.inline_grammar_text = inline_grammar_text
        elif global_grammar_label:
            grammar_msg.global_grammar_label = global_grammar_label
        elif session_grammar_label:
            grammar_msg.session_grammar_label = session_grammar_label
        elif builtin_voice_grammar:
            grammar_msg.builtin_voice_grammar = builtin_voice_grammar
        elif builtin_dtmf_grammar:
            grammar_msg.builtin_dtmf_grammar = builtin_dtmf_grammar

        if label:
            grammar_msg.label.value = label

        return grammar_msg

    def inline_grammar_by_file_ref(self, grammar_reference) -> common_msg.Grammar:
        """
        Load text contents of grammar file into grammar message (common.proto) and return grammar message
        """
        return common_msg.Grammar(inline_grammar_text=self.get_grammar_file_by_ref(grammar_reference=grammar_reference))

    async def interaction_create_amd(self, session_stream, amd_settings: settings_msg.AmdSettings,
                                     audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                     vad_settings: settings_msg.VadSettings = None,
                                     general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                     correlation_id: str = None) -> interaction_msg.InteractionCreateAmdResponse:
        """
        Handle InteractionCreateAmd (interaction.proto), given AMD and Audio Consume Settings
        Returns InteractionCreateAmdResponse, containing the interaction ID
        """

        interaction_create_amd_request = interaction_msg.InteractionCreateAmdRequest(
            amd_settings=amd_settings,
            audio_consume_settings=audio_consume_settings,
            vad_settings=vad_settings,
            general_interaction_settings=general_interaction_settings
        )

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_amd=interaction_create_amd_request
        )

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_cpa(self, session_stream, cpa_settings: settings_msg.CpaSettings,
                                     audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                     vad_settings: settings_msg.VadSettings = None,
                                     general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                     correlation_id: str = None) -> interaction_msg.InteractionCreateCpaResponse:
        """
        Handle InteractionCreateCpa (interaction.proto), given CPA and Audio Consume Settings
        Returns InteractionCreateCpaResponse, containing the interaction ID
        """

        interaction_create_cpa_request = interaction_msg.InteractionCreateCpaRequest(
            cpa_settings=cpa_settings,
            audio_consume_settings=audio_consume_settings,
            vad_settings=vad_settings,
            general_interaction_settings=general_interaction_settings
        )

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_cpa=interaction_create_cpa_request
        )

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_asr(self, session_stream, language: str, grammars: list,
                                     grammar_settings: settings_msg.GrammarSettings = None,
                                     recognition_settings: settings_msg.RecognitionSettings = None,
                                     vad_settings: settings_msg.VadSettings = None,
                                     audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                     general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                     correlation_id: str = None) -> interaction_msg.InteractionCreateAsrResponse:
        """
        Handle InteractionCreateAsr (interaction.proto)
        Returns InteractionCreateAsrResponse, containing the interaction ID

        grammars: list of common_msg.Grammar protobuf messages
        """

        interaction_create_asr_request = interaction_msg.InteractionCreateAsrRequest(
            language=language,
            grammars=grammars,
            grammar_settings=grammar_settings,
            recognition_settings=recognition_settings,
            vad_settings=vad_settings,
            audio_consume_settings=audio_consume_settings,
            general_interaction_settings=general_interaction_settings
        )

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_asr=interaction_create_asr_request
        )

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_tts(self, session_stream,
                                     audio_format: int = None, sample_rate_hertz: int = None,
                                     language: str = None, inline_text: str = None,
                                     tts_inline_synthesis_settings: settings_msg.TtsInlineSynthesisSettings = None,
                                     ssml_url: str = None, ssl_verify_peer: bool = True,
                                     synthesis_timeout_ms: int = 5000,
                                     general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                     correlation_id: str = None):
        """
        Handle InteractionCreateTts (interaction.proto)
        InlineTtsRequest:
            inline_text
            tts_inline_synthesis_settings
        SsmlUrlRequest:
            ssml_url
            ssl_verify_peer
        """

        if not audio_format:
            audio_format = audio_formats.AudioFormat(
                standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW,
                sample_rate_hertz=self.optional_int32(8000))
        else:
            audio_format = audio_formats.AudioFormat(
                standard_audio_format=audio_format,
                sample_rate_hertz=self.optional_int32(sample_rate_hertz))

        interaction_create_tts_request = interaction_msg.InteractionCreateTtsRequest(
            language=language,
            audio_format=audio_format,
            general_interaction_settings=general_interaction_settings
        )

        if inline_text:
            # setting message contents this way as the inline_request is a nested message
            interaction_create_tts_request.inline_request.text = inline_text
            if tts_inline_synthesis_settings:
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.voice.value = \
                    tts_inline_synthesis_settings.voice.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_emphasis_level.value = \
                    tts_inline_synthesis_settings.synth_emphasis_level.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_prosody_pitch.value = \
                    tts_inline_synthesis_settings.synth_prosody_pitch.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_prosody_contour.value = \
                    tts_inline_synthesis_settings.synth_prosody_contour.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_prosody_rate.value = \
                    tts_inline_synthesis_settings.synth_prosody_rate.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_prosody_duration.value = \
                    tts_inline_synthesis_settings.synth_prosody_duration.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_prosody_volume.value = \
                    tts_inline_synthesis_settings.synth_prosody_volume.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_voice_age.value = \
                    tts_inline_synthesis_settings.synth_voice_age.value
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.synth_voice_gender.value = \
                    tts_inline_synthesis_settings.synth_voice_gender.value
        elif ssml_url:
            interaction_create_tts_request.ssml_request.ssml_url = ssml_url
            interaction_create_tts_request.ssml_request.ssl_verify_peer.value = ssl_verify_peer

        # interaction_create_tts_request.secure_context.value = secure_context
        interaction_create_tts_request.synthesis_timeout_ms.value = synthesis_timeout_ms

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_tts=interaction_create_tts_request
        )

        await self.session_stream_write(
            session_stream=session_stream,
            interaction_request_msg=interaction_request_msg,
            correlation_id=correlation_id
        )

    async def interaction_create_transcription(self, session_stream, language: str,
                                               phrases: list = None,
                                               continuous_utterance_transcription: bool = False,
                                               recognition_settings: settings_msg.RecognitionSettings = None,
                                               vad_settings: settings_msg.VadSettings = None,
                                               audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                               normalization_settings: settings_msg.NormalizationSettings = None,
                                               phrase_list_settings: settings_msg.PhraseListSettings = None,
                                               general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                               correlation_id: str = None):
        """
        Handle InteractionCreateTranscription (interaction.proto)

        phrases: A list of interaction_msg.TranscriptionPhraseList protobuf messages (interaction.proto),
            see self.define_transcription_phrase_list()
        """

        interaction_create_transcription_request = interaction_msg.InteractionCreateTranscriptionRequest(
            language=language,
            phrases=phrases,
            phrase_list_settings=phrase_list_settings,
            continuous_utterance_transcription=self.optional_bool(continuous_utterance_transcription),
            recognition_settings=recognition_settings,
            vad_settings=vad_settings,
            audio_consume_settings=audio_consume_settings,
            normalization_settings=normalization_settings,
            general_interaction_settings=general_interaction_settings
        )

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_transcription=interaction_create_transcription_request
        )

        await self.session_stream_write(
            session_stream=session_stream,
            interaction_request_msg=interaction_request_msg,
            correlation_id=correlation_id
        )

    async def interaction_create_grammar_parse(self, session_stream, language: str, grammars: list, input_text: str,
                                               grammar_settings: settings_msg.GrammarSettings = None,
                                               general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                               parse_timeout_ms: int = None, correlation_id: str = None):
        """
        Handle InteractionCreateGrammarParse (interaction.proto)

        grammars: A list of common_msg.Grammar protobuf messages
        """

        interaction_create_grammar_parse_request = interaction_msg.InteractionCreateGrammarParseRequest(
            language=language,
            grammars=grammars,
            grammar_settings=grammar_settings,
            input_text=input_text,
            parse_timeout_ms=self.optional_int32(parse_timeout_ms) if parse_timeout_ms else None,
            general_interaction_settings=general_interaction_settings,
        )

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_grammar_parse=interaction_create_grammar_parse_request
        )

        await self.session_stream_write(
            session_stream=session_stream,
            interaction_request_msg=interaction_request_msg,
            correlation_id=correlation_id
        )

    async def interaction_begin_processing(self, session_stream, interaction_id: str, correlation_id: str = None):
        """
        Handle InteractionBeginProcessing (interaction.proto)
        Currently no response to return
        """

        interaction_begin_processing_request = \
            interaction_msg.InteractionBeginProcessingRequest(interaction_id=interaction_id)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_begin_processing=interaction_begin_processing_request
        )

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_finalize_processing(self, session_stream, interaction_id: str, correlation_id: str = None):
        """
        Handle InteractionFinalizeProcessing (interaction.proto)
        Currently no response to return
        """

        interaction_finalize_processing_request = \
            interaction_msg.InteractionFinalizeProcessingRequest(interaction_id=interaction_id)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_finalize_processing=interaction_finalize_processing_request
        )

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_request_results(self, session_stream, interaction_id: str, correlation_id: str = None) \
            -> interaction_msg.InteractionRequestResultsResponse:
        """
        Handle InteractionRequestResults (interaction.proto)
        Returns InteractionRequestResultsResponse
        """

        interaction_request_results_request = \
            interaction_msg.InteractionRequestResultsRequest(interaction_id=interaction_id)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_request_results=interaction_request_results_request
        )

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_close(self, session_stream, interaction_id: str, correlation_id: str = None) \
            -> interaction_msg.InteractionCloseResponse:
        """
        Handle InteractionCloseRequest (interaction.proto)
        Returns InteractionCloseResponse
        """

        interaction_close_request = interaction_msg.InteractionCloseRequest(interaction_id=interaction_id)
        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_close=interaction_close_request
        )

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def audio_push_from_buffer(self, session_stream, audio_buffer, correlation_id: str = None) -> bool:
        """
        Helper function to take an audio buffer (AudioBuffer defined in helper_audio_functions.py) and push its data
        into the session stream.

        With every audio push, a session_event message is returned.
        """
        audio_data = audio_buffer.get_next_chunk()
        if audio_data is None:
            # We've reached the end of the buffer, so nothing else to send.
            return False

        await self.session_audio_push(session_stream=session_stream, audio_data=audio_data,
                                      correlation_id=correlation_id)
        return True

    async def session_init(self, session_id: str = None,
                           deployment_id: str = None,
                           operator_id: str = None,
                           correlation_id: str = None):
        """
        Helper function to create a session and provide both the session stream and ID
        @param session_id: A UUID value to use as the session ID upon creation
        @param deployment_id: unique UUID of the deployment to use for the session
        @param operator_id: optional unique UUID can be used to track who is making API calls
        @param correlation_id: optional UUID can be used to track individual API calls
        @return: Returns both the session_stream and session ID
        """
        session_stream = await self.create_channel_and_init_stream()
        self.init_session_stream_maps(session_stream)
        await self.set_session_stream_for_reader_task(session_stream=session_stream)

        if session_id:
            await self.session_create(session_stream=session_stream, session_id=session_id,
                                      deployment_id=deployment_id, operator_id=operator_id,
                                      correlation_id=correlation_id)
        else:
            await self.session_create(session_stream=session_stream,
                                      deployment_id=deployment_id, operator_id=operator_id,
                                      correlation_id=correlation_id)

        session_id = await self.session_id_queue.get()
        if session_id:
            print("session_id from session_create:", session_id)

        return session_stream, session_id

    async def session_close_all(self, session_stream):
        """
        Helper function to handle closing session and stream. Check that SessionClose returns a proper status code (0).
        @param session_stream:
        @return: None
        """
        await self.session_close(session_stream=session_stream)
        session_close_response = await self.get_session_general_response(session_stream=session_stream, wait=3)
        # self.assertEqual(session_close_response.session_close.close_status.code, 0)

        await session_stream.done_writing()

    async def global_stream_close(self, global_stream):
        await global_stream.done_writing()

    async def close_interaction_and_validate(self, session_stream, interaction_id: str):
        """
        Given a session stream and interaction ID, close the interaction and confirm that the proper interaction was
        closed and that the status code is 0.
        @param session_stream: Stream of the session containing the interaction
        @param interaction_id: ID of the interaction to close
        @return: None
        """
        await self.interaction_close(session_stream=session_stream, interaction_id=interaction_id)
        r2 = await self.get_session_general_response(session_stream=session_stream, wait=3)

    async def handle_interaction_close_all(self, session_stream, interaction_id: str,
                                           close_session: bool = True, global_stream=None):
        """
        Call the function to close interaction (with the proper returned status code), and then close the session and
        associated stream.

        @param global_stream: Possible global stream to close
        @param session_stream: Stream of session to close
        @param interaction_id: ID of interaction to close
        @param close_session: Whether to close session.
        @return:
        """
        await self.close_interaction_and_validate(session_stream=session_stream,
                                                  interaction_id=interaction_id)
        if close_session:
            await self.session_close_all(session_stream=session_stream)
            self.reader_task_cancel.set()
            self.reader_task_cancel_2.set()

            if global_stream:
                await self.global_stream_close(global_stream=global_stream)
                # self.global_stream_set.remove(global_stream)

            self.set_streams_sets_to_none()

            return

        return

    async def audio_pull_all(self, session_stream, audio_id: str, audio_channel: int = None, audio_start: int = None,
                             audio_length: int = None, correlation_id: str = None) -> bytes:
        final_audio_data: bytes = b''
        final_data_chunk = False

        while not final_data_chunk:
            await self.session_audio_pull(session_stream=session_stream, audio_id=audio_id,
                                          correlation_id=correlation_id,
                                          audio_channel=audio_channel, audio_start=audio_start,
                                          audio_length=audio_length)
            r = await self.get_session_general_response(session_stream=session_stream, wait=3)
            if not r:
                return b''
            final_audio_data += r.audio_pull.audio_data
            final_data_chunk = r.audio_pull.final_data_chunk  # will return True if no more audio is detected

        return final_audio_data

    # @staticmethod
    # def get_header(deployment_id=deploymentid,
    #                operator_id=operatorid,
    #                scopes=None,
    #                correlation_id=None):
    #     # Changed to allow an optional correlation_id to be specified for the call.
    #     # If it is not specified, it will not be added to the headers passed
    #
    #     headers = ()  # Create empty tuple to begin with
    #
    #     # Note: odd syntax below is how to insert into a tuple (don't change it unless you know what you're doing)
    #     if deployment_id is not None:
    #         headers += (("x-deployment-id", str(deployment_id)),)
    #     if operator_id is not None:
    #         headers += (("x-operator-id", str(operator_id)),)
    #     if correlation_id is not None:
    #         headers += (("x-correlation-id", str(correlation_id)),)
    #     if scopes is not None:
    #         headers += (("x-scopes", str(scopes)),)
    #
    #     return headers

    def get_grpc_channel_for_service(self, service_name, max_message_mb=4, is_async=False):

        service_address_and_port = LUMENVOX_API_SERVICE
        target_host = LUMENVOX_API_SERVICE

        use_tls = False
        if ENABLE_TLS == True:
            use_tls = True

        # Initialize and return the channel (using defined service endpoint)
        if use_tls:
            with open('./server.crt', 'rb') as f:
                credentials = grpc.ssl_channel_credentials(root_certificates=f.read())
            self.channel = grpc.secure_channel(LUMENVOX_API_SERVICE, credentials=credentials)

            service_address_and_port = target_host + ':443'

            return grpc.secure_channel(service_address_and_port,
                                       options=[
                                           ('grpc.max_send_message_length', max_message_mb * 1048576),
                                           ('grpc.max_receive_message_length', max_message_mb * 1048576)
                                       ], credentials=credentials) if not is_async else \
                grpc.aio.secure_channel(service_address_and_port,
                                        options=[
                                            ('grpc.max_send_message_length', max_message_mb * 1048576),
                                            ('grpc.max_receive_message_length', max_message_mb * 1048576)
                                        ], credentials=credentials)
        else:
            if service_name == 'lumenvox_api_service':
                service_address_and_port = target_host + ':8280'

            return grpc.insecure_channel(service_address_and_port,
                                         options=[
                                             ('grpc.max_send_message_length', max_message_mb * 1048576),
                                             ('grpc.max_receive_message_length', max_message_mb * 1048576),
                                         ]) if not is_async else \
                grpc.aio.insecure_channel(service_address_and_port,
                                          options=[
                                              ('grpc.max_send_message_length', max_message_mb * 1048576),
                                              ('grpc.max_receive_message_length', max_message_mb * 1048576),
                                          ])

    def get_audio_file(self, filename) -> bytes:
        """
        Reads the specified audio file from disc and returns the data
        :param filename:
        :return: bytes from file
        """

        if os.path.isfile(filename):
            # Running from test folder
            audio_file_path = filename
        else:
            # Running from command line in parent folder (remove first .)
            audio_file_path = filename[1:]

        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        return audio_data

    def get_grammar_file_by_ref(self, grammar_reference) -> str:
        """
        Opens the referenced grammar file and returns the contents as a string

        :param grammar_reference: string reference to grammar
        :return: string containing grammar
        """

        if os.path.isfile(grammar_reference):
            # Running from test folder
            grammar_file_path = grammar_reference
        else:
            # Running from command line in parent folder (remove first .)
            grammar_file_path = grammar_reference[1:]

        # self.assertTrue(os.path.isfile(grammar_file_path), "Referenced grammar file not found!")

        # Read as UTF-8 by default
        with open(grammar_file_path, 'r', encoding='utf-8') as file:
            data = file.read()

        # Handle ISO-8859-1 encoded grammars...
        if 'iso-8859-1' in data[:70].lower():
            with open(grammar_file_path, 'r', encoding='iso-8859-1') as file:
                data = file.read()
        return data

    def define_transcription_phrase_list(self, phrases: list = None,
                                         global_phrase_list: str = None,
                                         session_phrase_list: str = None) -> interaction_msg.TranscriptionPhraseList:
        """
        Construct a TrasncriptionPhraseList message (interaction.proto)
        :param phrases: Optional list of strings containing words and phrases "hints"
        :param global_phrase_list: Optional reference to previously defined global phrase list(s) (common.proto)
        :param session_phrase_list: Optional reference to previously defined session phrase list(s) (common.proto)
        :return: TranscriptionPhraseList
        """
        transcription_phrase_list = interaction_msg.TranscriptionPhraseList(
            phrases=phrases  # ,
            # global_phrase_list=common_msg.PhraseList(phrase_list_label=global_phrase_list),
            # session_phrase_list=common_msg.PhraseList(phrase_list_label=session_phrase_list)
        )

        return transcription_phrase_list

    def load_audio_buffer(self, filename, chunk_bytes) -> AudioBuffer:
        """
        Reads the specified audio file from disk into an AudioBuffer object and returns it

        :param chunk_bytes: number of bytes per chunk to stream
        :param filename:
        :return: bytes from file
        """

        if os.path.isfile(filename):
            # Running from test folder
            audio_file_path = filename
        else:
            # Running from command line in parent folder (remove first .)
            audio_file_path = filename[1:]

        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        audio_buffer = AudioBuffer(audio_data=audio_data, chunk_bytes=chunk_bytes)
        return audio_buffer

    def create_audio_file(self, session_id, byte_array, file_type=".wav", append='') -> str:
        """
        Creates a File and stored the specified audio data within
        :param session_id: session_id string, which is used in the generated filename
        :param append: name to append before session_id
        :param byte_array: raw audio to be stored in the file
        :param file_type: file suffix indicating the type of file, i.e. .ulaw, .alaw, .pcm, etc.
        :return: Filename generated including relative path
        """

        if append:
            append += '_'

        if os.path.isfile('lumenvox_helper_function.py'):
            output_path = 'created_data/'  # Running from test folder
            # print('########### running on ide')
        else:
            output_path = 'created_data/'  # Running from command line in parent folder
            # print('########### running on cli')
        output_filename = output_path + session_id + file_type
        if os.path.isfile(output_filename):
            output_filename = output_path + session_id + '-1' + file_type
        with open(output_filename, mode='bx') as f:
            f.write(byte_array)

        return output_filename

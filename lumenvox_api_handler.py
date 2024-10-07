""" LumenVox API Handling Code
This file serves to provide the essential tools to interact with the LumenVox API via Python.
Many of the methods found in the file wrap over the messages found in the protocol buffer files required to utilize the
API.
"""
import os.path
import queue
import asyncio
import uuid

import grpc

from enum import IntEnum

# common.proto messages
import lumenvox.api.common_pb2 as common_msg
# global.proto message
import lumenvox.api.global_pb2 as global_msg
# interaction.proto messages
import lumenvox.api.interaction_pb2 as interaction_msg
# session.proto messages
import lumenvox.api.session_pb2 as session_msg
# settings.proto messages
import lumenvox.api.settings_pb2 as settings_msg
# optional_values.proto messages
import lumenvox.api.optional_values_pb2 as optional_values
# LumenVox API protocol buffer messages and stub
from lumenvox.api.lumenvox_pb2_grpc import LumenVoxStub

from helpers import common_helper

# Import essential user connection data for gRPC/LumenVox API.
from lumenvox_api_user_connection_data import LUMENVOX_API_SERVICE_CONNECTION
from lumenvox_api_user_connection_data import ENABLE_TLS
from lumenvox_api_user_connection_data import CERT_FILE
from lumenvox_api_user_connection_data import deployment_id
from lumenvox_api_user_connection_data import operator_id


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


class LumenVoxApiClient:
    """ LumenVox API Client Handler Class

    A class strictly for core LumenVox api functions used by example code.
    Handles streams, requests, and message definitions. Many of the methods found in the file wrap over the messages
    found in the protocol buffer files required to utilize the API.
    Sample code of each type of interaction is in its own file.
    """

    session_stream_set = set()  # Store references to session streams.
    global_stream_set = set()  # Store references to global streams.
    queue_map = {}  # Map of session streams to queues.
    event_map = {}  # Map of session streams to events.
    session_id_map = {}  # Map of session streams to session IDs.
    session_id_queue = None
    stream_reader_task = None
    global_reader_task = None
    session_reader_task_cancel = asyncio.Event()
    global_reader_task_cancel = asyncio.Event()
    loop = None

    response_handler_queue = None  # Queue of callback ResponseHandler objects.

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_grpc_channel_for_service(max_message_mb=4, is_async=False):
        """
        Establish a gRPC channel. This process is required to obtain a stream with which the user can interact with the
        LumenVox API using the sample scripts provided in this project.
        :param max_message_mb: Maximum number of megabytes to allow for gRPC messages.
        :param is_async: Determines whether to use a gRPC channel for asyncio or not.
        :return: gRPC channel.
        """

        service_address_and_port = LUMENVOX_API_SERVICE_CONNECTION

        # Initialize and return the channel (using defined service endpoint)
        if ENABLE_TLS:
            with open(CERT_FILE, 'rb') as f:
                credentials = grpc.ssl_channel_credentials(root_certificates=f.read())

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

    async def create_channel_and_init_stream(self, stream_type: int = StreamType.STREAM_TYPE_SESSION):
        """
        Initializes gRPC channel and returns a newly created stream.
        The LumenVox API utilizes a bidirectional stream to perform user interactions. The stream created in this
        function is used to carry out the tasks seen in the sample files.

        The stream_type parameter will determine if a Session (0) or Global (1) stream is returned. The samples provided
        in this repository utilize the session stream.

        :return: A gRPC stream for bidirectional API functionality.
        """

        # A gRPC channel must first be established to reach the stub.
        grpc_channel = self.get_grpc_channel_for_service(is_async=True)
        # Python files generated from the protocol buffer files (such lumenvox_pb2_grpc.py) have stub with which the
        # user can access the functions of the API.
        stub = LumenVoxStub(channel=grpc_channel)

        # Depending on the type of stream desired, the Session() RPC (see lumenvox.proto) is called to receive a stream,
        # which will facilitate bidirectional interactivity between the user and the API.
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

    async def task_read_session_streams(self):
        """
        Iterates through set of session streams and process responses.
        """
        while not self.session_reader_task_cancel.is_set():
            if self.session_stream_set is None:
                return
            for stream in self.session_stream_set:
                # For each stream in the set, check for certain response types to put into their own queues.
                if 'terminated' not in str(stream):  # Don't attempt to read if the stream's been terminated.
                    r = await stream.read()
                    print(r)
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
                            print('>> task_read_session_streams: final_result received')
                            self.queue_map[stream].result_queue.put_nowait(r.final_result)
                            self.event_map[stream].result_event.set()
                        else:
                            self.queue_map[stream].general_response_queue.put_nowait(r)

            await asyncio.sleep(0)
        if self.session_reader_task_cancel.is_set():
            return

    async def task_read_global_streams(self):
        """
        Iterates through set of global streams and process responses.
        """
        while not self.global_reader_task_cancel.is_set():
            if self.global_stream_set is None:
                return
            for stream in self.global_stream_set:
                # For each stream in the set, check for certain response types to put into their own queues.
                if 'terminated' not in str(stream):  # Don't attempt to read if the stream's been terminated.
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
        if self.global_reader_task_cancel.is_set():
            return

    @staticmethod
    def empty_queue(q: asyncio.Queue):
        for _ in range(q.qsize()):
            q.get_nowait()
            q.task_done()

    def empty_all_stream_queues(self):
        """
        Empty all queues for session streams.
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
        Empty all queues for global streams.
        """
        if not self.global_stream_set:
            return

        for stream in self.global_stream_set:
            self.empty_queue(self.queue_map[stream].global_event_queue)
            self.empty_queue(self.queue_map[stream].global_settings_queue)

    def empty_all_queues(self):
        """
        Empty queues for both session and global streams.
        """
        self.empty_all_stream_queues()
        self.empty_global_queues()

        self.empty_queue(self.session_id_queue)
        self.empty_queue(self.response_handler_queue)

    @staticmethod
    async def get_from_queue(aio_queue: asyncio.Queue, wait: int):
        """
        Retrieves an item from a queue.
        """
        try:
            if not wait:
                return aio_queue.get_nowait()
            else:
                try:
                    return await asyncio.wait_for(aio_queue.get(), wait)
                except asyncio.TimeoutError:
                    # asyncio.wait_for will raise a TimeoutError if it doesn't retrieve anything in the specified time,
                    # but here we'll just return None and handle the case within the tests.
                    return None
        # The following will except errors thrown by queues if an attempt has been made to retrieve an item from the
        # queue when its empty. In these cases, just return None.
        except queue.Empty:
            return None
        except asyncio.QueueEmpty:
            return None

    async def get_session_general_response(self, session_stream, wait: int = 3):
        """
        Given session stream, attempt to receive a general (non-notification) response from the respective queue.
        """
        if session_stream not in self.queue_map:
            return None

        return await self.get_from_queue(aio_queue=self.queue_map[session_stream].general_response_queue, wait=wait)

    async def get_session_partial_result(self, session_stream, wait: int = 3):
        """
        Retrieve the final result response of the given session stream if available; otherwise, return None.
        """
        if session_stream not in self.queue_map:
            return None

        return await self.get_from_queue(aio_queue=self.queue_map[session_stream].partial_result_queue, wait=wait)

    async def get_session_final_result(self, session_stream, wait: int = 3):
        """
        Retrieve the final result response of the given session stream if available; otherwise, return None.
        """
        if session_stream not in self.queue_map:
            return None

        return await self.get_from_queue(aio_queue=self.queue_map[session_stream].result_queue, wait=wait)

    async def set_session_stream_for_reader_task(self, session_stream):
        """
        Add session stream to set so that it can be read from response-reading task.
        """
        self.session_stream_set.add(session_stream)

    async def set_global_stream_for_reader_task(self, global_stream):
        """
        Add global stream to set so that it can be read from response-reading task.
        """
        self.global_stream_set.add(global_stream)

    def set_streams_sets_to_none(self):
        """
        Set both session and global stream sets to None (to quit response handling flags).
        """
        self.session_stream_set = None
        self.global_stream_set = None

    def run_user_coroutine(self, user_coroutine) -> tuple:
        """
        The Lumenvox gRPC API works with asynchronous messages in both directions.
        This function sets up the required event loop and message queues to support bidirectional functionality.
        The user supplied coroutine is the "task" to perform interactions with the LumenVox API.
        
        :param user_coroutine: The async-defined coroutine to run as the main task
        :return: Tuple of return values from tasks run in self.loop.run_until_complete.
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

        # Initialize events that can be used to cancel the stream reader tasks.
        # These events will need to be set (.set()) to cancel/kill the reader tasks.
        self.session_reader_task_cancel = asyncio.Event()
        self.global_reader_task_cancel = asyncio.Event()

        # Create reader tasks for both Session and Global streams.
        self.stream_reader_task = self.loop.create_task(self.task_read_session_streams())
        self.global_reader_task = self.loop.create_task(self.task_read_global_streams())

        # The task the user provides will be the 'main' task.
        main_task = self.loop.create_task(user_coroutine)
        # The main task and the reader tasks are collected to run all at once.
        tasks = asyncio.gather(main_task, self.stream_reader_task, self.global_reader_task)

        # Tasks collected into asyncio.gather and run in the loop will return their respective values inside a tuple.
        task_return_values: tuple = self.loop.run_until_complete(tasks)
        return task_return_values

    @staticmethod
    async def session_stream_write(session_stream, correlation_id: str = None,
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

        await session_stream.write(session_request)

    @staticmethod
    async def global_stream_write(global_stream,
                                  deployment_uuid: str, operator_uuid: str, correlation_id: str = None,
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
        Takes a global stream, correlation ID, deployment ID, operator ID and one of the 'oneof' message types.
        Sends the GlobalRequest message to the stream.

        Unlike session stream requests, deployment and operator IDs will have to be specified for each request that goes
        into the global stream.
        """

        correlation_id = optional_values.OptionalString(value=correlation_id if correlation_id else str(uuid.uuid4()))

        # initial parameter setup
        global_request = global_msg.GlobalRequest(correlation_id=correlation_id,
                                                  deployment_id=deployment_uuid,
                                                  operator_id=operator_uuid,
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

    @staticmethod
    async def session_stream_read(session_stream, timeout: float = 0.5) -> \
            session_msg.SessionResponse:
        """
        Retrieve SessionResponse from session stream with a timeout.
        Generally , trying to read() from a stream that doesn't have any new output will cause a hangup.
        asyncio.wait_for will wait for output to be provided, otherwise this will return None.

        :param session_stream: Session stream to read messages from.
        :param timeout: Tha maximum amount of time to allow for reading the session stream.
        """
        try:
            print('session_stream_read: Reading from Session stream with a timeout of', timeout)
            return await asyncio.wait_for(session_stream.read(), timeout=timeout)
        except asyncio.TimeoutError:
            print('session_stream_read: Timeout reached, returning nothing.')
            return None

    async def session_create(self, session_stream, session_id: str = None, deployment_uuid: str = deployment_id,
                             operator_uuid: str = operator_id, correlation_uuid: str = None):
        """
        Given a stream, it creates a new session and returns the ID of the new session.

        :param session_stream: A previously created stream to and from which we write and read messages.
        :param session_id: Unique UUID with which the created session will be referenced.
        :param deployment_uuid: Unique UUID of the deployment to use for the session. The default imported at the top
        of this file is used if not provided to this function.
        :param operator_uuid: Unique UUID required for API calls.The default imported at the top of this file is used
        if not provided to this function.
        :param correlation_uuid: Optional UUID can be used to track individual API calls.
        """
        # Custom optional_values defined in optional_values.proto need their 'value' field set specifically.
        session_id = optional_values.OptionalString(value=session_id) if session_id else None

        # Message setup.
        session_create_request = \
            session_msg.SessionCreateRequest(deployment_id=deployment_uuid,
                                             operator_id=operator_uuid,
                                             session_id=session_id)

        session_request_msg = session_msg.SessionRequestMessage(session_create=session_create_request)

        # write messages to stream
        print("session_create: Writing session request to stream.")
        await self.session_stream_write(session_stream=session_stream,
                                        session_request_msg=session_request_msg,
                                        correlation_id=correlation_uuid)

        await asyncio.sleep(0.1)

    async def session_close(self, session_stream, correlation_id: str = None):
        """
        Close Session given a stream.
        :param correlation_id: Optional UUID that can be used to track requests.
        :param session_stream: A previously created stream to and from which we write and read messages.
        """

        # Message setup.
        session_close_request = session_msg.SessionCloseRequest(**{})
        session_request_msg = session_msg.SessionRequestMessage(session_close=session_close_request)

        print("session_close: Writing session request to stream.")
        await self.session_stream_write(session_stream=session_stream,
                                        session_request_msg=session_request_msg,
                                        correlation_id=correlation_id)

    async def session_set_inbound_audio_format(self, session_stream, correlation_id: str = None,
                                               audio_format_msg = None):
        """
        Specify Audio Format to be used within the session. See audio_formats.proto for more information.
        Setting the inbound audio format is required for any interactions where audio is processed (ASR, AMD, CPA, and
        Transcription).
        :param correlation_id: Optional UUID that can be used to track requests.
        :param audio_format_msg: Audio format message (see audio_format.proto) to use for inbound audio.
        :param session_stream: Stream of the session to set the inbound audio format on.
        """
        session_inbound_audio_format_request = \
            session_msg.SessionInboundAudioFormatRequest(audio_format=audio_format_msg)

        session_request_msg = \
            session_msg.SessionRequestMessage(session_audio_format=session_inbound_audio_format_request)

        await self.session_stream_write(session_stream=session_stream,
                                        session_request_msg=session_request_msg,
                                        correlation_id=correlation_id)

    async def session_audio_push(self, session_stream, correlation_id: str = None, audio_data: bytes = None):
        """
        Wrapping over AudioPushRequest (common.proto).
        Takes audio_data as bytes and sends the data within a protobuf message over gRPC.
        :param session_stream: Stream of the session to send an AudioPush request to.
        :param audio_data: Bytes of audio data to send into the API with AudioPush.
        :param correlation_id: Optional UUID that can be used to track requests.
        """

        audio_push_request = common_msg.AudioPushRequest(audio_data=audio_data)
        audio_request_msg = common_msg.AudioRequestMessage(audio_push=audio_push_request)

        await self.session_stream_write(session_stream=session_stream,
                                        correlation_id=correlation_id,
                                        audio_request_msg=audio_request_msg)

    async def session_audio_pull(self, session_stream, audio_id: str, correlation_id: str = None,
                                 audio_channel: int = None, audio_start: int = None, audio_length: int = None):
        """
        Wrapping over AudioPullRequest (common.proto)
        Returns AudioPullResponse (which would contain bytes of audio data)

        :param correlation_id: Optional UUID value used to track requests.
        :param session_stream: gRPC stream in which to send an AudioRequest message for AudioPull.
        :param audio_id: ID of the audio requested (Note that this could be session_id to request the inbound audio
        resource).
        :param audio_channel: For multichannel audio, this is the channel number being referenced. Range is from 0 to N.
            Default channel 0 will be used if not specified.
        :param audio_start: Number of milliseconds from the beginning of the audio to return (default is from the
        beginning).
        :param audio_length: Maximum number of milliseconds to return. A zero value returns all available audio (from
        requested start point). Default is all audio, from the starting point.
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

    async def interaction_create_amd(self, session_stream, amd_settings: settings_msg.AmdSettings,
                                     audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                     vad_settings: settings_msg.VadSettings = None,
                                     general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                     correlation_id: str = None) -> interaction_msg.InteractionCreateAmdResponse:
        """
        Sends a request to the API to create an AMD interaction.
        :param session_stream: Stream of the session to the request to.
        :param amd_settings: Settings that affect AMD processing (see settings.proto).
        :param audio_consume_settings: Audio Consume settings (see settings.proto).
        :param vad_settings: VAD settings (see settings.proto).
        :param general_interaction_settings: General interaction settings (see settings.proto).
        :param correlation_id: Optional UUID that can be used to track requests.
        """

        interaction_create_amd_request = interaction_msg.InteractionCreateAmdRequest(
            amd_settings=amd_settings,
            audio_consume_settings=audio_consume_settings,
            vad_settings=vad_settings,
            general_interaction_settings=general_interaction_settings)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_amd=interaction_create_amd_request)

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_cpa(self, session_stream, cpa_settings: settings_msg.CpaSettings,
                                     audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                     vad_settings: settings_msg.VadSettings = None,
                                     general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                     correlation_id: str = None):
        """
        Sends a request to the API to create a CPA interaction.
        :param session_stream: Stream of the session to the request to.
        :param cpa_settings: Settings that affect CPA processing (see settings.proto).
        :param audio_consume_settings: Audio Consume settings (see settings.proto).
        :param vad_settings: VAD settings (see settings.proto).
        :param general_interaction_settings: General interaction settings (see settings.proto).
        :param correlation_id: Optional UUID that can be used to track requests.
        """
        interaction_create_cpa_request = interaction_msg.InteractionCreateCpaRequest(
            cpa_settings=cpa_settings,
            audio_consume_settings=audio_consume_settings,
            vad_settings=vad_settings,
            general_interaction_settings=general_interaction_settings)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_cpa=interaction_create_cpa_request)

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
        Sends a request to the API to create an ASR interaction.
        :param session_stream: Stream of the session to the request to.
        :param language: Language code to use for the interaction (ex. 'en-us').
        :param grammars: List of grammar messages (see common.proto) to use for ASR interaction.
        :param grammar_settings: Settings to apply to grammars (see settings.proto).
        :param recognition_settings: Recognition settings (see settings.proto).
        :param vad_settings: VAD settings (see settings.proto).
        :param audio_consume_settings: Audio Consume settings (see settings.proto).
        :param general_interaction_settings: General interaction settings (see settings.proto).
        :param correlation_id: Optional UUID that can be used to track requests.
        """

        interaction_create_asr_request = interaction_msg.InteractionCreateAsrRequest(
            language=language,
            grammars=grammars,
            grammar_settings=grammar_settings,
            recognition_settings=recognition_settings,
            vad_settings=vad_settings,
            audio_consume_settings=audio_consume_settings,
            general_interaction_settings=general_interaction_settings)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_asr=interaction_create_asr_request)

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_tts(self, session_stream, audio_format = None, language: str = None,
                                     inline_text: str = None,
                                     tts_inline_synthesis_settings: settings_msg.TtsInlineSynthesisSettings = None,
                                     ssml_url: str = None, ssl_verify_peer: bool = True,
                                     synthesis_timeout_ms: int = 5000,
                                     general_interaction_settings: settings_msg.GeneralInteractionSettings = None,
                                     correlation_id: str = None):
        """
        Sends a request to the API to create a TTS interaction.
        :param session_stream: Stream of the session to the request to.
        :param audio_format: Audio format to use for synthesis audio output.
        :param language: Language code to use for the interaction (ex. 'en-us').
        :param inline_text: Inline text to synthesis.
        :param tts_inline_synthesis_settings: Settings to use for inline text (see settings.proto).
        :param ssml_url: URL reference for SSML.
        :param ssl_verify_peer: Determines whether to check for certificates upon using URL references.
        :param synthesis_timeout_ms: Maximum amount of time to use for synthesis.
        :param general_interaction_settings: General interaction settings (see settings.proto).
        :param correlation_id: Optional UUID that can be used to track requests.
        """
        interaction_create_tts_request = (
            interaction_msg.InteractionCreateTtsRequest(language=language,
                                                        audio_format=audio_format,
                                                        general_interaction_settings=general_interaction_settings))

        if inline_text:
            # setting message contents this way as the inline_request is a nested message
            interaction_create_tts_request.inline_request.text = inline_text

            # If provided, transfer the giving inline TTS settings into format proper for the interaction.
            if tts_inline_synthesis_settings:
                interaction_create_tts_request.inline_request.tts_inline_synthesis_settings.voice.value = \
                    tts_inline_synthesis_settings.voice.value

                (interaction_create_tts_request.inline_request.
                 tts_inline_synthesis_settings.synth_emphasis_level).value = \
                    tts_inline_synthesis_settings.synth_emphasis_level.value

                (interaction_create_tts_request.inline_request.
                 tts_inline_synthesis_settings.synth_prosody_pitch).value = \
                    tts_inline_synthesis_settings.synth_prosody_pitch.value

                (interaction_create_tts_request.inline_request.
                 tts_inline_synthesis_settings.synth_prosody_contour).value = \
                    tts_inline_synthesis_settings.synth_prosody_contour.value

                (interaction_create_tts_request.inline_request.
                 tts_inline_synthesis_settings.synth_prosody_rate).value = \
                    tts_inline_synthesis_settings.synth_prosody_rate.value

                (interaction_create_tts_request.inline_request.
                 tts_inline_synthesis_settings.synth_prosody_duration).value = \
                    tts_inline_synthesis_settings.synth_prosody_duration.value

                (interaction_create_tts_request.inline_request.
                 tts_inline_synthesis_settings.synth_prosody_volume).value = \
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
            interaction_create_tts=interaction_create_tts_request)

        await self.session_stream_write(session_stream=session_stream, interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_transcription(self, session_stream, language: str, phrases: list = None,
                                               continuous_utterance_transcription: bool = False,
                                               recognition_settings: settings_msg.RecognitionSettings = None,
                                               vad_settings: settings_msg.VadSettings = None,
                                               audio_consume_settings: settings_msg.AudioConsumeSettings = None,
                                               normalization_settings: settings_msg.NormalizationSettings = None,
                                               phrase_list_settings: settings_msg.PhraseListSettings = None,
                                               general_interaction_settings:
                                               settings_msg.GeneralInteractionSettings = None,
                                               enable_postprocessing: str = None,
                                               language_model_name: str = None,
                                               acoustic_model_name: str = None,
                                               embedded_grammars: list = None, correlation_id: str = None):
        """
        Sends a request to the API to create a Transcription interaction.
        :param enable_postprocessing: Optional custom postprocessing to enhance decoder functionality.
        :param language_model_name: Optional custom language model.
        :param acoustic_model_name: Optional custom acoustic model.
        :param session_stream: Stream of the session to the request to.
        :param language: Language code to use for the interaction (ex. 'en-us').
        :param phrases: List of TranscriptionPhraseList messages (see interaction.proto).
        :param continuous_utterance_transcription: Enables continuous utterance transcription (multiple final results).
        :param recognition_settings: Recognition settings (see settings.proto).
        :param vad_settings: VAD settings (see settings.proto).
        :param audio_consume_settings: Audio Consume settings (see settings.proto).
        :param normalization_settings: Settings to use for normalization (see settings.proto).
        :param phrase_list_settings: Settings for phrase lists, if used (see settings.proto).
        :param general_interaction_settings: General interaction settings (see settings.proto).
        :param embedded_grammars: List of grammar messages (see common.proto). Their inclusion enables enhanced 
        transcription.
        :param correlation_id: Optional UUID that can be used to track requests.
        """
        interaction_create_transcription_request = interaction_msg.InteractionCreateTranscriptionRequest(
            language=language,
            phrases=phrases,
            phrase_list_settings=phrase_list_settings,
            continuous_utterance_transcription=
            common_helper.optional_bool(continuous_utterance_transcription),
            recognition_settings=recognition_settings,
            vad_settings=vad_settings,
            audio_consume_settings=audio_consume_settings,
            normalization_settings=normalization_settings,
            general_interaction_settings=general_interaction_settings,
            embedded_grammars=embedded_grammars,
            language_model_name=common_helper.optional_string(language_model_name),
            acoustic_model_name=common_helper.optional_string(acoustic_model_name),
            enable_postprocessing=common_helper.optional_string(enable_postprocessing))

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_transcription=interaction_create_transcription_request)

        await self.session_stream_write(session_stream=session_stream, interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_normalize_text(self, session_stream, language: str, transcript: str,
                                                normalization_settings: settings_msg.NormalizationSettings = None,
                                                general_interaction_settings:
                                                settings_msg.GeneralInteractionSettings = None,
                                                correlation_id: str = None):
        """
        Sends a request to the API to create a NormalizeText interaction.
        :param session_stream: Stream of the session to the request to and to create an interaction on.
        :param language: Language code to use for the interaction (ex. 'en-us').
        :param transcript: Text to use for normalization.
        :param normalization_settings: Settings to use for normalization (see settings.proto).
        :param general_interaction_settings: General interaction settings (see settings.proto).
        :param correlation_id: Optional UUID that can be used to track requests.
        """

        interaction_create_normalize_text_request = \
            interaction_msg.InteractionCreateNormalizeTextRequest(
                language=language, transcript=transcript, normalization_settings=normalization_settings,
                general_interaction_settings=general_interaction_settings)

        interaction_request_msg = \
            interaction_msg.InteractionRequestMessage(
                interaction_create_normalize_text=interaction_create_normalize_text_request)

        await self.session_stream_write(session_stream=session_stream, interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_create_grammar_parse(self, session_stream, language: str, grammars: list, input_text: str,
                                               grammar_settings: settings_msg.GrammarSettings = None,
                                               general_interaction_settings:
                                               settings_msg.GeneralInteractionSettings = None,
                                               parse_timeout_ms: int = None, correlation_id: str = None):
        """
        Sends a request to the API to create a GrammarParse interaction.
        :param session_stream: Stream of the session to the request to and to create an interaction on.
        :param language: Language code to use for the interaction (ex. 'en-us').
        :param grammars: List of grammar messages (see common.proto) to use in the interaction.
        :param input_text: Text to parse from the provided grammars. 
        :param grammar_settings: Grammar settings to use for the interaction (see settings.proto).
        :param general_interaction_settings: General interaction settings (see settings.proto).
        :param parse_timeout_ms: Maximum amount of time to allow for parsing.
        :param correlation_id: Optional UUID that can be used to track requests.
        """

        interaction_create_grammar_parse_request = interaction_msg.InteractionCreateGrammarParseRequest(
            language=language,
            grammars=grammars,
            grammar_settings=grammar_settings,
            input_text=input_text,
            parse_timeout_ms=common_helper.optional_int32(parse_timeout_ms) if parse_timeout_ms else None,
            general_interaction_settings=general_interaction_settings)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_create_grammar_parse=interaction_create_grammar_parse_request)

        await self.session_stream_write(session_stream=session_stream, interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_begin_processing(self, session_stream, interaction_id: str, correlation_id: str = None):
        """
        Sends a request to the API for InteractionBeginProcessing.
        :param session_stream: Stream of the session to the request to.
        :param interaction_id: UUID of the interaction to process.
        :param correlation_id: Optional UUID that can be used to track requests.
        """
        interaction_begin_processing_request = \
            interaction_msg.InteractionBeginProcessingRequest(interaction_id=interaction_id)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_begin_processing=interaction_begin_processing_request)

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_finalize_processing(self, session_stream, interaction_id: str, correlation_id: str = None):
        """
        Sends a request to the API to handle InteractionFinalizeProcessing.
        :param session_stream: Stream of the session to the request to.
        :param interaction_id: UUID of the interaction to request results from.
        :param correlation_id: Optional UUID that can be used to track requests.
        """

        interaction_finalize_processing_request = \
            interaction_msg.InteractionFinalizeProcessingRequest(interaction_id=interaction_id)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_finalize_processing=interaction_finalize_processing_request)

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_request_results(self, session_stream, interaction_id: str, correlation_id: str = None):
        """
        Handle InteractionRequestResults (interaction.proto)
        Returns InteractionRequestResultsResponse
        """

        interaction_request_results_request = \
            interaction_msg.InteractionRequestResultsRequest(interaction_id=interaction_id)

        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_request_results=interaction_request_results_request)

        await self.session_stream_write(session_stream=session_stream,
                                        interaction_request_msg=interaction_request_msg,
                                        correlation_id=correlation_id)

    async def interaction_close(self, session_stream, interaction_id: str, correlation_id: str = None):
        """
        Sends a request to the API for InteractionClose.
        :param session_stream: Stream of the session to the request to.
        :param interaction_id: UUID of the interaction to close.
        :param correlation_id: Optional UUID that can be used to track requests.
        """
        interaction_close_request = interaction_msg.InteractionCloseRequest(interaction_id=interaction_id)
        interaction_request_msg = interaction_msg.InteractionRequestMessage(
            interaction_close=interaction_close_request)

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

    async def session_init(self, session_id: str = None, deployment_uuid: str = None, operator_uuid: str = None,
                           correlation_uuid: str = None):
        """
        Helper function to create a session and provide both the session stream and ID.
        :param session_id: A UUID value to use as the session ID upon creation.
        :param deployment_uuid: Unique UUID of the deployment to use for the session.
        :param operator_uuid: Optional unique UUID can be used to track who is making API calls.
        :param correlation_uuid: Optional UUID can be used to track individual API calls.
        :return: Returns both the session_stream and session ID.
        """
        session_stream = await self.create_channel_and_init_stream()
        self.init_session_stream_maps(session_stream)
        await self.set_session_stream_for_reader_task(session_stream=session_stream)

        if session_id:
            await self.session_create(session_stream=session_stream, session_id=session_id,
                                      deployment_uuid=deployment_uuid, operator_uuid=operator_uuid,
                                      correlation_uuid=correlation_uuid)
        else:
            await self.session_create(session_stream=session_stream, deployment_uuid=deployment_uuid,
                                      operator_uuid=operator_uuid, correlation_uuid=correlation_uuid)

        session_id = await self.session_id_queue.get()
        if session_id:
            print("session_id from session_create:", session_id)

        return session_stream, session_id

    async def session_close_all(self, session_stream):
        """
        Helper function to handle closing session and stream. Check that SessionClose returns a proper status code (0).
        :param session_stream: Stream of the session to close.
        """
        await self.session_close(session_stream=session_stream)
        session_close_response = await self.get_session_general_response(session_stream=session_stream, wait=3)

        print("SessionClose response message:\n", session_close_response)

        await session_stream.done_writing()

    @staticmethod
    async def global_stream_close(global_stream):
        await global_stream.done_writing()

    async def audio_pull_all(self, session_stream, audio_id: str, audio_channel: int = None, audio_start: int = None,
                             audio_length: int = None, correlation_id: str = None) -> bytes:
        """
        Function to call SessionAudioPull to until all audio has been received. Mainly used for TTS interactions.
        :param session_stream: gRPC stream of the session to pull audio from.
        :param audio_id: Audio ID. For TTS interactions, this is the interaction ID.
        :param audio_channel: Optional. Audio channel to pull from.
        :param audio_start: Optional. Start time of the audio (ms).
        :param audio_length: Optional. Maximum audio length (ms).
        :param correlation_id: Optional. Correlation ID.
        :return: Bytes of audio data.
        """
        final_audio_data: bytes = b''
        final_data_chunk = False

        # Use a while loop to send AudioPull requests. If all the audio has been received, the loop is broken.
        while not final_data_chunk:
            await self.session_audio_pull(session_stream=session_stream, audio_id=audio_id,
                                          correlation_id=correlation_id,
                                          audio_channel=audio_channel, audio_start=audio_start,
                                          audio_length=audio_length)
            r = await self.get_session_general_response(session_stream=session_stream, wait=3)
            if not r:
                return b''
            final_audio_data += r.audio_pull.audio_data
            final_data_chunk = r.audio_pull.final_data_chunk  # Will return True if no more audio is detected.

        return final_audio_data

    def kill_stream_reader_tasks(self):
        """
        Use this function to kill the stream-reading asyncio tasks, so they won't continue after all other functions.
        """
        self.session_reader_task_cancel.set()
        self.global_reader_task_cancel.set()

    async def get_streaming_response(self, session_stream, audio_push_finish_event: asyncio.Event, wait: int = 5):
        """
        Some interactions, such as ASR, Transcription, AMD, and CPA may call for waiting for a final result message to
        be received from the API while audio is being streamed/processed.
        This function runs a loop while audio_push_finish_event is not set to check for the final result message.
        :param session_stream: Stream of the session to receive a final result message from.
        :param audio_push_finish_event: An event that is set when audio is done being sent.
        :param wait: Time to wait for final response message for each loop iteration.
        :return: Final result message. None if not received.
        """
        final_result = None

        # Run a loop to check for final result while the audio is being pushed.
        while not audio_push_finish_event.is_set():
            # Check for final result while this loop runs.
            # This next call will return None if the final result is not ready yet.
            final_result = await self.get_session_final_result(session_stream=session_stream, wait=wait)

            # Break this loop if we get the final result.
            if final_result:
                break

            await asyncio.sleep(0.0)  # Use this sleep to enable an asyncio loop.

        return final_result

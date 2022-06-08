import asyncio
import grpc
import os
import queue
import threading
import time
import typing
from concurrent.futures import ThreadPoolExecutor

from lumenvox.api.speech.v1 import speech_pb2 as speech_api
from lumenvox.api.speech.v1.speech_pb2_grpc import SpeechAPIServiceStub

# Define your target machine here
LUMENVOX_SPEECH_API_SERVICE = 'speech-api.testmachine.com:443'

# Use this to enable TLS connectivity to your service
ENABLE_TLS = True

# This should be changed to match the deployment_id assigned to your system
DEPLOYMENT_ID = "d80b9d9b-086f-42f0-a728-d95f39dc2229"

# Operator is used to identify the person or machine making API requests from an audit and debugging perspective
OPERATOR_ID = "a69c7ee5-ac2d-40c2-9524-8fb0f5e5e7fd"

# This is used to specify the maximum message length handled by GRPC (do not change unless you understand impact)
MAX_GRPC_MESSAGE_MB = 4


class CallbackQueues:
    def __init__(self):
        self.vad_queue = queue.SimpleQueue()
        self.result_queue = queue.SimpleQueue()
        self.partial_result_queue = queue.SimpleQueue()


class NotificationEvents:
    def __init__(self):
        self.result_event = threading.Event()
        self.partial_result_event = threading.Event()


class ResponseHandler:
    def __init__(self, session_callback_stream):
        self.session_callback_stream = session_callback_stream
        self.callback_loop = asyncio.get_event_loop()


class AudioStreamBuffer:
    def __init__(self, audio_data, stream_chunk_bytes=200):
        # This audio_data buffer assigned during constructor can be referenced later
        self.audio_data = audio_data

        # During creation, users can specify a different chunk size, or use the default
        self.stream_chunk_bytes = stream_chunk_bytes

        self.read_location = 0
        self.bytes_remaining = 0
        self.total_audio_bytes = len(audio_data)

    def get_next_chunk(self):
        self.bytes_remaining = self.total_audio_bytes - self.read_location
        if self.bytes_remaining < 0:
            self.bytes_remaining = 0
        if self.bytes_remaining > 0:
            if self.bytes_remaining >= self.stream_chunk_bytes:
                bytes_to_stream = self.stream_chunk_bytes
            else:
                bytes_to_stream = self.bytes_remaining

            result_chunk = self.audio_data[self.read_location:self.read_location + bytes_to_stream]
            self.read_location += bytes_to_stream
            return result_chunk
        else:
            return None


class LumenVoxSpeechApiHelper:

    queue_map = {}  # Map of session_id to queues
    event_map = {}  # Map of session_id to events
    executor = None
    response_handler_queue = queue.SimpleQueue()  # Queue of callback ResponseHandler objects
    cancel_event = None
    session_id_queue = None
    last_error_details = None
    last_error_code = None

    def __init__(self):
        self.stub = None
        self.channel = None
        self.grammar_endpoint = None
        self.certs_path_suffix = ''
        self.machine_section = None
        self._peer_responded = None
        self.result_ready = False
        self.results_response = None

    def initialize_speech_api_helper(self):
        # Initialize the channel and stub (using defined service endpoint)
        if ENABLE_TLS:
            with open('./server.crt', 'rb') as f:
                credentials = grpc.ssl_channel_credentials(root_certificates=f.read())
            self.channel = grpc.secure_channel(LUMENVOX_SPEECH_API_SERVICE, credentials=credentials)
        else:
            self.channel = grpc.insecure_channel(LUMENVOX_SPEECH_API_SERVICE,
                                                 options=[
                                                     ('grpc.max_send_message_length', MAX_GRPC_MESSAGE_MB * 1048576),
                                                     ('grpc.max_receive_message_length', MAX_GRPC_MESSAGE_MB * 1048576),
                                                 ])
        self.stub = SpeechAPIServiceStub(self.channel)

        # Initialize threading
        self._peer_responded = threading.Event()
        self.executor = ThreadPoolExecutor()
        self.cancel_event = threading.Event()

        self.session_id_queue = queue.SimpleQueue()

    def shutdown_speech_api_helper(self):
        self.cancel_event.set()
        self.executor.shutdown(wait=False)

        # iterate through all response handlers and stop their loops and streams
        while self.response_handler_queue.qsize():
            response_handler = typing.cast(ResponseHandler, self.response_handler_queue.get())
            response_handler.callback_loop.stop()
            response_handler.session_callback_stream.cancel()  # Cancel the stream

    def add_to_callback_loop(self, session_callback_stream) -> None:
        """
        Adds a new thread/loop for specified session_callback_stream

        :param session_callback_stream: the stream that will receive callbacks
        :return: Nothing
        """
        new_response_handler = ResponseHandler(session_callback_stream=session_callback_stream)
        new_response_handler.callback_loop = asyncio.get_event_loop()
        new_response_handler.callback_loop.run_in_executor(self.executor, self.response_handler, session_callback_stream, self.cancel_event)
        self.response_handler_queue.put(new_response_handler)

    def audio_streamer(self, session_id, audio_streaming_buffer, cancel_event):
        """
        Returns an iterator which can be used to stream the given audio.

        :param session_id: The session id, sent as the first message in the iterator.
        :param audio_streaming_buffer: The buffer object containing the audio to be streamed.
        :param cancel_event: Threading event which can be used to cancel the stream early.
        """
        # The first message in the stream should be the session id. After sending this, continue to the data.
        yield speech_api.AudioStreamRequest(**{"session_id": session_id})

        chunk_counter = 0
        while True:
            time.sleep(0.1)
            if cancel_event.is_set():
                break
            data = audio_streaming_buffer.get_next_chunk()
            if data is None:
                # End of file reached - end the stream
                break
            else:
                chunk_counter += 1
                print(f"sending audio chunk {chunk_counter}")
                yield speech_api.AudioStreamRequest(**{"audio_data": data})

    def stream_audio(self, session_id, audio_streaming_buffer, cancel_event):
        # Create iterator for streaming the audio
        streamer = self.audio_streamer(session_id, audio_streaming_buffer, cancel_event)

        # Stream the audio
        self.stub.AudioStream(streamer, metadata=self.get_header())

    @staticmethod
    def get_header(deployment_id=DEPLOYMENT_ID,
                   operator_id=OPERATOR_ID) -> tuple:
        # Pass no parameters to use the constant values defined at top of file, or specify alternates to use
        # This is used when sending requests to the API and holds metadata in addition to the actual request
        return (
            ("x-deployment-id", str(deployment_id)),
            ("x-operator-id", str(operator_id))
        )

    def response_handler(self, listener: speech_api.SessionCreateResponse, cancel: threading.Event):
        try:
            for response in listener:
                callback_type = response.WhichOneof("response")

                if callback_type == "session_id":
                    print('>> session_id in response_handler: ', response.session_id)
                    self.session_id_queue.put(response.session_id)

                elif callback_type == "vad_event":
                    print('>> VAD CALLBACK in response_handler')
                    session_id_from_response = response.vad_event.session_id
                    if session_id_from_response in self.queue_map:
                        self.queue_map[session_id_from_response].vad_queue.put(response.vad_event)

                elif callback_type == "final_result":
                    print('>> RESULT CALLBACK in response_handler')
                    session_id_from_response = response.final_result.session_id
                    if session_id_from_response in self.queue_map:
                        self.queue_map[session_id_from_response].result_queue.put(response.final_result)
                        self.event_map[session_id_from_response].result_event.set()

                elif callback_type == "partial_result":
                    print('>> PARTIAL RESULT CALLBACK in response_handler')
                    session_id_from_response = response.partial_result.session_id
                    if session_id_from_response in self.queue_map:
                        self.queue_map[session_id_from_response].partial_result_queue.put(response.partial_result)
                        self.event_map[session_id_from_response].partial_result_event.set()
                else:
                    raise RuntimeError(
                        "Received SessionCreateResponse without expected type"
                    )

                if cancel.is_set():
                    return

        except Exception as e:
            self._peer_responded.set()
            raise

    def get_vad_callback(self, session_id, timeout_value):
        try:
            if session_id in self.queue_map:
                if timeout_value == 0:
                    return self.queue_map[session_id].vad_queue.get_nowait()
                else:
                    return self.queue_map[session_id].vad_queue.get(timeout=timeout_value)
            else:
                return None
        except queue.Empty as e:
            # Handle empty queue here
            return None

    def get_result_callback(self, session_id, timeout_value):
        try:
            if session_id in self.queue_map:
                if timeout_value == 0:
                    return self.queue_map[session_id].result_queue.get_nowait()
                else:
                    return self.queue_map[session_id].result_queue.get(timeout=timeout_value)
            else:
                return None
        except queue.Empty as e:
            # Handle empty queue here (no callback received)
            return None

    def get_partial_result_callback(self, session_id, timeout_value):
        try:
            if session_id in self.queue_map:
                if timeout_value == 0:
                    return self.queue_map[session_id].partial_result_queue.get_nowait()
                else:
                    return self.queue_map[session_id].partial_result_queue.get(timeout=timeout_value)
            else:
                return None
        except queue.Empty as e:
            # Handle empty queue here (no callback received)
            return None

    # ----------------------------------

    def SessionCreate(self, audio_format=None) -> typing.Union[str, None]:
        """
        Call SessionStart return valid session_id (uuid)
        """
        metadata = self.get_header()

        params = {
            "audio_format": {
                "standard_audio_format": audio_format
            }
        }

        # Create session and a reference to the stream object returned (which will receive callbacks)
        session_callback_stream = self.stub.SessionCreate(speech_api.SessionCreateRequest(**params), metadata=metadata)

        # Add the new session_callback_stream to a ResponseHandler and start a loop listening to it
        self.add_to_callback_loop(session_callback_stream=session_callback_stream)

        # Wait for the next entry in the session_id_queue (the first one sent back from the server)
        session_id = self.session_id_queue.get(timeout=2)

        self.queue_map[session_id] = CallbackQueues()
        self.event_map[session_id] = NotificationEvents()
        return session_id

    def SessionClose(self, session_id) -> None:
        """
        Closes the specified session

        :param session_id:
        :return: None
        """
        params = {
            "session_id": session_id
        }
        self.stub.SessionClose(speech_api.SessionCloseRequest(**params), metadata=self.get_header())

    def reset_result_event(self, session_id) -> None:
        """
        Resets the result_event for the specified session_id, allowing multiple results per session to be handled

        :param session_id: session_id of result_event to reset
        :return: None
        """
        self.event_map[session_id].result_event.clear()

    def wait_for_final_results(self, session_id, interaction_id, wait_time=3.5) -> bool:
        """
        Helper used to wait for a final results callback

        :param interaction_id: expected interaction_id
        :param session_id: expected session_id
        :param wait_time: number of seconds to wait for final_result event
        :return: True if final_result event received within specified timeout period
        """
        self.result_ready = False

        if self.event_map[session_id].result_event.wait(wait_time):
            if interaction_id:
                self.result_ready = self.InteractionRequestResults(session_id, interaction_id)
            else:
                return True

        return self.result_ready

    def reset_partial_result_event(self, session_id) -> None:
        """
        Resets the partial_result_event for the specified session_id, allowing multiple results per session to be
        handled

        :param session_id: session_id of partial_result_event to reset
        :return: None
        """
        self.event_map[session_id].partial_result_event.clear()

    def wait_for_partial_results(self, session_id, interaction_id, wait_time=5) -> bool:
        """
        Helper used to wait for a partial results callback

        :param interaction_id: expected interaction_id
        :param session_id: expected session_id
        :param wait_time: number of seconds to wait for partial_result event
        :return: True if partial_result event received within specified timeout period
        """
        self.result_ready = False

        if self.event_map[session_id].partial_result_event.wait(wait_time):
            self.result_ready = self.InteractionRequestResults(session_id, interaction_id)

        return self.result_ready

    def AudioStream(self, session_id) -> None:
        """
        Calls AudioStreamCreate passing the specified audio_format to create an inbound audio stream for ASR

        :param session_id: target session identifier
        :return: None
        """

        params = {
            "session_id": session_id,
        }
        self.stub.AudioStream((yield speech_api.AudioStreamRequest(**params)), metadata=self.get_header())

    def AudioPush(self, session_id, audio_data) -> None:
        """
        Used to push audio into the API

        :param session_id: target session identifier
        :param audio_data: bytes containing the audio to process (size automatically determined)
        :return: None
        """
        params = {
            "session_id": session_id,
            "audio_data": audio_data
        }
        self.stub.AudioPush(speech_api.AudioPushRequest(**params), metadata=self.get_header())

    def StartStreaming(self, session_id, audio_streaming_buffer, cancel_event):
        asyncio.get_event_loop().run_in_executor(self.executor, self.stream_audio, session_id, audio_streaming_buffer,
                                                 cancel_event)

    def AudioStreamingPush(self, session_id, audio_stream_buffer) -> bool:
        """
        Fetch and send the next chunk from the audio_stream_buffer

        :param session_id: session_id into which to send the audio
        :param audio_stream_buffer: buffer object to process
        :return: True if more data available to send in audio_stream_buffer, otherwise False
        """
        data = audio_stream_buffer.get_next_chunk()
        if data is None:
            # We've reached the end of the buffer, so nothing else to send.
            return False

        params = {
            "session_id": session_id,
            "stream_data": data
        }
        self.stub.AudioStreamPush(speech_api.AudioStreamPushRequest(**params), metadata=self.get_header())
        return True

    def AudioPull(self, interaction_id=None, session_id=None, audio_start=None, audio_length=None) -> typing.Any:
        """
        Call AudioPull to request audio from the API

        :param interaction_id: specified audio_id
        :param session_id: related session_id
        :param audio_start: optional start location
        :param audio_length: optional audio length to fetch
        :return: audio_data_len, audio_data
        """
        params = {
            "session_id": session_id,
            "audio_id": interaction_id,
        }
        if audio_start is not None:
            params["audio_start"] = audio_start
        if audio_length is not None:
            params["audio_length"] = audio_length

        response = self.stub.AudioPull(speech_api.AudioPullRequest(**params),
                                             metadata=self.get_header())

        audio_data_len = len(response.audio_data)
        return audio_data_len, response.audio_data

    def InteractionRequestResults(self, session_id=None, interaction_id=None) -> bool:
        """
        Call InteractionRequestResults, populate self.results_response and return True if results_ready

        :param session_id: specified session to query for results
        :param interaction_id: specified interaction to query for results
        :return: True if results are available
        """
        params = {
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        # storing the results in self.results_response so other routines can access the result data (if available)
        self.results_response = self.stub.InteractionRequestResults(
            speech_api.InteractionRequestResultsRequest(**params), metadata=self.get_header())

        self.result_ready = self.results_response.result_ready
        return self.results_response.result_ready

    def InteractionFinalizeProcessing(self, session_id=None, interaction_id=None) -> None:
        """
        InteractionFinalizeProcessing

        Used to force VAD complete when VAD is used, or after VAD speech begin.

        Takes all available stream audio and triggers an ASR decode. This
        is optional most of the time, when the default auto-decode setting is used.

        This can also be used when performing DTMF or Text type interactions

        Results for the interaction may be available during subsequent calls to
        InteractionRequestResults

        :param session_id: specified session
        :param interaction_id: the interaction to trigger finalize
        :return: None
        """
        params = {
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        self.stub.InteractionFinalizeProcessing(
            speech_api.InteractionFinalizeProcessingRequest(**params), metadata=self.get_header())

    def InteractionBeginProcessing(self, session_id=None, interaction_id=None) -> None:
        """
        Call InteractionBeginProcessing initiates processing of the specified interaction

        :param session_id: specified session_id
        :param interaction_id: interaction to begin processing
        :return: Nothing
        """
        params = {
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        self.stub.InteractionBeginProcessing(speech_api.InteractionBeginProcessingRequest(**params),
                                             metadata=self.get_header())

    def InteractionSetSettings(self, session_id, interaction_id, json_settings_string) -> None:
        """
        Call InteractionSetSettings to apply specified settings in interaction

        :param session_id: specified session_id
        :param interaction_id: interaction to apply settings
        :param json_settings_string: settings JSON string to apply to interaction
        :return: Nothing
        """
        params = {
            "session_id": session_id,
            "interaction_id": interaction_id,
            "json_settings": json_settings_string
        }
        self.stub.InteractionSetSettings(speech_api.InteractionSetSettingsRequest(**params),
                                         metadata=self.get_header())

    def InteractionGetSettings(self, session_id, interaction_id) -> str:
        """
        Call InteractionGetSettings to return JSON string containing interaction settings

        :param session_id: specified session_id
        :param interaction_id: interaction to return settings from
        :return: String containing JSON result
        """
        params = {
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        response = self.stub.InteractionGetSettings(speech_api.InteractionGetSettingsRequest(**params),
                                                    metadata=self.get_header())
        return response.json_settings

    def InteractionCancel(self, session_id=None, interaction_id=None) -> None:
        """
        Cancels the specified interaction

        :param session_id: specified session_id
        :param interaction_id: interaction to cancel
        :return: None
        """
        params = {
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        self.stub.InteractionCancel(speech_api.InteractionCancelRequest(**params), metadata=self.get_header())

    def InteractionClose(self, session_id=None, interaction_id=None) -> None:
        """
        Closes the specified interaction

        :param session_id: specified session
        :param interaction_id: interaction to close
        :return: None
        """
        params = {
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        self.stub.InteractionClose(speech_api.InteractionCloseRequest(**params), metadata=self.get_header())

    def InteractionCreateGrammarLoad(self, session_id, language_code, inline_grammar_text=None, grammar_url=None):
        """
        Creates an interaction to load the specified grammar (optional inline text or URL)

        :param session_id: selected session to associate the new interation with
        :param language_code: language of the specified grammar (i.e. 'en', 'fr', 'de', etc.)
        :param inline_grammar_text: string containing complete grammar
        :param grammar_url: location of grammar to load. This should be reachable by the system
        :return: interaction_id - this is described as grammar_id and can be passed to InteractionCreateASR etc.
        """
        params = {
            "session_id": session_id,
            "language": language_code,
        }
        if inline_grammar_text:
            params['inline_grammar_text'] = inline_grammar_text
        if grammar_url:
            params['grammar_url'] = grammar_url
        response = self.stub.InteractionCreateGrammarLoad(speech_api.InteractionCreateGrammarLoadRequest(**params),
                                                          metadata=self.get_header())
        return response.interaction_id

    def InteractionCreateASR(self, session_id, interaction_ids) -> str:
        """
        InteractionCreateASR - creates a new ASR interaction for the specified session_id
        Note that interactions_ids is an array of one or more interaction_id values (grammar_ids) obtained from
        call(s) to InteractionCreateGrammarLoad

        :param session_id: session_id to associate new interaction with
        :param interaction_ids: array of grammars to use
        :return: interaction_id
        """
        if not isinstance(interaction_ids, list):
            print("InteractionCreateASR Error: Did you pass string as interactions_ids instead of array?")
        params = {
            "session_id": session_id,
            "interaction_ids": interaction_ids
        }
        response = self.stub.InteractionCreateASR(speech_api.InteractionCreateASRRequest(**params),
                                                  metadata=self.get_header())
        return response.interaction_id

    def InteractionCreateGrammarParse(self, session_id, grammar_ids, input_text) -> str:
        """
        Creates a new InteractionCreateGrammarParse request, returning a new interaction_id

        :param session_id: the session_id in which to create the new interaction
        :param grammar_ids: array of grammar_ids that should be used for this request
        :param input_text: string that should be processed by this request
        :return: interaction_id associated with new parse interaction
        """
        assert isinstance(grammar_ids, list), "Did you pass string as grammar_ids instead of array?"
        params = {
            "session_id": session_id,
            "grammar_ids": grammar_ids,
            "input_text": input_text,
        }
        response = self.stub.InteractionCreateGrammarParse(
            speech_api.InteractionCreateGrammarParseRequest(**params),
            metadata=self.get_header())
        return response.interaction_id

    def InteractionCreateTTS(self, session_id=None, language=None, ssml_url=None, text=None, voice=None,
                             audio_format=None) -> str:
        """
        Creates a new InteractionCreateTTS request, returning a new interaction_id
        Note that one of either ssml_url or text should be specified.

        :param session_id: the session_id in which to create the new interaction
        :param language: language for TTS synthesis
        :param ssml_url: optional URL where SSML document can be loaded (must be reachable by server)
        :param text: optional text to be synthesized by this request
        :param voice: optional voice to use for synthesis. This should not be supplied if using SSML (inline or URL)
        :param audio_format: audio format that the synthesis should generate
        :return: interaction_id associated with new interaction
        """
        params = {
            "session_id": session_id,
            "language": language,
            "audio_format": {
                "standard_audio_format": audio_format
            }
        }
        inline_request = {}
        if ssml_url is not None:
            params["ssml_url"] = ssml_url
            # Important! You cannot specify either voice or text when using ssml_url
            assert voice is None
            assert text is None
        if text is not None:
            inline_request['text'] = text
        if voice is not None:
            inline_request['voice'] = voice
        if text is not None or voice is not None:
            params["inline_request"] = inline_request

        response = self.stub.InteractionCreateTTS(speech_api.InteractionCreateTTSRequest(**params),
                                                  metadata=self.get_header())
        return response.interaction_id

    def get_audio_file(self, audio_file_path) -> bytes:
        """
        Reads the specified audio file from disc and returns the data

        :param audio_file_path: relative or absolute path to audio file
        :return: bytes from file
        """
        assert os.path.isfile(audio_file_path), "Referenced audio file not found!"

        # print("audio_file_path: ", audio_file_path)
        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        return audio_data

    def load_audio_stream_buffer(self, audio_file_path, stream_chunk_bytes) -> AudioStreamBuffer:
        """
        Reads the specified audio file from disc into an AudioStreamBuffer object and returns it

        :param stream_chunk_bytes: number of bytes per chunk to stream
        :param audio_file_path: relative or absolute path to audio file
        :return: bytes from file
        """
        assert os.path.isfile(audio_file_path), "Referenced audio file not found!"

        with open(audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        audio_stream_buffer = AudioStreamBuffer(audio_data=audio_data, stream_chunk_bytes=stream_chunk_bytes)
        return audio_stream_buffer

    def get_ssml_file_by_ref(self, ssml_file_path) -> str:
        """
        Opens the referenced SSML file and returns the contents as a string

        :param ssml_file_path: file path reference to SSML
        :return: string containing SSML
        """
        with open(ssml_file_path, 'r') as file:
            data = file.read()
        return data

    @staticmethod
    def create_audio_file(session_id, byte_array, file_type=".ulaw") -> str:
        """
        Creates a File and stored the specified audio data within

        :param session_id: session_id string, which is used in the generated filename
        :param byte_array: raw audio to be stored in the file
        :param file_type: file suffix indicating the type of file, i.e. .ulaw, .alaw, .pcm, etc.
        :return: Filename generated including relative path
        """
        output_path = 'test_data/'
        output_filename = output_path + session_id + file_type
        with open(output_filename, mode='bx') as f:
            f.write(byte_array)
        return output_filename

    def load_grammar_file(self, grammar_file_path) -> str:
        """
        Opens the referenced grammar file and returns the contents as a string

        :param grammar_file_path: relative or absolute path to grammar file
        :return: string containing grammar
        """
        assert os.path.isfile(grammar_file_path), "Referenced grammar file not found!"

        with open(grammar_file_path, 'r') as file:
            data = file.read()
        return data

    def load_grammar_helper(self, session_id, language_code, grammar_file_path=None, grammar_url=None):
        """
        Helper to load one or more specified grammars and wait for them to load, then return an
        array containing all loaded grammar_ids.

        :param session_id: session_id associated with the specified grammar(s) to be loaded
        :param language_code: the language_code to be applied to all specified grammars during load
        :param grammar_file_path: string reference or array of relative or absolute path to grammar files
        :param grammar_url: string URL reference or array of string URL references
        :return: array of grammar_id values relating to specified grammar(s)
        """
        assert not (grammar_file_path is None and grammar_url is None), "You must specify either grammar_file_ref or grammar_url"
        grammar_ids = []

        # If specified grammar reference is a string (as opposed to array), convert into array
        if grammar_file_path:
            if type(grammar_file_path) == str:
                grammar_file_path = [grammar_file_path]
            gram_array = grammar_file_path
        else:
            if type(grammar_url) == str:
                grammar_url = [grammar_url]
            gram_array = grammar_url

        for gram in gram_array:
            if grammar_file_path:
                inline_grammar_text = self.load_grammar_file(grammar_file_path=gram)
                grammar_id = self.InteractionCreateGrammarLoad(session_id=session_id,
                                                               language_code=language_code,
                                                               inline_grammar_text=inline_grammar_text)
            else:
                grammar_id = self.InteractionCreateGrammarLoad(session_id=session_id,
                                                               language_code=language_code,
                                                               grammar_url=gram)

            self.reset_result_event(session_id=session_id)

            # Tell grammar to start processing...
            self.InteractionBeginProcessing(session_id=session_id, interaction_id=grammar_id)

            # Wait for callback indicating grammar loaded
            self.wait_for_final_results(session_id=session_id, interaction_id=None, wait_time=3.5)
            grammar_ids.append(grammar_id)

        self.reset_result_event(session_id=session_id)

        return grammar_ids

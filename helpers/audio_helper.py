"""
Audio Handler file
This file introduces the AudioHandler class to facilitate audio-sending processes utilized in AMD, ASR, CPA, and
Transcription call flows.
"""
import asyncio
import os
import time

# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats
# Import code/data needed to interaction with the API
from lumenvox_api_handler import LumenVoxApiClient

from helpers.common_helper import optional_int32

# Common sample rate values.
SAMPLE_RATE_8HZ = 8000
SAMPLE_RATE_16HZ = 16000
SAMPLE_RATE_22HZ = 22050

# Define a series of common audio format messages that can be used in other files. 
# The AudioFormat message type in audio_formats.proto contains an enumeration specifying audio format values
# (StandardAudioFormat).
# The sample rates are also, and are required for all formats except WAV and FLAC.

AUDIO_FORMAT_ULAW_8KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=SAMPLE_RATE_8HZ),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW
)

AUDIO_FORMAT_ULAW_16KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=SAMPLE_RATE_16HZ),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW,
)

AUDIO_FORMAT_ALAW_8KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=SAMPLE_RATE_8HZ),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ALAW,
)

AUDIO_FORMAT_PCM_8KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=SAMPLE_RATE_8HZ),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_LINEAR16,
)

AUDIO_FORMAT_PCM_16KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=SAMPLE_RATE_16HZ),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_LINEAR16,
)

AUDIO_FORMAT_PCM_22KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=SAMPLE_RATE_22HZ),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_LINEAR16,
)

AUDIO_FORMAT_WAV_8KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=8000),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_WAV,
)


class AudioBuffer:
    """
    Class to contain an audio buffer or rather audio data (bytes) split up into chunks.
    """
    def __init__(self, audio_data, chunk_bytes=200):
        """
        Initialize the audio buffer.
        :param audio_data: Audio data (bytes) to save to buffer.
        :param chunk_bytes: Integer value pertaining to how big each individual audio chunk size should be.
        """
        # Initialize the entire audio data.
        self.audio_data = audio_data

        # During creation, users can specify a different chunk size, or use the default.
        self.chunk_bytes = chunk_bytes

        self.read_location = 0
        self.bytes_remaining = 0

        # Note bytes remaining cannot easily be converted to milliseconds here, since we don't know audio format!
        self.total_audio_bytes = len(audio_data)

    def get_next_chunk(self):
        """
        Depending on the provided chunk size, return a portion of audio data (bytes).
        :return: Audio data chunk (bytes)
        """
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


class AudioHandler:
    """
    This class handles audio functionality used for ASR and ASR-adjacent operations (AMD, CPA, Transcription).
    The purpose of this class is to facilitate a way to track the state of audio as we send its data into the session.
    """
    lumenvox_api_client: LumenVoxApiClient = None

    session_stream = None
    session_id: str = None

    audio_file_path: str = None
    audio_format: audio_formats.AudioFormat = None

    audio_push_sleep_override: float = 0  # Use this variable to change the rate at which we push audio.
    audio_push_chunk_size_bytes: int = 0  # Size of audio chunks to send.
    num_audio_chunks_sent: int = 0  # Used to keep track of how much audio is sent.

    audio_data_buffer: AudioBuffer = None
    audio_data = None

    # These next events are used for sending audio in chunks.
    audio_push_cancel_event = asyncio.Event()  # Set this to cancel audio push prematurely (if using buffers/chunks).
    audio_push_finish_event = asyncio.Event()  # Use this to track whether the audio has been entirely pushed.

    # Determines whether to print audio push messages or not. Not essential.
    print_audio_push_messages = True

    correlation_id: str = None

    def __init__(self, lumenvox_api_client, audio_file_path: str = None,
                 audio_format: audio_formats.AudioFormat = None, chunk_audio: bool = True,
                 audio_push_sleep_override: float = 0, audio_push_chunk_size_bytes: int = 0,
                 audio_push_cancel_event: asyncio.Event = None, audio_push_finish_event: asyncio.Event = None,
                 session_stream=None, session_id: str = None):

        self.lumenvox_api_client = lumenvox_api_client
        self.audio_file_path = audio_file_path

        if not self.audio_file_path:
            raise ValueError("No audio file path given.")

        self.audio_format = audio_format

        self.audio_push_sleep_override = audio_push_sleep_override
        self.audio_push_chunk_size_bytes = audio_push_chunk_size_bytes
        self.audio_push_cancel_event = audio_push_cancel_event if audio_push_cancel_event else asyncio.Event()
        self.audio_push_finish_event = audio_push_finish_event if audio_push_finish_event else asyncio.Event()

        if chunk_audio:
            self.init_audio_buffer()  # Set audio data buffer.
        else:
            self.init_full_audio_bytes()  # Set audio data.

        self.session_stream = session_stream
        self.session_id = session_id

    def init_audio_buffer(self):
        """
        Reads the specified audio file from disk into an AudioBuffer object and returns it.
        """
        if not self.audio_push_chunk_size_bytes:
            raise ValueError("Invalid audio chunk size")
        if not os.path.isfile(self.audio_file_path):
            raise FileNotFoundError(self.audio_file_path + " not found")

        with open(self.audio_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()

        self.audio_data_buffer = AudioBuffer(audio_data=audio_data, chunk_bytes=self.audio_push_chunk_size_bytes)

    def init_full_audio_bytes(self, audio_file_path: str = None):
        """
        Read full audio file into self.audio_data (bytes).
        :param audio_file_path: Use this if self.audio_file_path is not already set.
        """
        if not self.audio_file_path:
            self.audio_file_path = audio_file_path

        if not self.audio_file_path:
            raise ValueError("AudioHandler: Must be given a file path to read audio file.")

        if not os.path.isfile(self.audio_file_path):
            raise FileNotFoundError(self.audio_file_path + " not found")

        with open(self.audio_file_path, 'rb') as audio_file:
            self.audio_data = audio_file.read()

    async def set_inbound_audio_format(self):
        """
        This function will wrap over the session_set_inbound_audio_format function provided in the LumenVox API Client
        class, setting the audio format provided to this class.
        """
        if not self.lumenvox_api_client:
            raise ValueError("AudioHandler Error: Set lumenvox_api_client before running audio functions.")

        if not self.audio_format:
            raise ValueError("AudioHandler Error: Set audio_format before running audio functions.")

        await self.lumenvox_api_client.session_set_inbound_audio_format(
            session_stream=self.session_stream,
            audio_format_msg=self.audio_format,
            correlation_id=self.correlation_id)

    async def push_all_audio(self):
        """
        This function will push the entirety of the audio data (self.audio_data) at once.
        Unlike self.push_audio_chunks, this does not need to be run as a task.
        """
        if not self.audio_data:
            raise ValueError("Cannot not push audio without self.audio_data")

        if not self.lumenvox_api_client:
            raise ValueError("AudioHandler Error: Set lumenvox_api_client before running audio functions.")

        await self.lumenvox_api_client.session_audio_push(
            session_stream=self.session_stream,
            audio_data=self.audio_data,
            correlation_id=self.correlation_id)

    async def push_audio_chunks(self):
        """
        Push audio data chunks into the LumenVox API.
        """
        sample_rate: int = self.audio_format.sample_rate_hertz.value
        audio_format = self.audio_format.standard_audio_format

        bytes_per_sample = 1

        # The format of the audio is crucial to determine the rate at which the audio is sent, so the bytes_per_sample
        # is set based on the format.
        # Here, we reference the Enumeration defined in the AudioFormat protocol buffer message
        # (see audio_formats.proto).
        if audio_format == audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW:
            bytes_per_sample = 1
        elif audio_format == audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ALAW:
            bytes_per_sample = 1
        elif audio_format == audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_LINEAR16:
            bytes_per_sample = 2
        elif audio_format == audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_WAV:
            # here, we need to grab information from the WAV header

            wav_format = self.audio_data_buffer.audio_data[20]  # Get WAV format from header.
            if (wav_format == 7) or (wav_format == 6):  # Handle ULAW/ALAW.
                bytes_per_sample = 1
            elif wav_format == 1:  # Handle PCM.
                bytes_per_sample = 2

            sample_rate = (self.audio_data_buffer.audio_data[29] << 8) + self.audio_data_buffer.audio_data[28]

            self.audio_data_buffer.get_next_chunk()  # Get rid of the first chunk since it should already be sent.

        # We calculate the rate of time at which audio is sent into the API. Bytes/millisecond needs to be determined
        # beforehand.
        bytes_per_ms = (bytes_per_sample * sample_rate) / 1000
        chunk_duration_ms = self.audio_push_chunk_size_bytes / bytes_per_ms

        start_time = time.time()
        total_request_time = 0  # seconds

        # Execute a while loop wherein audio chunks are sent to the API. The rate of time at which the chunks are sent
        # factors in the chunk_duration_ms calculated above.
        more_bytes = True
        self.num_audio_chunks_sent = 0
        while more_bytes:
            request_start_time = time.time()  # seconds

            if self.audio_push_cancel_event or self.audio_push_finish_event:
                if self.audio_push_cancel_event.is_set():
                    self.audio_push_finish_event.set()
                    break

            more_bytes = \
                await self.lumenvox_api_client.audio_push_from_buffer(
                    session_stream=self.session_stream,
                    audio_buffer=self.audio_data_buffer,
                    correlation_id=self.correlation_id)

            self.num_audio_chunks_sent += 1

            if self.print_audio_push_messages:
                print("Sending audio chunk ", self.num_audio_chunks_sent)

            request_time = time.time() - request_start_time  # seconds
            total_request_time += request_time

            sleep_duration = ((self.num_audio_chunks_sent * chunk_duration_ms) / 1000) - (time.time() - start_time)
            await \
                asyncio.sleep(sleep_duration if not self.audio_push_sleep_override else self.audio_push_sleep_override)

        total_stream_time = time.time() - start_time
        sleep_time = total_stream_time - total_request_time

        print("AUDIO STREAM COMPLETED. ",
              ", TotalAudioStreamDuration (ms):", total_stream_time * 1000,
              ", TotalTimeSpentOnAllRequests (ms): ", total_request_time * 1000,
              ", SleepingTime (ms): ", sleep_time * 1000,
              ", TotalNumberOfStreamingRequests (Chunk counter): ", self.num_audio_chunks_sent)

        # Set the finish event defined above so that any function waiting for audio to be sent knows that the process
        # has been finished.
        if self.audio_push_finish_event:
            self.audio_push_finish_event.set()

"""
ASR Sample with Audio Channel Selection
This script will run through a session utilizing a batch ASR interaction targeting specific audio channels.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/asr-integration#section/INTEGRATION-WORKFLOWS/ASR

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/asr-configuration
"""
import uuid

# Import protocol buffer messages from settings
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code
import lumenvox_api_handler

# Import helper functions for settings.
from helpers import settings_helper
# Import helper functions for grammar files.
from helpers import grammar_helper

# Import code needed to interact with the API
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_WAV_8KHZ

# Importing the AsrInteractionData class from the asr_batch_sample.py script.
from asr_batch_sample import AsrInteractionData
# Also import the asr_batch function from the same script.
from asr_batch_sample import asr_batch


def run_interactions(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient):
    """
    Run two ASR interactions, each using a different channel.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    interaction_data_1 = AsrInteractionData()
    interaction_data_2 = AsrInteractionData()

    language_code = 'en-us'

    audio_chunk_size = 160

    # These interactions will utilize a WAV file containing a header.
    audio_format_msg = AUDIO_FORMAT_WAV_8KHZ

    # This is a WAV file containing a header. The first channel is "1 2 3 4". The second is "mouse".
    audio_file_path = './sample_data/Audio/en/first_1234_second_mouse_ulaw.wav'

    # Defining a list containing a single Transcription grammar here, allowing the ASR to perform Transcription.
    grammar_1 = (
        grammar_helper.inline_grammar_by_file_ref('sample_data/Grammar/en-US/en_digits.grxml'))
    grammar_2 = (
        grammar_helper.inline_grammar_by_file_ref('sample_data/Grammar/en-US/en_animals.gram'))

    # Define settings.
    # As this script focuses on two interactions using different channels, two different sets of AudioConsumeSettings
    # need to be defined.
    # Since a batch ASR interaction is being used, AUDIO_CONSUME_MODE_BATCH and
    # STREAM_START_LOCATION_STREAM_BEGIN need to be set (see asr_batch_sample.py).

    # AudioConsumeSettings for the first channel.
    audio_consume_settings_1 = \
        settings_helper.define_audio_consume_settings(
            audio_channel=0,
            audio_consume_mode=settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_BATCH,
            stream_start_location=
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_STREAM_BEGIN)

    # AudioConsumeSettings for the second channel.
    audio_consume_settings_2 = \
        settings_helper.define_audio_consume_settings(
            audio_channel=1,
            audio_consume_mode=settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_BATCH,
            stream_start_location=
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_STREAM_BEGIN)

    # These settings will be used for both interactions.
    vad_settings = settings_helper.define_vad_settings(use_vad=True)
    recognition_settings = settings_helper.define_recognition_settings()

    # Set up data for interaction 1.
    interaction_data_1.language_code = language_code
    interaction_data_1.audio_handler = (
        AudioHandler(lumenvox_api_client=lumenvox_api_client,
                     audio_file_path=audio_file_path,
                     audio_format=audio_format_msg,
                     audio_push_chunk_size_bytes=audio_chunk_size))
    interaction_data_1.grammar_messages = [grammar_1]
    interaction_data_1.audio_consume_settings = audio_consume_settings_1
    interaction_data_1.vad_settings = vad_settings
    interaction_data_1.recognition_settings = recognition_settings
    interaction_data_1.correlation_id = str(uuid.uuid4())

    # Store full audio bytes from file specified in the path above for Batch.
    interaction_data_1.audio_handler.init_full_audio_bytes()

    # Set up data for interaction 2.
    interaction_data_2.language_code = language_code
    interaction_data_2.audio_handler = (
        AudioHandler(lumenvox_api_client=lumenvox_api_client,
                     audio_file_path=audio_file_path,
                     audio_format=audio_format_msg,
                     audio_push_chunk_size_bytes=audio_chunk_size))
    interaction_data_2.grammar_messages = [grammar_2]
    interaction_data_2.audio_consume_settings = audio_consume_settings_2
    interaction_data_2.vad_settings = vad_settings
    interaction_data_2.recognition_settings = recognition_settings
    interaction_data_2.correlation_id = str(uuid.uuid4())

    # Store full audio bytes from file specified in the path above for Batch.
    interaction_data_2.audio_handler.init_full_audio_bytes()

    # Should provide the result "1 2 3 4".
    coroutine_first_channel = (
        asr_batch(lumenvox_api_client=lumenvox_api_client, asr_interaction_data=interaction_data_1))
    lumenvox_api_client.run_user_coroutine(coroutine_first_channel)

    # Should provide the result "mouse".
    coroutine_second_channel = (
        asr_batch(lumenvox_api_client=lumenvox_api_client, asr_interaction_data=interaction_data_2))
    lumenvox_api_client.run_user_coroutine(coroutine_second_channel)


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    # This function will run through two interactions showcasing audio channel selection for ASR/Transcription.
    run_interactions(lumenvox_api_client=lumenvox_api)

"""
Transcription Sample with Audio Channel Selection
This script will run through a session utilizing a Transcription interaction targeting specific audio channels.

As this script utilizes a Transcription interaction, it pulls functionality and the interaction data container class
from the transcription_sample.py script. Refer to that script for more information on Transcription interactions.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/asr-integration#section/INTEGRATION-WORKFLOWS/Transcription

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/asr-configuration
"""
# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code.
import lumenvox_api_handler

# Our custom helper functions for settings.
from helpers import settings_helper

# Import code needed to interact with the API.
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences.
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_WAV_8KHZ

# This script will utilize the TranscriptionInteractionData class from the transcription_sample.py
from transcription_sample import TranscriptionInteractionData
# Also import the function since the process carrying out the interaction will be the same.
from transcription_sample import transcription


def run_interactions(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient):
    """
    This function will run two different transcription interactions; one interaction will use the first channel,
    the other will use the second channel. Take note of the differences in the results.

    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    # Initialize objects to hold data for both interactions.
    interaction_data_1 = TranscriptionInteractionData()
    interaction_data_2 = TranscriptionInteractionData()

    language_code = 'en-us'

    # Audio chunk size value to use for both interactions.
    audio_chunk_size = 160

    print_audio_push_messages = False

    # Define an audio format for ULAW 8kHz. See the audio_helper file referenced above for more information on the
    # data within these messages.
    audio_format_msg = AUDIO_FORMAT_WAV_8KHZ

    # This is a WAV file containing a header. The first channel is "1 2 3 4". The second is "mouse".
    audio_file_path = './sample_data/Audio/en/first_1234_second_mouse_ulaw.wav'

    # Settings for both interactions (see transcription_sample.py for more information).
    recognition_settings = settings_helper.define_recognition_settings(enable_partial_results=False)
    vad_settings = settings_helper.define_vad_settings(use_vad=True)

    # AudioConsumeSettings for the first channel.
    audio_consume_settings_1 = \
        settings_helper.define_audio_consume_settings(
            audio_channel=0,
            audio_consume_mode=settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING,
            stream_start_location=
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    # AudioConsumeSettings for the second channel.
    audio_consume_settings_2 = \
        settings_helper.define_audio_consume_settings(
            audio_channel=1,
            audio_consume_mode=settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING,
            stream_start_location=
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    # Set up data for the interaction using the first channel.
    interaction_data_1.language_code = language_code
    interaction_data_1.audio_handler = (
        AudioHandler(
            audio_file_path=audio_file_path,
            audio_format=audio_format_msg,
            audio_push_chunk_size_bytes=audio_chunk_size,
            lumenvox_api_client=lumenvox_api_client))
    interaction_data_1.audio_handler.print_audio_push_messages = print_audio_push_messages
    interaction_data_1.audio_consume_settings = audio_consume_settings_1
    interaction_data_1.recognition_settings = recognition_settings
    interaction_data_1.vad_settings = vad_settings

    # Set up data for the interaction using the second channel.
    interaction_data_2.language_code = language_code
    interaction_data_2.audio_handler = (
        AudioHandler(
            audio_file_path=audio_file_path,
            audio_format=audio_format_msg,
            audio_push_chunk_size_bytes=audio_chunk_size,
            lumenvox_api_client=lumenvox_api_client))
    interaction_data_2.audio_handler.print_audio_push_messages = print_audio_push_messages
    interaction_data_2.audio_consume_settings = audio_consume_settings_2
    interaction_data_2.recognition_settings = recognition_settings
    interaction_data_2.vad_settings = vad_settings

    # Should provide the result "1 2 3 4"
    coroutine_first_channel = (
        transcription(lumenvox_api_client=lumenvox_api_client, transcription_interaction_data=interaction_data_1))
    lumenvox_api_client.run_user_coroutine(coroutine_first_channel)

    # Should provide the result "mouse".
    coroutine_second_channel = (
        transcription(lumenvox_api_client=lumenvox_api_client, transcription_interaction_data=interaction_data_2))
    lumenvox_api_client.run_user_coroutine(coroutine_second_channel)


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    # This function will run through two interactions utilizing two different channels of the audio.
    run_interactions(lumenvox_api_client=lumenvox_api)

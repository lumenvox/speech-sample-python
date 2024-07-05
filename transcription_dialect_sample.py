"""
Transcription with Dialects Sample
This script will demonstrate the effects dialects can have on Transcription results.

As this script utilizes a Transcription interaction, it pulls functionality and the interaction data container class
from the transcription_samply.py script. Refer to that script for more information on Transcription interactions.

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
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ

# This script will utilize the TranscriptionInteractionData class from the transcription_sample.py
from transcription_sample import TranscriptionInteractionData
# Also import the function since the process carrying out the interaction will be the same.
from transcription_sample import transcription


def run_interactions(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient):
    """
    This function will run two different transcription interactions; one interaction will use 'en-us' and the other will
    use 'en-gb'. Take note of the differences in the results.

    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    # Initialize objects to hold data for both interactions.
    interaction_data_1 = TranscriptionInteractionData()
    interaction_data_2 = TranscriptionInteractionData()

    # Audio chunk size value to use for both interactions.
    audio_chunk_size = 160

    # Define an audio format for ULAW 8kHz. See the audio_helper file referenced above for more information on the
    # data within these messages.
    audio_format_msg = AUDIO_FORMAT_ULAW_8KHZ

    # This audio file contains words that have different spellings for
    # American English (en-us) or British English (en-gb).
    audio_file_path = './sample_data/Audio/en/transcription/for_the_catalog_ulaw.raw'

    # Settings for both interactions (see transcription_sample.py for more information).
    audio_consume_settings = \
        settings_helper.define_audio_consume_settings(
            audio_consume_mode=settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING,
            stream_start_location=
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)
    recognition_settings = settings_helper.define_recognition_settings(enable_partial_results=False)
    vad_settings = settings_helper.define_vad_settings(use_vad=True)

    # Set up data for the 'en-us' interaction.
    interaction_data_1.language_code = 'en-us'
    interaction_data_1.audio_handler = (
        AudioHandler(
            audio_file_path=audio_file_path,
            audio_format=audio_format_msg,
            audio_push_chunk_size_bytes=audio_chunk_size,
            lumenvox_api_client=lumenvox_api_client))
    interaction_data_1.audio_handler.print_audio_push_messages = False
    interaction_data_1.audio_consume_settings = audio_consume_settings
    interaction_data_1.recognition_settings = recognition_settings
    interaction_data_1.vad_settings = vad_settings

    # Set up data for the 'en-gb' interaction.
    interaction_data_2.language_code = 'en-gb'
    interaction_data_2.audio_handler = (
        AudioHandler(
            audio_file_path=audio_file_path,
            audio_format=audio_format_msg,
            audio_push_chunk_size_bytes=audio_chunk_size,
            lumenvox_api_client=lumenvox_api_client))
    interaction_data_2.audio_handler.print_audio_push_messages = False
    interaction_data_2.audio_consume_settings = audio_consume_settings
    interaction_data_2.recognition_settings = recognition_settings
    interaction_data_2.vad_settings = vad_settings

    # The following two coroutines will run interactions providing slightly different results based on dialect.
    # The final result output will contain a "transcript" field.

    # The result this should provide is: "for the catalog we will organize the items based on color"
    coroutine_en_us = (
        transcription(lumenvox_api_client=lumenvox_api_client, transcription_interaction_data=interaction_data_1))
    lumenvox_api_client.run_user_coroutine(coroutine_en_us)

    # The result this should provide is: "for the catalogue we will organise the items based on colour"
    coroutine_en_gb = (
        transcription(lumenvox_api_client=lumenvox_api_client, transcription_interaction_data=interaction_data_2))
    lumenvox_api_client.run_user_coroutine(coroutine_en_gb)


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    # This function will run through two interactions showcasing the effect dialects may have on the transcript.
    run_interactions(lumenvox_api_client=lumenvox_api)

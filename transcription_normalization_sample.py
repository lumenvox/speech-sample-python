"""
Normalized Transcription Sample
This script will run through a session utilizing a Transcription interaction.

As this script utilizes a Transcription interaction, it pulls functionality and the interaction data container class
from the transcription_samply.py script. Refer to that script for more information on Transcription interactions.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/4.6.0/asr-integration#section/INTEGRATION-WORKFLOWS/Transcription

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/4.6.0/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/4.6.0/asr-configuration
"""
import uuid

# Import protocol buffer messages from settings
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code
import lumenvox_api_handler

# Our custom helper functions for settings.
from helpers import settings_helper

# Import code needed to interact with the API
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ

# This script will utilize the TranscriptionInteractionData class from the transcription_sample.py
from transcription_sample import TranscriptionInteractionData
# Also import the function since the process carrying out the interaction will be the same.
from transcription_sample import transcription


def transcription_interaction_data_setup(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient) \
        -> TranscriptionInteractionData:
    """
    Function to set up data for a transcription interaction.
    Transcription with Normalization enabled will come with additional information in the final result message such
    as verbalized, verbalized_redacted, final, and final_redacted fields.

    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    :return: Interaction data used for transcription.
    """
    interaction_data = TranscriptionInteractionData()

    interaction_data.language_code = 'en-us'

    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    interaction_data.correlation_id = str(uuid.uuid4())

    ####### Define Audio Data #######
    interaction_data.audio_handler = (
        AudioHandler(
            lumenvox_api_client=lumenvox_api_client,
            audio_file_path=
            './sample_data/Audio/en/transcription/meeting.raw',
            audio_format=AUDIO_FORMAT_ULAW_8KHZ,
            audio_push_chunk_size_bytes=4000))

    # For non-batch operations, load audio data into a buffer.
    interaction_data.audio_handler.init_audio_buffer()

    ####### Define Settings #######
    # Transcription interactions utilize numerous settings that may affect the flow of the interaction.
    # Most settings are optional but some may affect the flow and performance of the interaction.

    # Define normalization settings using the helper function that provides a NormalizationSettings message
    # (see settings.proto).
    # Setting at least one of the settings to True will provide at least some form of normalization on the result.
    normalization_settings = (
        settings_helper.define_normalization_settings(enable_inverse_text=True, enable_redaction=True,
                                                      enable_punctuation_capitalization=True))

    # Define variables to use for audio consume settings. This will affect the processing type (Batch/Streaming) and
    # determine when we push audio.
    # Since the function handles streaming, we will need AUDIO_CONSUME_MODE_STREAMING.
    audio_consume_mode = settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING

    # A stream start location of STREAM_START_LOCATION_INTERACTION_CREATED or
    # STREAM_START_LOCATION_BEGIN_PROCESSING_CALL is required for ASR streaming functionality.
    # See settings.proto for more information on the enumeration this value comes from.
    stream_start_location = (
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    audio_consume_settings = (
        settings_helper.define_audio_consume_settings(audio_consume_mode=audio_consume_mode,
                                                      stream_start_location=stream_start_location))
    recognition_settings = settings_helper.define_recognition_settings()
    vad_settings = settings_helper.define_vad_settings(use_vad=True)

    interaction_data.normalization_settings = normalization_settings
    interaction_data.audio_consume_settings = audio_consume_settings
    interaction_data.recognition_settings = recognition_settings
    interaction_data.vad_settings = vad_settings

    return interaction_data


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    user_interaction_data = transcription_interaction_data_setup(lumenvox_api_client=lumenvox_api)
    lumenvox_api.run_user_coroutine(
        transcription(lumenvox_api_client=lumenvox_api, transcription_interaction_data=user_interaction_data))

"""
Enhanced Transcription Sample
This script will run through a session utilizing a Transcription interaction with the inclusion of grammars.

Refer to the transcription_sample.py script for more information on Transcription interaction, as this script takes
interaction and the interaction function from that.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/asr-integration#section/INTEGRATION-WORKFLOWS/Transcription

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/asr-configuration
"""
import uuid

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code.
import lumenvox_api_handler

# Import helper functions for settings.
from helpers import settings_helper
# Import helper functions for grammar files.
from helpers import grammar_helper

# Import code needed to interact with the API.
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
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    :return: Interaction data used for transcription.
    """
    interaction_data = TranscriptionInteractionData()

    interaction_data.language_code = 'en-us'

    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    interaction_data.correlation_id = str(uuid.uuid4())

    # The user defines a set of grammars to use for Enhanced Transcription.
    # If the contents of the grammars are recognized in the audio, then the Transcription results will contain
    # semantic interpretations, similar to the results of ASR interactions.
    embedded_grammars = [
        grammar_helper.inline_grammar_by_file_ref(
            grammar_reference='./sample_data/Grammar/en-US/ABNFDigits.gram'),
        grammar_helper.define_grammar(builtin_voice_grammar=4),  # built-in grammar (see common.proto)
        grammar_helper.inline_grammar_by_file_ref(
            grammar_reference='./sample_data/Grammar/en-US/the_man_was_one_hundred_years_old.grxml'),
        grammar_helper.inline_grammar_by_file_ref(
            grammar_reference='./sample_data/Grammar/en-US/en_animals.gram')
    ]

    interaction_data.embedded_grammars = embedded_grammars

    ####### Define Audio Data #######
    interaction_data.audio_handler = (
        AudioHandler(
            lumenvox_api_client=lumenvox_api_client,
            audio_file_path=
            './sample_data/Audio/en/transcription/passphrase_the_man_was_one_hundred_years_old_passcode_4127_ulaw.raw',
            audio_format=AUDIO_FORMAT_ULAW_8KHZ,
            audio_push_chunk_size_bytes=4000))

    # Set this to True to view messages on AudioPush status.
    interaction_data.audio_handler.print_audio_push_messages = True

    # For non-batch operations, load audio data into a buffer.
    interaction_data.audio_handler.init_audio_buffer()

    ####### Define Settings #######
    # Transcription interactions utilize numerous settings that may affect the flow of the interaction.
    # Most settings are optional but some may affect the flow and performance of the interaction.

    # Define variables to use for audio consume settings. This will affect the processing type (Batch/Streaming) and
    # determine when we push audio.
    # Since the function handles streaming, we will need AUDIO_CONSUME_MODE_STREAMING.
    audio_consume_mode = settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING

    # A stream start location of STREAM_START_LOCATION_INTERACTION_CREATED or
    # STREAM_START_LOCATION_BEGIN_PROCESSING_CALL is required for ASR streaming functionality
    stream_start_location = (
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    # Determine whether to use VAD or not (VAD is required for Transcription streaming interactions).
    use_vad = True

    # This Recognition setting can be used to enable partial results.
    enable_partial_results = False

    audio_consume_settings = (
        settings_helper.define_audio_consume_settings(audio_consume_mode=audio_consume_mode,
                                                      stream_start_location=stream_start_location))
    recognition_settings = (
        settings_helper.define_recognition_settings(enable_partial_results=enable_partial_results))
    vad_settings = settings_helper.define_vad_settings(use_vad=use_vad)

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

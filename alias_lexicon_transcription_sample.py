"""
Transcription with Alias/Lexicon Sample
This script will run through a session utilizing a batch ASR interaction using a Transcription grammar to showcase
alias/lexicon usage.

As this script utilizes an ASR batch interaction, it pulls functionality and the interaction data container class from
the asr_batch_sample.py script. Refer to that script for more information on ASR batch interactions.

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

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# Import helper functions for settings.
from helpers import settings_helper
# Import helper functions for grammar files.
from helpers import grammar_helper

# Import code needed to interact with the API.
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences.
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ

# Importing the AsrInteractionData class from the asr_batch_sample.py script.
from asr_batch_sample import AsrInteractionData
# Also import the asr_batch function from the same script.
from asr_batch_sample import asr_batch

# Inline grammar text, using a lexicon reference to a public XML file.
# The lexicon file contains words 'zero', 'oh', and 'naught' as aliases for the grapheme 'Zero'.
# Due to the Transcription Engine being referenced in the meta name, an ASR interaction using this grammar will
# perform Transcription.
inline_grammar_text = \
    """<?xml version='1.0'?>
    <grammar xml:lang="en" version="1.0" root="root" mode="voice"
             xmlns="http://www.w3.org/2001/06/grammar"
             tag-format="semantics/1.0.2006">

        <meta name="TRANSCRIPTION_ENGINE" content="V2"/>
        <lexicon uri="https://assets.lumenvox.com/lexicon/zero_lexicon.xml"/>       
        <rule id="root" scope="public">
            <item>

            </item>
        </rule>
    </grammar>
    """


def asr_interaction_data_setup(lumenvox_api_client: LumenVoxApiClient) -> AsrInteractionData:
    """
    Use this function to set up interaction data used for the ASR interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    :return: Object containing interaction data for ASR.
    """
    interaction_data = AsrInteractionData()

    interaction_data.language_code = 'en-us'
    interaction_data.correlation_id = str(uuid.uuid4())

    ####### Define Audio Data #######
    # Audio file saying "zero, oh, naught"; should be returned as "Zero Zero Zero" per the grammar and lexicon above.
    audio_file_path = './sample_data/Audio/en/transcription/zero_oh_naught.raw'

    interaction_data.audio_handler = (
        AudioHandler(
            lumenvox_api_client=lumenvox_api_client,
            audio_file_path=audio_file_path,
            audio_format=AUDIO_FORMAT_ULAW_8KHZ,
            audio_push_chunk_size_bytes=160))

    # Store full audio bytes from file specified in the path above for Batch.
    interaction_data.audio_handler.init_full_audio_bytes()

    ####### Define Grammar #######
    # ASR interactions require at least one grammar to function.
    # If a grammar contains TRANSCRIPTION_ENGINE as a meta tag, the ASR will then perform transcription as shown with
    # this interaction.

    # Here, a grammar message is defined using the inline grammar text provided above.
    grammar_1 = grammar_helper.define_grammar(inline_grammar_text=inline_grammar_text)
    grammar_messages = [grammar_1]

    interaction_data.grammar_messages = grammar_messages

    ####### Define Settings #######
    # ASR interactions utilize numerous settings that may affect the flow of the interaction.
    # Most settings are optional but some may affect the flow and performance of the interaction.

    # Define variables to use for audio consume settings. This will affect the processing type (Batch/Streaming) and
    # determine when audio is pushed.
    # Since the function handles Batch processing, we will need AUDIO_CONSUME_MODE_BATCH.
    audio_consume_mode = settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_BATCH
    # A stream start location of STREAM_START_LOCATION_STREAM_BEGIN is required for ASR batch processing.
    stream_start_location = (
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_STREAM_BEGIN)

    # Determine whether to use VAD or not (VAD is not required for ASR interactions, but useful for determining when
    # speech starts and ends).
    use_vad = True

    audio_consume_settings = (
        settings_helper.define_audio_consume_settings(audio_consume_mode=audio_consume_mode,
                                                      stream_start_location=stream_start_location))
    recognition_settings = settings_helper.define_recognition_settings()  # default recognition settings
    vad_settings = settings_helper.define_vad_settings(use_vad=use_vad)

    interaction_data.audio_consume_settings = audio_consume_settings
    interaction_data.recognition_settings = recognition_settings
    interaction_data.vad_settings = vad_settings

    ####### Return Interaction Data #######
    return interaction_data


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    user_interaction_data = asr_interaction_data_setup(lumenvox_api_client=lumenvox_api)
    lumenvox_api.run_user_coroutine(
        asr_batch(lumenvox_api_client=lumenvox_api, asr_interaction_data=user_interaction_data))

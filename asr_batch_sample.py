"""
ASR Batch Sample
This script will run through a session utilizing an ASR interaction with batch processing.
Refer to the integration diagrams found here:
https://developer.lumenvox.com/4.6.0/asr-integration#section/INTEGRATION-WORKFLOWS/ASR

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/4.6.0/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/4.6.0/asr-configuration
"""
import uuid

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code.
import lumenvox_api_handler

# Import essential helper functions.
from helpers import settings_helper
from helpers import grammar_helper

# Import code/data needed to interact with the API.
# Our default deployment and operator IDs are stored in the lumenvox_api_handler.
from lumenvox_api_handler import deployment_id
from lumenvox_api_handler import operator_id
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences.
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ


class AsrInteractionData:
    """
    A class containing data to be used in ASR interactions.
    See the interaction_create_asr function defined in the lumenvox_api_handler.py file for more information
    on the data used in this class.
    """
    language_code: str = None
    audio_handler: AudioHandler = None
    grammar_messages: list = None

    audio_consume_settings: settings_msg.AudioConsumeSettings = None
    recognition_settings: settings_msg.RecognitionSettings = None
    vad_settings: settings_msg.VadSettings = None

    correlation_id: str = None


async def asr_batch(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient,
                    asr_interaction_data: AsrInteractionData):
    """
    ASR Batch Sample Function

    :param asr_interaction_data: Object of AsrInteractionData containing variables used for the interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    ####### Session/Interaction Data #######
    # Define the data to use for the ASR interaction here.

    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    correlation_id = asr_interaction_data.correlation_id

    ####### Session Stream initialization and Session Create #######
    # session_init is a function that will initialize the session stream for the API, and provide a session UUID with
    # SessionCreate.
    session_stream, session_id = \
        await lumenvox_api_client.session_init(deployment_uuid=deployment_id, operator_uuid=operator_id,
                                               correlation_uuid=correlation_id)

    ####### SessionSetInboundAudioFormat #######
    # Populate audio handler with session stream and ID (so we can push audio into the correct stream).
    asr_interaction_data.audio_handler.session_stream = session_stream
    asr_interaction_data.audio_handler.session_id = session_id

    # For interactions that utilize user audio, it's required that the user provide the audio format.
    await asr_interaction_data.audio_handler.set_inbound_audio_format()

    ####### AudioPush (using STREAM_START_LOCATION_STREAM_BEGIN) #######
    # Batch processing can only be used with STREAM_START_LOCATION_STREAM_BEGIN (i.e. audio sent before interaction).
    # Push all audio data at once
    await asr_interaction_data.audio_handler.push_all_audio()

    ####### InteractionCreateASR #######
    # Create the ASR interaction using the variables and settings defined in asr_interaction_data.
    await lumenvox_api_client.interaction_create_asr(
        session_stream=session_stream,
        language=asr_interaction_data.language_code,
        audio_consume_settings=asr_interaction_data.audio_consume_settings,
        recognition_settings=asr_interaction_data.recognition_settings,
        vad_settings=asr_interaction_data.vad_settings,
        correlation_id=asr_interaction_data.correlation_id,
        grammars=asr_interaction_data.grammar_messages)

    # Wait for response containing interaction ID to be returned from the API.
    r = await lumenvox_api_client.get_session_general_response(session_stream=session_stream)
    interaction_id = r.interaction_create_asr.interaction_id

    ####### GetResult #######
    final_result = await lumenvox_api_client.get_session_final_result(session_stream=session_stream)

    ####### InteractionClose #######
    # Once we receive the result and there's nothing left to do, we close the interaction.
    await lumenvox_api_client.interaction_close(session_stream=session_stream, interaction_id=interaction_id,
                                                correlation_id=correlation_id)

    ####### SessionClose #######
    # Similarly, we close the session if there are no other interactions.
    await lumenvox_api_client.session_close(session_stream=session_stream, correlation_id=correlation_id)

    ####### Other #######
    # As we run other tasks to read response from the API, we have this function to kill those tasks once we're finished
    # with this interaction/session.
    lumenvox_api_client.kill_stream_reader_tasks()

    # If desired, the final result message can be checked or returned here.
    # A successful ASR interaction will provide a status of FINAL_RESULT_STATUS_GRAMMAR_MATCH.
    return final_result


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
    interaction_data.audio_handler = (
        AudioHandler(
            lumenvox_api_client=lumenvox_api_client,
            audio_file_path='./sample_data/Audio/en/1234-1s-front-1s-end.ulaw',
            audio_format=AUDIO_FORMAT_ULAW_8KHZ,
            audio_push_chunk_size_bytes=160))

    # Store full audio bytes from file specified in the path above for Batch.
    interaction_data.audio_handler.init_full_audio_bytes()

    ####### Define Grammars #######
    # ASR interactions require at least one grammar to function.
    # Multiple grammars can be defined and passed into the interaction.
    grammar_1 = grammar_helper.inline_grammar_by_file_ref('./sample_data/Grammar/en-US/en_digits.grxml')
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

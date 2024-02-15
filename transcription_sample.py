"""
Transcription Sample
This script will run through a session utilizing a Transcription interaction.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/4.6.0/asr-integration#section/INTEGRATION-WORKFLOWS/Transcription

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/4.6.0/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/4.6.0/asr-configuration
"""
import asyncio
import uuid

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code
import lumenvox_api_handler
# Our custom helper functions for settings.
from helpers import settings_helper

# Import code/data needed to interact with the API.
# Our default deployment and operator IDs are stored in the lumenvox_api_handler.
from lumenvox_api_handler import deployment_id
from lumenvox_api_handler import operator_id
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences.
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ


class TranscriptionInteractionData:
    """
    A class containing data to used in Transcription interactions.
    See the interaction_create_transcription function defined in the lumenvox_api_handler.py file for more information
    on the data used in this class.
    """
    language_code: str = None

    audio_handler: AudioHandler = None

    embedded_grammars: list = None
    phrases: list = None

    audio_consume_settings: settings_msg.AudioConsumeSettings = None
    normalization_settings: settings_msg.NormalizationSettings = None
    recognition_settings: settings_msg.RecognitionSettings = None
    vad_settings: settings_msg.VadSettings = None

    enable_postprocessing: str = None
    language_model_name: str = None
    acoustic_model_name: str = None

    correlation_id: str = None


async def transcription(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient,
                        transcription_interaction_data: TranscriptionInteractionData):
    """
    Transcription Sample Function

    :param transcription_interaction_data: Class to hold interaction data for Transcription.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    ####### Session/Interaction Data #######
    # Define the data to use for the ASR interaction here.
    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    correlation_id = transcription_interaction_data.correlation_id

    audio_push_finish_event = transcription_interaction_data.audio_handler.audio_push_finish_event

    ####### Session Stream initialization and Session Create #######
    # session_init is a function that will initialize the session stream for the API, and provide a session UUID with
    # SessionCreate.
    session_stream, session_id = \
        await lumenvox_api_client.session_init(deployment_uuid=deployment_id, operator_uuid=operator_id,
                                               correlation_uuid=correlation_id)

    ####### SessionSetInboundAudioFormat #######
    # Populate audio handler with session stream and ID (so we can push audio into the correct stream).
    transcription_interaction_data.audio_handler.session_stream = session_stream
    transcription_interaction_data.audio_handler.session_id = session_id

    # For interactions that utilize user audio, it's required that the user provide the audio format.
    await transcription_interaction_data.audio_handler.set_inbound_audio_format()

    ####### InteractionCreateTranscription #######
    # Create a Transcription interaction using the data from the transcription_interaction_data object of the
    # TranscriptionInteractionData class above.
    await lumenvox_api_client.interaction_create_transcription(
        session_stream=session_stream,
        language=transcription_interaction_data.language_code,
        audio_consume_settings=transcription_interaction_data.audio_consume_settings,
        recognition_settings=transcription_interaction_data.recognition_settings,
        vad_settings=transcription_interaction_data.vad_settings,
        normalization_settings=transcription_interaction_data.normalization_settings,
        embedded_grammars=transcription_interaction_data.embedded_grammars,
        phrases=transcription_interaction_data.phrases,
        enable_postprocessing=transcription_interaction_data.enable_postprocessing,
        language_model_name=transcription_interaction_data.language_model_name,
        acoustic_model_name=transcription_interaction_data.acoustic_model_name,
        correlation_id=correlation_id)

    # Wait for response containing interaction ID to be returned from the API.
    response = await lumenvox_api_client.get_session_general_response(session_stream=session_stream)
    interaction_id = response.interaction_create_transcription.interaction_id

    ####### AudioPush (if using STREAM_START_LOCATION_INTERACTION_CREATED) #######
    # Using STREAM_START_LOCATION_INTERACTION_CREATED, we send audio after the interaction has been created.
    if transcription_interaction_data.audio_consume_settings.stream_start_location == \
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED:
        # Run audio push in a separate task.
        asyncio.create_task(transcription_interaction_data.audio_handler.push_audio_chunks())

    ####### InteractionBeginProcessing + AudioPush (if using STREAM_START_LOCATION_BEGIN_PROCESSING_CALL) #######
    # Using STREAM_START_LOCATION_BEGIN_PROCESSING_CALL will require InteractionBeginProcessing to be called before
    # sending audio.

    if transcription_interaction_data.audio_consume_settings.stream_start_location == \
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_BEGIN_PROCESSING_CALL:
        # InteractionBeginProcessing, passing in session stream and interaction ID.
        await lumenvox_api_client.interaction_begin_processing(
            session_stream=session_stream, interaction_id=interaction_id, correlation_id=correlation_id)
        # Run audio push in a separate task.
        asyncio.create_task(transcription_interaction_data.audio_handler.push_audio_chunks())

    ####### Get Result #######
    # Call get_streaming_response which runs a loop attempting to receive the final result message as audio is being
    # pushed and processed.
    final_result = \
        await lumenvox_api_client.get_streaming_response(
            session_stream=session_stream, audio_push_finish_event=audio_push_finish_event)

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

    # If desired, the final result can be checked here.
    # A successful Transcription interaction will provide a status of FINAL_RESULT_STATUS_TRANSCRIPTION_MATCH.
    print("Transcription final result:\n", final_result)

    return final_result


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

    ####### Define Audio Data #######
    interaction_data.audio_handler = (
        AudioHandler(
            lumenvox_api_client=lumenvox_api_client,
            audio_file_path='./sample_data/Audio/en/transcription/the_great_gatsby_1_minute.ulaw',
            audio_format=AUDIO_FORMAT_ULAW_8KHZ,
            audio_push_chunk_size_bytes=4000))

    # Set this value to True to print AudioPush messages.
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
    # For audio with pauses, it's important to set this so that we receive a result for the whole audio, and not just
    # the first portion (as seen with The Great Gatsby audio file).
    eos_delay_ms = 3210

    # This Recognition setting can be used to enable partial results.
    enable_partial_results = False

    audio_consume_settings = (
        settings_helper.define_audio_consume_settings(audio_consume_mode=audio_consume_mode,
                                                      stream_start_location=stream_start_location))
    recognition_settings = (
        settings_helper.define_recognition_settings(enable_partial_results=enable_partial_results))
    vad_settings = settings_helper.define_vad_settings(use_vad=use_vad, eos_delay_ms=eos_delay_ms)

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

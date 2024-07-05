"""
ASR Streaming Sample
This script will run through a session for an ASR interaction with an approach utilizing audio streaming.

This script utilizes code written in the asr_streaming_sample.py script. Refer to that script and the linked documents
for more detail on running ASR interactions.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/asr-integration#section/INTEGRATION-WORKFLOWS/ASR

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/asr-configuration
"""
import asyncio  # This library is used to perform tasking and sleeping functions for the audio streaming approach.
import uuid  # Provide UUID strings for the correlation ID.

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code.
import lumenvox_api_handler

# Import helper functions for settings.
from helpers import settings_helper
# Import helper functions for grammar files.
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

# Importing the AsrInteractionData class from the asr_batch_sample.py script.
from asr_batch_sample import AsrInteractionData


async def asr_streaming(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient,
                        asr_interaction_data: AsrInteractionData):
    """
    ASR Streaming Sample Function

    :param asr_interaction_data: Object of AsrInteractionData containing variables used for the interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    correlation_id = asr_interaction_data.correlation_id

    # We use this event to track when our audio has been fully pushed.
    audio_push_finish_event = asr_interaction_data.audio_handler.audio_push_finish_event

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

    ####### InteractionCreateASR #######
    # Create the ASR interaction using the variables and settings defined above.
    await lumenvox_api_client.interaction_create_asr(
        session_stream=session_stream,
        audio_consume_settings=asr_interaction_data.audio_consume_settings,
        language=asr_interaction_data.language_code,
        recognition_settings=asr_interaction_data.recognition_settings,
        vad_settings=asr_interaction_data.vad_settings,
        correlation_id=correlation_id,
        grammars=asr_interaction_data.grammar_messages)

    # Wait for response containing interaction ID to be returned from the API.
    r = await lumenvox_api_client.get_session_general_response(session_stream=session_stream)
    interaction_id = r.interaction_create_asr.interaction_id

    ####### AudioPush (if using STREAM_START_LOCATION_INTERACTION_CREATED) #######
    # Using STREAM_START_LOCATION_INTERACTION_CREATED, we send audio after the interaction has been created.
    if asr_interaction_data.audio_consume_settings.stream_start_location == \
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED:
        # Run audio push in a separate task.
        asyncio.create_task(asr_interaction_data.audio_handler.push_audio_chunks())

    ####### InteractionBeginProcessing + AudioPush (if using STREAM_START_LOCATION_BEGIN_PROCESSING_CALL) #######
    # Using STREAM_START_LOCATION_BEGIN_PROCESSING_CALL will require InteractionBeginProcessing to be called before
    # sending audio.

    if asr_interaction_data.audio_consume_settings.stream_start_location == \
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_BEGIN_PROCESSING_CALL:
        # InteractionBeginProcessing, passing in session stream and interaction ID.
        await lumenvox_api_client.interaction_begin_processing(
            session_stream=session_stream, interaction_id=interaction_id, correlation_id=correlation_id)
        # Run audio push in a separate task.
        asyncio.create_task(asr_interaction_data.audio_handler.push_audio_chunks())

    ####### Get Result #######
    # If not using VAD, then InteractionFinalizeProcessing needs to be called.
    if not asr_interaction_data.vad_settings.use_vad.value:
        await audio_push_finish_event.wait()
        await lumenvox_api_client.interaction_finalize_processing(
            session_stream=session_stream, interaction_id=interaction_id, correlation_id=correlation_id)
        final_result = await lumenvox_api_client.get_session_final_result(session_stream=session_stream)
    else:
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

    # For non-batch operations, load audio data into a buffer.
    interaction_data.audio_handler.init_audio_buffer()

    # Set this to True to view messages on AudioPush status.
    interaction_data.audio_handler.print_audio_push_messages = True

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
    # determine when we push audio.
    # Since the function handles streaming, we will need AUDIO_CONSUME_MODE_STREAMING.
    audio_consume_mode = settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING

    # A stream start location of STREAM_START_LOCATION_INTERACTION_CREATED or
    # STREAM_START_LOCATION_BEGIN_PROCESSING_CALL is required for ASR streaming functionality
    stream_start_location = (
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    # Determine whether to use VAD or not (VAD is not required for ASR interactions).
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
        asr_streaming(lumenvox_api_client=lumenvox_api, asr_interaction_data=user_interaction_data))

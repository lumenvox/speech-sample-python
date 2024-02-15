"""
AMD Sample
This script will run through a session utilizing an AMD interaction.
Refer to the integration diagrams found here:
https://developer.lumenvox.com/4.6.0/cpa-integration#section/INTEGRATION-WORKFLOWS/AMD

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/4.6.0/cpa-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/4.6.0/cpa-configuration
"""
import asyncio  # This library is used to perform tasking and sleeping functions for the audio streaming approach.
import uuid  # Provide UUID strings for the correlation ID.

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code.
import lumenvox_api_handler
# Import helpers functions for settings.
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


class AmdInteractionData:
    """
    A class containing data to be used in AMD interactions.
    See the interaction_create_amd function defined in the lumenvox_api_handler.py file for more information
    on the data used in this class.
    """
    amd_settings: settings_msg.AmdSettings = None
    audio_consume_settings: settings_msg.AudioConsumeSettings = None
    recognition_settings: settings_msg.RecognitionSettings = None
    vad_settings: settings_msg.VadSettings = None

    audio_handler: AudioHandler = None

    correlation_id: str = None


async def amd(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient, amd_interaction_data: AmdInteractionData):
    """
    AMD Sample Function

    There are three different flows for AMD interactions:
    Streaming / VAD Active / STREAM_START_LOCATION_INTERACTION_CREATED
    Streaming / VAD Active / STREAM_START_LOCATION_BEGIN_PROCESSING_CALL
    Batch Mode / VAD Active / STREAM_START_LOCATION_STREAM_BEGIN

    :param amd_interaction_data: Object of AmdInteractionData containing variables used for the interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    ####### Session/Interaction Data #######
    # Define the data to use for the AMD interaction here.

    # Correlation IDs aren't required, but can be useful in tracking messages sent to and from the API.
    correlation_id = amd_interaction_data.correlation_id

    # We use this event to track when our audio has been fully pushed.
    audio_push_finish_event = amd_interaction_data.audio_handler.audio_push_finish_event

    ####### Session Stream initialization and Session Create #######
    # session_init is a function that will initialize the session stream for the API, and provide a session UUID with
    # SessionCreate.
    session_stream, session_id = \
        await lumenvox_api_client.session_init(deployment_uuid=deployment_id, operator_uuid=operator_id,
                                               correlation_uuid=correlation_id)

    # Populate audio handler with session stream and ID (so we can push audio into the correct stream).
    amd_interaction_data.audio_handler.session_stream = session_stream
    amd_interaction_data.audio_handler.session_id = session_id
    amd_interaction_data.audio_handler.lumenvox_api_client = lumenvox_api_client

    ####### SessionSetInboundAudioFormat #######
    # For interactions that utilize user audio, it's required that the user provide the audio format.
    await amd_interaction_data.audio_handler.set_inbound_audio_format()

    ####### AudioPush (if using STREAM_START_LOCATION_STREAM_BEGIN) #######
    # We check if the Audio Consume Mode is Batch.
    # Batch processing can only be used with STREAM_START_LOCATION_STREAM_BEGIN (i.e. audio sent before interaction).
    # Push all audio at once if these conditions are met.

    if amd_interaction_data.audio_consume_settings.audio_consume_mode == \
            settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING:

        if amd_interaction_data.audio_consume_settings.stream_start_location == \
                settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED:
            # Push all audio data at once
            await amd_interaction_data.audio_handler.push_all_audio()
        else:
            raise ValueError("AUDIO_CONSUME_MODE_BATCH can only be used with STREAM_START_LOCATION_STREAM_BEGIN.")

    ####### InteractionCreateAMD #######
    # Audio may be pushed before or after this point depending on the audio consume settings defined above.
    # If using batch processing, the audio is sent before the interaction is created.
    # If using STREAM_START_LOCATION_INTERACTION_CREATED, the audio is sent after the interaction is created.
    # If using STREAM_START_LOCATION_BEGIN_PROCESSING_CALL, we send audio after InteractionBeginProcessing is called.

    # Create the AMD interaction using the data defined in amd_interaction_data.
    await lumenvox_api_client.interaction_create_amd(
        session_stream=session_stream,
        audio_consume_settings=amd_interaction_data.audio_consume_settings,
        amd_settings=amd_interaction_data.amd_settings,
        vad_settings=amd_interaction_data.vad_settings,
        correlation_id=correlation_id)

    # Wait for response containing interaction ID to be returned from the API.
    response = await lumenvox_api_client.get_session_general_response(session_stream=session_stream)
    interaction_id = response.interaction_create_amd.interaction_id

    ####### AudioPush (if using STREAM_START_LOCATION_INTERACTION_CREATED) #######
    # Using STREAM_START_LOCATION_INTERACTION_CREATED, we send audio after the interaction has been created.
    if amd_interaction_data.audio_consume_settings.stream_start_location == \
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED:
        # Run audio push in a separate task.
        asyncio.create_task(amd_interaction_data.audio_handler.push_audio_chunks())

    ####### InteractionBeginProcessing + AudioPush (if using STREAM_START_LOCATION_BEGIN_PROCESSING_CALL) #######
    # Using STREAM_START_LOCATION_BEGIN_PROCESSING_CALL will require InteractionBeginProcessing to be called before
    # sending audio.

    if amd_interaction_data.audio_consume_settings.stream_start_location == \
            settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_BEGIN_PROCESSING_CALL:
        # InteractionBeginProcessing, passing in session stream and interaction ID.
        await lumenvox_api_client.interaction_begin_processing(
            session_stream=session_stream, interaction_id=interaction_id, correlation_id=correlation_id)
        # Run audio push in a separate task.
        asyncio.create_task(amd_interaction_data.audio_handler.push_audio_chunks())

    ####### Get Result #######
    # If batch processing is used, the final result can be checked after creating the interaction.
    if amd_interaction_data.audio_consume_settings.audio_consume_mode == \
            settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_BATCH:
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

    # If desired, the final result can be checked or returned here.
    # A successful AMD interaction will provide a status of FINAL_RESULT_STATUS_AMD_TONE.
    return final_result


def amd_interaction_data_setup(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient) -> AmdInteractionData:
    """
    Use this function to set up interaction data used for the AMD interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    :return:
    """
    interaction_data = AmdInteractionData()

    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    interaction_data.correlation_id = str(uuid.uuid4())

    ####### Define Audio Data #######
    interaction_data.audio_handler = (
        AudioHandler(
            lumenvox_api_client=lumenvox_api_client,
            audio_file_path='./sample_data/Audio/amd/audio-TDB-AM.ulaw',
            audio_format=AUDIO_FORMAT_ULAW_8KHZ,
            audio_push_chunk_size_bytes=160))

    # Set this to True to view messages on AudioPush status.
    interaction_data.audio_handler.print_audio_push_messages = True

    # Store full audio bytes from file specified in the path above for Batch.
    interaction_data.audio_handler.init_full_audio_bytes()
    # For non-batch operations, load audio data into a buffer.
    interaction_data.audio_handler.init_audio_buffer()

    ####### Define Settings #######
    # AMD interactions utilize numerous settings that may affect the flow of the interaction.
    # Most settings are optional but some may affect the flow and performance of the interaction.

    # Define variables to use for audio consume settings. This will affect the processing type (Batch/Streaming) and
    # determine when we push audio.
    audio_consume_mode = settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING
    stream_start_location = (
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    # Determine whether to use VAD or not (VAD is required for AMD).
    use_vad = True

    audio_consume_settings = (
        settings_helper.define_audio_consume_settings(audio_consume_mode=audio_consume_mode,
                                                      stream_start_location=stream_start_location))
    amd_settings = settings_helper.define_amd_settings()  # default AMD settings
    vad_settings = settings_helper.define_vad_settings(use_vad=use_vad)

    interaction_data.amd_settings = amd_settings
    interaction_data.audio_consume_settings = audio_consume_settings
    interaction_data.vad_settings = vad_settings

    ####### Return Interaction Data #######
    return interaction_data


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    user_interaction_data = amd_interaction_data_setup(lumenvox_api_client=lumenvox_api)
    lumenvox_api.run_user_coroutine(amd(lumenvox_api_client=lumenvox_api, amd_interaction_data=user_interaction_data))

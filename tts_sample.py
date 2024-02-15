"""
Text-to-Speech (TTS) Sample
This script will run through a session utilizing a TTS interaction.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/4.6.0/tts-integration

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/4.6.0/tts-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/4.6.0/tts-configuration
"""
import uuid

# LumenVox API handling code.
import lumenvox_api_handler
# Our custom helper functions for settings.
from helpers import settings_helper

# Import code/data needed to interaction with the API.
# Our default deployment and operator IDs are stored in the lumenvox_api_handler.
from lumenvox_api_handler import deployment_id
from lumenvox_api_handler import operator_id
from lumenvox_api_handler import LumenVoxApiClient

# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ


class TtsInteractionData:
    """
    A class containing data to be used in TTS interactions.
    See the interaction_create_tts function defined in the lumenvox_api_handler.py file for more information
    on the data used in this class.
    """
    text: str = None
    ssml_url: str = None

    language_code: str = None
    audio_format = None

    save_tts_audio: bool = False
    tts_audio_output_filename: str = None

    tts_inline_synthesis_settings = None

    correlation_id: str = None


async def tts(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient, tts_interaction_data: TtsInteractionData):
    """
    TTS Sample function

    Here we define the text we want to synthesis, and then initialize processing upon InteractionCreateTts.

    The general flow for TTS interactions goes as follows:
    SessionCreate -> InteractionCreateTTS -> InteractionClose -> SessionClose

    :param tts_interaction_data: Data class to use to initiate a TTS interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    ####### Session/Interaction Data #######
    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    correlation_id = tts_interaction_data.correlation_id

    ####### Session Stream initialization and SessionCreate #######
    # session_init is a function that will initialize the session stream for the API, and provide a session UUID with
    # SessionCreate.
    session_stream, session_id = \
        await lumenvox_api_client.session_init(deployment_uuid=deployment_id, operator_uuid=operator_id,
                                               correlation_uuid=correlation_id)

    ####### InteractionCreateTTS #######
    # This is used to create the TTS interaction. Processing of the request will automatically begin upon creation.
    await lumenvox_api_client.interaction_create_tts(
        session_stream=session_stream,
        language=tts_interaction_data.language_code,
        inline_text=tts_interaction_data.text,
        ssml_url=tts_interaction_data.ssml_url,
        audio_format=tts_interaction_data.audio_format,
        tts_inline_synthesis_settings=tts_interaction_data.tts_inline_synthesis_settings,
        correlation_id=correlation_id)

    # Wait for response containing interaction ID to be returned from the API.
    response = await lumenvox_api.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = response.interaction_create_tts.interaction_id

    ####### Result #######
    # Check for a final result returned from the Session.
    # The final result message can be stored into a variable for further assessment once the interaction or session
    # finishes.
    final_result = await lumenvox_api_client.get_session_final_result(session_stream=session_stream)

    ####### AudioPull #######
    # We can receive the audio from the TTS interaction with this function that will call SessionAudioPull until all the
    # audio (in bytes) has been received from the interaction.
    audio_bytes = await lumenvox_api.audio_pull_all(session_stream=session_stream, audio_id=interaction_id)

    # The audio from the TTS interaction can be saved to a file with the named specified above.
    if tts_interaction_data.save_tts_audio:
        # Save the audio file if a proper filename was provided.
        filepath = tts_interaction_data.tts_audio_output_filename

        if filepath is None:
            raise ValueError("Please provide a proper file path to save TTS audio with.")

        # Write audio bytes to file.
        with (open(filepath, "wb")
              as binary_file):
            binary_file.write(audio_bytes)

    ####### InteractionClose #######
    # Once we receive the result and there's nothing left to do, we close the interaction.
    await lumenvox_api_client.interaction_close(session_stream=session_stream, interaction_id=interaction_id,
                                                correlation_id=correlation_id)

    ####### SessionClose #######
    # Similarly, we close the session if there are no other interactions.
    await lumenvox_api_client.session_close(session_stream=session_stream, correlation_id=correlation_id)

    ####### Other #######
    # If desired, the final result can be checked here.
    # A successful TTS interaction will provide a status of FINAL_RESULT_STATUS_TTS_READY.
    print("TTS final result:\n", final_result)

    # As we run other tasks to read response from the API, we have this function to kill those tasks once we're finished
    # with this interaction/session.
    lumenvox_api_client.kill_stream_reader_tasks()


def tts_interaction_data_setup() -> TtsInteractionData:
    """
    Use this function to set up interaction data used for the TTS interaction.
    :return:
    """

    interaction_data = TtsInteractionData()

    # Text to run through synthesis.
    interaction_data.text = "Hello world"

    # Code of language to use for the interaction.
    interaction_data.language_code = 'en-us'

    interaction_data.save_tts_audio = True
    interaction_data.tts_audio_output_filename = "tts-sample.ulaw"

    # Define an audio format for ULAW 8kHz. See the audio_helper file referenced above for more information on the
    # data within these messages.
    interaction_data.audio_format = AUDIO_FORMAT_ULAW_8KHZ

    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    interaction_data.correlation_id = str(uuid.uuid4())

    # Optionally, settings for inline TTS interactions can be provided.
    inline_settings = settings_helper.define_tts_inline_synthesis_settings()
    interaction_data.tts_inline_synthesis_settings = inline_settings

    return interaction_data


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow us
    # to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    user_interaction_data = tts_interaction_data_setup()
    lumenvox_api.run_user_coroutine(tts(lumenvox_api_client=lumenvox_api, tts_interaction_data=user_interaction_data))

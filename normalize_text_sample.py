"""
Normalize Text Sample
This script will demonstrate an interaction using normalize text functionality.

Further information on text normalization can be located here:
https://developer.lumenvox.com/4.6.0/asr-functional-overview#section/Transcription-ASR-Post-Processing

Further information on how to handle sessions & interactions can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects
"""
import uuid

# LumenVox API handling code.
import lumenvox_api_handler

# Our custom helper functions for settings.
from helpers import settings_helper

# Import code/data needed to interact with the API.
# Our default deployment and operator IDs are stored in the lumenvox_api_handler.
from lumenvox_api_handler import deployment_id
from lumenvox_api_handler import operator_id
from lumenvox_api_handler import LumenVoxApiClient


class NormalizeTextInteractionData:
    """
    A class containing data to be used in NormalizeText interactions.
    See the interaction_create_normalize_text function defined in the lumenvox_api_handler.py file for more information
    on the data used in this class.
    """
    transcript: str = ''
    language_code: str = ''

    normalization_settings = None
    correlation_id: str = ''


async def normalize_text(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient,
                         normalize_text_interaction_data: NormalizeTextInteractionData):
    """
    Normalize Text Sample Function

    Here we define the input text (transcript), and then initialize the interaction which will process the NormalizeText
    request upon creation.

    The general flow for NormalizeText goes as follows:
    SessionCreate -> InteractionCreateNormalizeText -> InteractionClose -> SessionClose

    :param normalize_text_interaction_data: Object of NormalizeTextInteractionData containing variables used for the
    interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    :return:
    """
    ####### Session/Interaction Data #######
    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    correlation_id = normalize_text_interaction_data.correlation_id

    ####### Session Stream initialization and SessionCreate #######
    # session_init is a function that will initialize the session stream for the API, and provide a session UUID to
    # SessionCreate.
    session_stream, session_id = \
        await lumenvox_api_client.session_init(
            deployment_uuid=deployment_id, operator_uuid=operator_id, correlation_uuid=correlation_id)

    ####### InteractionCreateNormalizeText #######
    # Create the NormalizeText interaction.
    # Upon creation, the interaction will process the transcript and provide a normalized result based on the
    # settings and data defined in normalize_text_interaction_data.
    await lumenvox_api_client.interaction_create_normalize_text(
        session_stream=session_stream,
        language=normalize_text_interaction_data.language_code,
        normalization_settings=normalize_text_interaction_data.normalization_settings,
        transcript=normalize_text_interaction_data.transcript,
        correlation_id=correlation_id)

    # Wait for response containing interaction ID to be returned from the API.
    response = await lumenvox_api_client.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = response.interaction_create_normalize_text.interaction_id

    ####### Result #######
    # Check for a final result returned from the Session.
    # The final result message can be stored into a variable for further assessment once the interaction or session
    # finishes.
    final_result = await lumenvox_api_client.get_session_final_result(session_stream=session_stream, wait=5)

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

    # If desired, the final result can be checked here. If successful, the API will provide a result with the status of
    # FINAL_RESULT_STATUS_TEXT_NORMALIZE_RESULT.
    return final_result


def normalize_text_interaction_data_setup() -> NormalizeTextInteractionData:
    """
    Use this function to set up interaction data used for the NormalizeText interaction.
    :return: Object containing data to run the interaction with.
    """
    interaction_data = NormalizeTextInteractionData()

    # Define the text to normalize.
    interaction_data.transcript = 'will the meeting take place on october fifteenth'

    # The user is required to specify a language.
    interaction_data.language_code = 'en'

    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    interaction_data.correlation_id = str(uuid.uuid4())

    interaction_data.normalization_settings = (
        settings_helper.define_normalization_settings(
            enable_inverse_text=True,
            enable_redaction=True,
            enable_punctuation_capitalization=True))

    return interaction_data


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    user_interaction_data = normalize_text_interaction_data_setup()
    lumenvox_api.run_user_coroutine(
        normalize_text(lumenvox_api_client=lumenvox_api, normalize_text_interaction_data=user_interaction_data))

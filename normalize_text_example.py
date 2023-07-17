import lumenvox.api.settings_pb2 as settings_msg
from lumenvox_helper_function import LumenVoxApiClient


async def normalize_text_interaction(lumenvox_api,
                                     language: str = 'en', transcript: str = None,
                                     normalization_settings: settings_msg.NormalizationSettings = None,
                                     deployment_id: str = None, operator_id: str = None, correlation_id: str = None):
    """

    :param lumenvox_api: Helper class for LumenVox client api
    :param language: Language code
    :param transcript: Text to run through normalization
    :param normalization_settings: Settings needed to trigger normalization functionality (see settings.proto)
    :param deployment_id: unique UUID of the deployment to use for the session
    :param operator_id: optional unique UUID can be used to track who is making API calls
    :param correlation_id: optional UUID can be used to track individual API calls
    :return:
    """

    # initialize session and receive its stream and ID
    session_stream, session_id = await lumenvox_api.session_init(deployment_id=deployment_id,
                                                                 operator_id=operator_id,
                                                                 correlation_id=correlation_id)

    # normalize text interaction here; a transcript and normalization settings message is required
    await lumenvox_api.interaction_create_normalize_text(session_stream=session_stream,
                                                         language=language,
                                                         transcript=transcript,
                                                         normalization_settings=normalization_settings,
                                                         correlation_id=correlation_id)

    # receive interaction ID after creating the interaction
    r = await lumenvox_api.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = r.interaction_create_normalize_text.interaction_id
    print("interaction_id extracted from interaction_create_normalize_text response is:", interaction_id)

    # attempt to retrieve a result at this point
    await lumenvox_api.get_session_final_result(session_stream=session_stream, wait=30)

    # close interaction and session
    await lumenvox_api.handle_interaction_close_all(session_stream=session_stream, interaction_id=interaction_id)


if __name__ == '__main__':
    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # Define normalization settings here. These are how normalization is enabled.
    normalization_settings = settings_msg.NormalizationSettings()
    normalization_settings.enable_inverse_text.value = True
    normalization_settings.enable_redaction.value = True
    normalization_settings.enable_punctuation_capitalization.value = True

    lumenvox_api.run_user_coroutine(
        normalize_text_interaction(lumenvox_api=lumenvox_api,
                                   language='en',
                                   normalization_settings=normalization_settings,
                                   transcript='will the meeting take place on october fifteenth')
    )

    lumenvox_api.shutdown_lumenvox_api_client()

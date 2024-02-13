# common.proto messages
import lumenvox.api.common_pb2 as common_msg

from lumenvox_helper_function import LumenVoxApiClient


async def create_api_session(lumenvox_api,
                             deployment_id: str = None, operator_id: str = None, correlation_id: str = None):
    """
    Creates LumenVox API session.

    :param lumenvox_api: Helper class for LumenVox client api
    :param deployment_id: unique UUID of the deployment to use for the session
      (default deployment id will be used if not specified)
    :param operator_id: optional unique UUID can be used to track who is making API calls
    :param correlation_id: optional UUID can be used to track individual API calls
    :return: Stream and ID of the session
    """

    # generate new session stream and session
    session_stream, session_id = await lumenvox_api.session_init(deployment_id=deployment_id,
                                                                 operator_id=operator_id,
                                                                 correlation_id=correlation_id)

    return session_stream, session_id


async def grammar_parse_interaction(lumenvox_api,
                                    language_code: str = None, input_text: str = None,
                                    grammars: list = None, deployment_id: str = None, operator_id: str = None,
                                    correlation_id: str = None):
    """

    :param lumenvox_api: Helper class for LumenVox client api
    :param language_code: two or four character code specifying the language of the interaction
    :param deployment_id: unique UUID of the deployment to use for the session
    :param operator_id: optional unique UUID can be used to track who is making API calls
    :param correlation_id: ptional UUID can be used to track individual API calls
      (default deployment id will be used if not specified)
    :param grammars: List of grammar messages to run Grammar parse on.
    """

    # create session and set up audio codec and sample rate
    session_stream, session_id = await create_api_session(lumenvox_api,
                                                          deployment_id=deployment_id,
                                                          operator_id=operator_id,
                                                          correlation_id=correlation_id)

    grammar_settings = lumenvox_api.define_grammar_settings()

    # InteractionCreateGrammarParse Request
    await lumenvox_api.interaction_create_grammar_parse(session_stream=session_stream,
                                                        grammars=grammars,
                                                        input_text=input_text,
                                                        language=language_code,
                                                        grammar_settings=grammar_settings,
                                                        correlation_id=correlation_id)

    # wait for response containing interaction ID to be returned
    r = await lumenvox_api.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = r.interaction_create_grammar_parse.interaction_id
    print("interaction_id extracted from interaction_create_grammar_parse response is:", interaction_id)

    # attempt to retrieve a result at this point
    await lumenvox_api.get_session_final_result(session_stream=session_stream, wait=30)

    await lumenvox_api.handle_interaction_close_all(session_stream=session_stream, interaction_id=interaction_id)


if __name__ == '__main__':
    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # list for passing in more than one grammar to the interaction
    grammar_msgs = [
        LumenVoxApiClient.inline_grammar_by_file_ref(
            grammar_reference='../test_data/Grammar/en-US/en_digits.grxml')
    ]

    lumenvox_api.run_user_coroutine(
        grammar_parse_interaction(lumenvox_api=lumenvox_api,
                                  language_code='en-us',
                                  input_text='ONE TWO THREE FOUR',
                                  grammars=grammar_msgs)
    )

    lumenvox_api.shutdown_lumenvox_api_client()

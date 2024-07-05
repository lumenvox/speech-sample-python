"""
Grammar Parse Sample
This script will run through a session utilizing a GrammarParse interaction.

Information on how to handle sessions & interaction can be found here:
https://developer.lumenvox.com/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/cpa-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/cpa-configuration
"""
import uuid

# LumenVox API handling code.
import lumenvox_api_handler

# Import helper functions for grammar files.
from helpers import grammar_helper

# Import code/data needed to interact with the API.
# Our default deployment and operator IDs are stored in the lumenvox_api_handler.
from lumenvox_api_handler import deployment_id
from lumenvox_api_handler import operator_id
from lumenvox_api_handler import LumenVoxApiClient


class GrammarParseInteractionData:
    """
    A class containing data to be used in GrammarParse interactions.
    See the interaction_create_grammar_parse function defined in the lumenvox_api_handler.py file for more information
    on the data used in this class.
    """
    input_text: str = None
    language_code: str = None

    grammar_messages: list = None

    correlation_id: str = None


async def grammar_parse(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient,
                        grammar_parse_interaction_data: GrammarParseInteractionData):
    """
    Grammar Parse Sample Function

    Here we define the input text and grammar(s) used for parsing, then initialize the GrammarParse interaction.

    The general flow for GrammarParse goes as follows:
    SessionCreate -> InteractionCreateGrammarParse -> InteractionClose -> SessionClose

    :param grammar_parse_interaction_data: Object of GrammarParseInteractionData containing variables used for the
    interaction.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    """

    ####### Session/Interaction Data #######
    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    correlation_id = grammar_parse_interaction_data.correlation_id

    ####### Session Stream initialization and SessionCreate #######
    # session_init is a function that will initialize the session stream for the API, and provide a session UUID with
    # SessionCreate.
    session_stream, session_id = \
        await lumenvox_api_client.session_init(
            deployment_uuid=deployment_id, operator_uuid=operator_id, correlation_uuid=correlation_id)

    ####### InteractionCreateGrammarParse #######
    # GrammarParse Interaction is created; the resulting ID is stored into variable.
    # Note that, for GrammarParse, interaction processing starts on interaction creation.
    await lumenvox_api_client.interaction_create_grammar_parse(
        session_stream=session_stream,
        language=grammar_parse_interaction_data.language_code,
        input_text=grammar_parse_interaction_data.input_text,
        grammars=grammar_parse_interaction_data.grammar_messages,
        correlation_id=correlation_id)

    # Wait for response containing interaction ID to be returned from the API.
    response = await lumenvox_api_client.get_session_general_response(session_stream=session_stream)
    interaction_id = response.interaction_create_grammar_parse.interaction_id

    ####### Result #######
    # Check for a final result returned from the Session.
    # The final result message can be stored into a variable for further assessment once the interaction or session
    # finishes.
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

    # If desired, the final result can be checked here. If the proper text and grammars were provided, then we should
    # a final result with a success status of FINAL_RESULT_STATUS_GRAMMAR_MATCH
    return final_result


def grammar_parse_interaction_data_setup() -> GrammarParseInteractionData:
    """
    Use this function to set up interaction data used for the GrammarParse interaction.
    :return: Object containing data to run the interaction with.
    """
    interaction_data = GrammarParseInteractionData()

    # Correlation IDs aren't required, but can be useful in tracking messages sent to/from the API.
    interaction_data.correlation_id = str(uuid.uuid4())

    interaction_data.input_text = "ONE TWO THREE FOUR"  # input text to parse from grammar(s)
    interaction_data.language_code = "EN-US"  # language code used for parsing/grammars

    # Multiple grammars can be defined and passed into the interaction.
    grammar_1 = grammar_helper.inline_grammar_by_file_ref('./sample_data/Grammar/en-US/en_digits.grxml')
    interaction_data.grammar_messages = [grammar_1]

    return interaction_data


if __name__ == '__main__':
    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    user_interaction_data = grammar_parse_interaction_data_setup()
    lumenvox_api.run_user_coroutine(
        grammar_parse(lumenvox_api_client=lumenvox_api, grammar_parse_interaction_data=user_interaction_data))

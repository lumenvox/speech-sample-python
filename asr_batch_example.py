# common.proto messages
import lumenvox.api.common_pb2 as common_msg
# settings.proto messages
import lumenvox.api.settings_pb2 as settings_msg
# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats

from lumenvox_helper_function import LumenVoxApiClient


async def asr_batch_interaction(lumenvox_api,
                                audio_file: str = None, audio_format: int = None, sample_rate_hertz: int = None,
                                language_code: str = None, grammar_file_ref: str = None,
                                builtin_voice_grammar: common_msg.Grammar = None, grammar_url: str = None,
                                deployment_id: str = None, operator_id: str = None, correlation_id: str = None,
                                ):
    """
    Common ASR (batch processing) coroutine

    @param lumenvox_api: Helper class for LumenVox client api
    @param audio_file: audio file to use for session audio
    @param audio_format: audio format enum from StandardAudioFormat
    @param sample_rate_hertz: audio sample rate
    @param language_code: two or four character code specifying the language of the interaction
    @param grammar_file_ref: String reference to grammar file
    @param grammar_url: URL of the grammar to use instead of inline
    @param builtin_voice_grammar: Enum for builtin grammar
    @param deployment_id: unique UUID of the deployment to use for the session
    @param operator_id: optional unique UUID can be used to track who is making API calls
    @param correlation_id: optional UUID can be used to track individual API calls
      (default deployment id will be used if not specified)
    """

    # # create session and set up audio codec and sample rate
    # the function session_init is an helper function to create the grpc channel and the session
    session_stream, session_id = await lumenvox_api.session_init(deployment_id=deployment_id,
                                                                         operator_id=operator_id,
                                                                         correlation_id=correlation_id)

    # Setting the sample rate and audio format for the audio we want to recognize
    await lumenvox_api.session_set_inbound_audio_format(session_stream=session_stream,
                                                                audio_format=audio_format, sample_rate_hertz=sample_rate_hertz)

    # with batch mode, all audio is sent before creating an interaction. The binary audio data is here added to the session audio resource.
    # session_audio_push is a helper function that takes audio_data as bytes and sends the data within a protobuf message over gRPC
    await lumenvox_api.session_audio_push(session_stream=session_stream,
                                                  audio_data=lumenvox_api.get_audio_file(filename=audio_file))

    # set audio usage as batch mode, and have processing for the interaction start at the beginning of all audio sent
    audio_consume_settings = lumenvox_api.define_audio_consume_settings(
        audio_consume_mode=
        settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_BATCH,
        stream_start_location=
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_STREAM_BEGIN)

    # use voice activity detection
    vad_settings = lumenvox_api.define_vad_settings(use_vad=True)

    # Set a default language in case a language is not detected
    if not language_code:
        language_code = 'en-us'

    # Settings related to recognition results
    recognition_settings = lumenvox_api.define_recognition_settings()

    # Settings related to SRGS grammar usage
    grammar_settings = lumenvox_api.define_grammar_settings()

    # define at least one grammar and append them to a list to parse into InteractionCreateGrammarParse
    grammars = []
    if isinstance(grammar_file_ref, str):
        if grammar_file_ref:
            grammar = lumenvox_api.define_grammar(
                inline_grammar_text=lumenvox_api.get_grammar_file_by_ref(grammar_file_ref))
            grammars.append(grammar)
    elif isinstance(builtin_voice_grammar, int):
        grammar = lumenvox_api.define_grammar(builtin_voice_grammar=builtin_voice_grammar)
        grammars.append(grammar)
    elif isinstance(grammar_file_ref, list):
        n = len(grammar_file_ref)
        for i in range(n):
            g = lumenvox_api.define_grammar(
                inline_grammar_text=lumenvox_api.get_grammar_file_by_ref(grammar_file_ref[i]))
            grammars.append(g)
    elif grammar_url:
        grammar = lumenvox_api.define_grammar(grammar_url=grammar_url)
        grammars.append(grammar)

    # ask the asr to decode the audio file performing an InteractionCreateAsrRequest request
    await lumenvox_api.interaction_create_asr(session_stream=session_stream, grammars=grammars, language=language_code,
                                                      audio_consume_settings=audio_consume_settings, vad_settings=vad_settings,
                                                      recognition_settings=recognition_settings,
                                                      grammar_settings=grammar_settings)

    # wait for response containing interaction ID to be returned.
    # the helper function get_session_general_response attempts to receive a general response from the respective queue
    r = await lumenvox_api.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = r.interaction_create_asr.interaction_id
    print("interaction_id extracted from interaction_create_asr response is:", interaction_id)

    # attempt to retrieve a result at this point.
    # the helper function "get_session_final_result" retrieves the final result response of the given session stream if available
    await lumenvox_api.get_session_final_result(session_stream=session_stream, wait=30)

    #
    await lumenvox_api.handle_interaction_close_all(session_stream=session_stream, interaction_id=interaction_id)


if __name__ == '__main__':
    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # the function asr_batch_interaction creates session, and runs an interaction
    # this needs to be passed as a coroutine into lumenvox_api.run_user_coroutine, so that the event loop
    # to handle gRPC async messages is created
    lumenvox_api.run_user_coroutine(
        asr_batch_interaction(lumenvox_api=lumenvox_api,
                              audio_file='../test_data/Audio/en/1234-1s-front-1s-end.ulaw',
                              audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW,
                              sample_rate_hertz=8000,
                              language_code='en',
                              grammar_file_ref='../test_data/Grammar/en-US/en_digits.grxml',
                              ), )

    lumenvox_api.shutdown_lumenvox_api_client()

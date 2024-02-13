# common.proto messages
import os
import sys

import lumenvox.api.common_pb2 as common_msg
# settings.proto messages
import lumenvox.api.settings_pb2 as settings_msg
# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats

from lumenvox_helper_function import LumenVoxApiClient


async def asr_batch_interaction(lumenvox_api,
                                audio_file: str = None, audio_format: int = None, sample_rate_hertz: int = None,
                                language_code: str = None, grammar_messages: list = None,
                                builtin_voice_grammar: common_msg.Grammar = None,
                                deployment_id: str = None, operator_id: str = None, correlation_id: str = None,
                                csv_file=None
                                ):
    """
    Common ASR (batch processing) coroutine

    :param lumenvox_api: Helper class for LumenVox client api
    :param audio_file: audio file to use for session audio
    :param audio_format: audio format enum from StandardAudioFormat
    :param sample_rate_hertz: audio sample rate
    :param language_code: two or four character code specifying the language of the interaction
    :param grammar_file_ref: String reference to grammar file
    :param grammar_url: URL of the grammar to use instead of inline
    :param builtin_voice_grammar: Enum for builtin grammar
    :param deployment_id: unique UUID of the deployment to use for the session
    :param operator_id: optional unique UUID can be used to track who is making API calls
    :param correlation_id: optional UUID can be used to track individual API calls
      (default deployment id will be used if not specified)
    :param csv_file: Reference to CSV file to write to.
    """

    # create session and set up audio codec and sample rate
    # the function session_init is a helper function to create the grpc channel and the session
    session_stream, session_id = await lumenvox_api.session_init(deployment_id=deployment_id,
                                                                 operator_id=operator_id,
                                                                 correlation_id=correlation_id)

    # Setting the sample rate and audio format for the audio we want to recognize
    await lumenvox_api.session_set_inbound_audio_format(session_stream=session_stream,
                                                        audio_format=audio_format,
                                                        sample_rate_hertz=sample_rate_hertz)

    # With batch mode, all audio is sent before creating an interaction.
    # The binary audio data is here added to the session audio resource.
    # Session_audio_push is a helper function that takes audio_data as bytes and
    # sends the data within a protobuf message over gRPC.
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

    # ask the asr to decode the audio file performing an InteractionCreateAsrRequest request
    await lumenvox_api.interaction_create_asr(session_stream=session_stream, grammars=grammar_messages,
                                              language=language_code, audio_consume_settings=audio_consume_settings,
                                              vad_settings=vad_settings, recognition_settings=recognition_settings,
                                              grammar_settings=grammar_settings)

    # wait for response containing interaction ID to be returned.
    # the helper function get_session_general_response attempts to receive a general response from the respective queue
    r = await lumenvox_api.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = r.interaction_create_asr.interaction_id
    print("interaction_id extracted from interaction_create_asr response is:", interaction_id)

    # Attempt to retrieve a result at this point.
    # The helper function "get_session_final_result" retrieves the final result response of the given session stream.
    result = await lumenvox_api.get_session_final_result(session_stream=session_stream, wait=30)

    # write results to CSV if specified
    if csv_file:
        fields = [
            audio_file,
            session_id,
            interaction_id,
            str(result.final_result_status) if result else 'No result',
            result.final_result.asr_interaction_result.n_bests[0].asr_result_meta_data.transcript
            if result else 'No result'
        ]

        fields_str = ''
        for f in fields:
            fields_str += (f + ',') if (fields[-1] != f) else f

        fields_str += '\n'
        csv_file.write(fields_str)

    await lumenvox_api.handle_interaction_close_all(session_stream=session_stream, interaction_id=interaction_id)

if __name__ == '__main__':
    # Modified version of the ASR batch sample script to process multiple audio files and write results to CSV.
    # sys.argv[1] - CSV file to write to
    # sys.argv[2] - Directory to read from
    # (optional) sys.argv[3:] - Audio file extensions to limit to

    if len(sys.argv) < 3:
        print("Invalid number of arguments")
        print("sys.argv[1] - CSV file to get audio file paths from")
        print("sys.argv[2] - CSV file to write to")
        print("(optional) sys.argv[3:] - Audio file extensions to limit to")

        sys.exit()

    extensions: list = None if len(sys.argv) < 4 else sys.argv[3:]

    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    results_csv = open(sys.argv[2], "a")
    results_csv.write("audio_file_ref, session_id, interaction_id, final_result_status, transcript\n")

    # Specify your grammars here
    grammar_msgs = [
        LumenVoxApiClient.inline_grammar_by_file_ref(
            grammar_reference='../test_data/Grammar/en-US/en_transcription.grxml'
        )
    ]

    # loop through files referenced in CSV and run ASR interaction
    with open(sys.argv[1]) as csv_file:
        c = False
        filepath = ''

        for line in csv_file:
            # skip first line of file
            if not c:
                c = True
                continue

            split_line = line.split(',')

            if extensions:
                for e in extensions:
                    if split_line[0].endswith(e):
                        filepath = split_line[0]
                        break
            else:
                filepath = split_line[0]

            if filepath:
                lumenvox_api.run_user_coroutine(
                    asr_batch_interaction(
                        lumenvox_api=lumenvox_api,
                        audio_file=filepath,
                        audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW,
                        sample_rate_hertz=8000,
                        language_code='en',
                        grammar_messages=grammar_msgs,
                        csv_file=results_csv
                    ),
                )

    lumenvox_api.shutdown_lumenvox_api_client()

    results_csv.close()

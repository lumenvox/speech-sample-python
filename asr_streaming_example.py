import json
import time

from lumenvox.api.speech.v1 import speech_pb2 as speech_api
from lumenvox_speech_helper import LumenVoxSpeechApiHelper


def asr_streaming_common(api_helper, audio_file, grammar_file_path=None, grammar_url=None,
                         language_code=None, audio_format=None):
    """
    This function will launch a streaming decode using the specified parameters

    Streaming decodes send several chunks of audio, which use Voice Activity Detection (VAD) to determine when
    human speech has started and ended, which can then trigger processing of the result.
    """

    session_id = api_helper.SessionCreate()
    print('1. session_id from SessionCreate: ', session_id)

    api_helper.AudioStreamCreate(session_id=session_id, audio_format=audio_format)
    print('2. Called AudioStreamCreate - no response expected')

    grammar_ids = api_helper.load_grammar_helper(session_id=session_id, language_code=language_code,
                                                 grammar_file_path=grammar_file_path, grammar_url=grammar_url)

    interaction_id = api_helper.InteractionCreateASR(session_id=session_id, interaction_ids=grammar_ids)
    print('3. interaction_id extracted from InteractionCreateASR response is: ', interaction_id)

    # Settings for streaming decodes
    interaction_test_json_string = '{"INTERACTION_AUDIO_CONSUME": ' \
                                   '{' \
                                   '   "AUDIO_CONSUME_MODE": "STREAMING", ' \
                                   '   "AUDIO_CONSUME_START_MODE":"STREAM_BEGIN"} ' \
                                   '}'
    api_helper.InteractionSetSettings(session_id=session_id, interaction_id=interaction_id,
                                      json_settings_string=interaction_test_json_string)

    api_helper.InteractionBeginProcessing(session_id=session_id, interaction_id=interaction_id)
    print('4. called InteractionBeginProcessing for ASR (no response expected) interaction_id: ', interaction_id)

    # Load audio buffer with specified audio file contents
    audio_stream_buffer = api_helper.load_audio_stream_buffer(audio_file_path=audio_file,
                                                              stream_chunk_bytes=4000)

    more_bytes = True
    chunk_counter = 0
    while more_bytes is True:
        # In this loop, we're streaming audio into the Speech API from the buffer we loaded above based on the
        # file we specified. During this loop, we may get various callbacks that can be handled if needed
        more_bytes = api_helper.AudioStreamingPush(session_id=session_id, audio_stream_buffer=audio_stream_buffer)
        chunk_counter += 1
        # Only here to show streamed audio is being sent
        print("sending audio chunk ", chunk_counter, " more bytes = ", str(more_bytes))

        # See if we got a VAD callback without delaying (timeout_value=0)
        vad_callback = api_helper.get_vad_callback(session_id=session_id, timeout_value=0)
        if vad_callback is not None:
            # We received a vad_callback here. We could do something with it.
            print("## Got vad callback", vad_callback.VadMessageEventType.Name(vad_callback.vad_message_type),
                  "interaction_id", vad_callback.interaction_id, "session_id", vad_callback.session_id)

        # Check if we got a PARTIAL RESULT callback without delaying (timeout_value=0)
        partial_result_callback = api_helper.get_partial_result_callback(session_id=session_id, timeout_value=0)
        if partial_result_callback is not None:
            # We received a partial result callback here. We could do something with it.
            print("## Got partial result callback for interaction_id", partial_result_callback.interaction_id,
                  "session_id", partial_result_callback.session_id)
            got_partial_result = api_helper.InteractionRequestResults(session_id=session_id,
                                                                      interaction_id=interaction_id)
            if got_partial_result and api_helper.result_ready:
                partial_json = json.loads(api_helper.results_response.results_json)
                print("Partial results: ", str(partial_json))

        # See if we got a RESULT callback without delaying (timeout_value=0)
        result_callback = api_helper.get_result_callback(session_id=session_id, timeout_value=0)
        if result_callback is not None:
            if type(result_callback) == speech_api.InteractionFinalResultsReadyMessage:
                if result_callback.session_id != session_id:
                    print("## Got InteractionFinalResultsReadyMessage for incorrect session_id ",
                          result_callback.session_id)
                else:
                    if result_callback.interaction_id in grammar_ids:
                        print("## Got InteractionFinalResultsReadyMessage for grammar_id ",
                              result_callback.interaction_id)
                    elif result_callback.interaction_id == interaction_id:
                        print("## Got InteractionFinalResultsReadyMessage for ASR interaction_id ",
                              result_callback.interaction_id)
                        # If we receive this message, it indicates the result is ready, we can stop streaming
                        break

        # Small pause between sent audio chunks (to emulate realtime streaming)
        time.sleep(0.1)

    print('5. Completed streaming audio')

    api_helper.wait_for_final_results(session_id=session_id, interaction_id=interaction_id)

    print('6. Final Results ready:', str(api_helper.result_ready))

    if api_helper.result_ready:
        # Only attempt to parse the results_json if result_ready is True (otherwise results_json is not valid)
        parsed_json = json.loads(api_helper.results_response.results_json)
    else:
        parsed_json = None

    api_helper.InteractionClose(session_id=session_id, interaction_id=interaction_id)
    api_helper.SessionClose(session_id=session_id)

    return parsed_json


if __name__ == '__main__':

    # Create and initialize the API helper object that will be used to simplify the example code
    api_helper = LumenVoxSpeechApiHelper()
    api_helper.initialize_speech_api_helper()

    result = asr_streaming_common(api_helper=api_helper,
                                  grammar_file_path='test_data/en_digits.grxml',
                                  audio_file='test_data/1234.ulaw',
                                  audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                                  language_code='en')

    print(">>>> result returned:\n", json.dumps(result, indent=4, sort_keys=True))

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    api_helper.shutdown_speech_api_helper()

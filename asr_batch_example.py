import json
import time

from lumenvox_speech_helper import LumenVoxSpeechApiHelper


def asr_batch_common(api_helper, audio_file, grammar_file_path=None, grammar_url=None,
                     language_code=None, audio_format=None):
    """
    This function will launch a batch decode using the specified parameters

    Batch decodes load all audio at once and requests processing to begin. It does not perform Voice Activity
    Detection (VAD)
    """

    session_id = api_helper.SessionCreate(audio_format)
    print('1. session_id from SessionCreate: ', session_id)

    audio_data_to_push = api_helper.get_audio_file(audio_file_path=audio_file)
    api_helper.AudioPush(session_id=session_id, audio_data=audio_data_to_push)
    print('2. Called AudioStreamPush - no response expected')

    grammar_ids = api_helper.load_grammar_helper(session_id=session_id, language_code=language_code,
                                                 grammar_file_path=grammar_file_path, grammar_url=grammar_url)

    interaction_id = api_helper.InteractionCreateASR(session_id=session_id, interaction_ids=grammar_ids)
    print('3. interaction_id extracted from InteractionCreateASR response is: ', interaction_id)

    # add setting for batch decoding.
    interaction_test_json_string = '{' \
                                   '    "INTERACTION_AUDIO_CONSUME": ' \
                                   '    {' \
                                   '        "AUDIO_CONSUME_MODE": "BATCH", ' \
                                   '        "AUDIO_CONSUME_START_MODE": "STREAM_BEGIN" ' \
                                   '    }' \
                                   '}'
    api_helper.InteractionSetSettings(session_id=session_id, interaction_id=interaction_id,
                                      json_settings_string=interaction_test_json_string)

    # Reset the final_result event so that we wait for the decode event (not the grammar events above)
    api_helper.reset_result_event(session_id=session_id)

    print('session id before InteractionBeginProcessing: ', session_id)
    api_helper.InteractionBeginProcessing(session_id=session_id, interaction_id=interaction_id)
    print('4. called InteractionBeginProcessing for ASR (no response expected) interaction_id: ', interaction_id)

    api_helper.wait_for_final_results(session_id=session_id, interaction_id=interaction_id, wait_time=3.5)
    print('5. Final Results ready:', str(api_helper.result_ready))

    if api_helper.result_ready:
        # Only attempt to parse the results_json if results_ready is True (otherwise results_json is not valid)
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

    result = asr_batch_common(api_helper=api_helper,
                              grammar_file_path='test_data/en_digits.grxml',
                              audio_file='test_data/1234.ulaw',
                              audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                              language_code='en')

    print(">>>> result returned:\n", json.dumps(result, indent=4, sort_keys=True, ensure_ascii=False))

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    api_helper.shutdown_speech_api_helper()

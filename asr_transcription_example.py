import json
import threading
import time

from lumenvox.api.speech.v1 import speech_pb2 as speech_api
from lumenvox_speech_helper import LumenVoxSpeechApiHelper


def asr_transcription_common(api_helper, audio_file, grammar_file_path=None, grammar_url=None,
                             language_code=None, audio_format=None):
    """
    This function will launch a transcription decode using the specified parameters

    This is very similar to streaming mode, except that transcription uses a special grammar to activate
    transcription mode, and typically processes lengthier audio. Also note that transcription can be performed
    using VAD mode (as shown here), or could be performed in batch-mode (similar to batch example) for offline,
    or non-realtime use cases.
    """

    session_id = api_helper.SessionCreate(audio_format)
    print('1. session_id from SessionCreate: ', session_id)

    # api_helper.AudioStreamCreate(session_id=session_id, audio_format=audio_format)
    # print('2. Called AudioStreamCreate - no response expected')

    grammar_ids = api_helper.load_grammar_helper(session_id=session_id, language_code=language_code,
                                                 grammar_file_path=grammar_file_path, grammar_url=grammar_url)

    interaction_id = api_helper.InteractionCreateASR(session_id=session_id, interaction_ids=grammar_ids)
    print('2. interaction_id extracted from InteractionCreateASR response is: ', interaction_id)

    # Settings for streaming decodes
    interaction_test_json_string = '{"INTERACTION_AUDIO_CONSUME": ' \
                                   '{' \
                                   '   "AUDIO_CONSUME_MODE": "STREAMING", ' \
                                   '   "AUDIO_CONSUME_START_MODE":"STREAM_BEGIN"} ' \
                                   '}'
    api_helper.InteractionSetSettings(session_id=session_id, interaction_id=interaction_id,
                                      json_settings_string=interaction_test_json_string)

    # Reset the final_result event so that we wait for the decode event (not the grammar events above)
    api_helper.reset_result_event(session_id=session_id)

    api_helper.InteractionBeginProcessing(session_id=session_id, interaction_id=interaction_id)
    print('3. called InteractionBeginProcessing for ASR (no response expected) interaction_id: ', interaction_id)

    # Load audio buffer with specified audio file contents and start streaming in another thread
    audio_streaming_buffer = api_helper.load_audio_stream_buffer(audio_file_path=audio_file,
                                                                 stream_chunk_bytes=4000)
    audio_stream_cancel = threading.Event()
    api_helper.StartStreaming(session_id=session_id, audio_streaming_buffer=audio_streaming_buffer,
                              cancel_event=audio_stream_cancel)

    while True:
        # In this loop, we're checking the callback channels to see what's happening with the stream. When we receive
        # results, we can set the audio_stream_cancel event to end the stream (which is happening in another thread).

        # See if we got a VAD callback without delaying (timeout_value=0)
        vad_callback = api_helper.get_vad_callback(session_id=session_id, timeout_value=0)
        if vad_callback is not None:
            # We received a vad_callback here. We could do something with it.
            print("## Got vad callback", vad_callback.VadEventType.Name(vad_callback.vad_event_type),
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
            if type(result_callback) == speech_api.FinalResultsReady:
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
                        audio_stream_cancel.set()
                        break

        # Small pause between sent audio chunks (to emulate realtime streaming)
        time.sleep(0.1)

    print('4. Completed streaming audio')

    api_helper.wait_for_final_results(session_id=session_id, interaction_id=interaction_id)

    print('5. Final Results ready:', str(api_helper.result_ready))

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

    # Audio sample courtesy of Open Speech Repository: https://www.voiptroubleshooter.com/open_speech/index.html
    result = asr_transcription_common(api_helper=api_helper,
                                      grammar_file_path='test_data/en_transcription.grxml',
                                      audio_file='test_data/OSR_us_000_0037_8k.ulaw',
                                      audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                                      language_code='en')

    # Note that prior to final result, there are several PARTIAL RESULT CALLBACK messages showing partial
    # results while the audio is being processed in realtime. The final result may contain a corrected version
    # of the partial results, since it may have more context around words and phrases to improve final output.

    print(">>>> result returned:\n", json.dumps(result, indent=4, sort_keys=True))

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    api_helper.shutdown_speech_api_helper()

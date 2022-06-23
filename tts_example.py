import json
import os
import time

from lumenvox_speech_helper import LumenVoxSpeechApiHelper


def tts_common(api_helper, text=None, ssml_url=None, voice=None,
               language_code=None, audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
               save_audio_file=False):
    """
    This function will request a TTS synthesis using the specified parameters
    """

    session_id = api_helper.SessionCreate('STANDARD_AUDIO_FORMAT_NO_AUDIO_RESOURCE')
    print('1. session_id from SessionCreate: ', session_id)

    if text:
        interaction_id = api_helper.InteractionCreateTTS(session_id=session_id, language=language_code,
                                                         text=text, voice=voice,
                                                         audio_format=audio_format)
    else:
        interaction_id = api_helper.InteractionCreateTTS(session_id=session_id, language=language_code,
                                                         ssml_url=ssml_url, voice=voice,
                                                         audio_format=audio_format)

    api_helper.InteractionBeginProcessing(session_id=session_id, interaction_id=interaction_id)

    # Wait until we receive the final results callback
    api_helper.wait_for_final_results(session_id=session_id, interaction_id=interaction_id, wait_time=3.5)

    api_helper.InteractionRequestResults(session_id=session_id, interaction_id=interaction_id)

    parsed_json = json.loads(api_helper.results_response.results_json)

    if 'synth_warnings' in parsed_json:
        print("Synthesis warnings: ", len(parsed_json['synth_warnings']))
        for warning in parsed_json['synth_warnings']:
            print('Synth warning reported: ', warning)

    print(f"PARSED JSON: \n{json.dumps(parsed_json, indent=4, ensure_ascii=False)}")

    print("SSML marks synthesized: ", len(parsed_json['synth_ssml_mark_offsets']))
    for entry in parsed_json['synth_ssml_mark_offsets']:
        print(" - mark Name: [", entry['name'], "] at offset:", entry['offset'])

    if 'synth_word_sample_offsets' in parsed_json:
        print("Words synthesized: ", len(parsed_json['synth_word_sample_offsets']))
        print("Sentences synthesized: ", len(parsed_json['synth_sentence_sample_offsets']))
        print("Voice used: ", parsed_json['synth_voice_sample_offsets'][0]['name'])

    audio_id = parsed_json["audio_id"]
    audio_data_len, audio_data = api_helper.AudioPull(session_id=session_id, interaction_id=audio_id)

    output_filepath = None
    if save_audio_file:
        file_type = '.ulaw'
        if audio_format == 'STANDARD_AUDIO_FORMAT_ALAW_8KHZ':
            file_type = '.alaw'
        if audio_format in ['STANDARD_AUDIO_FORMAT_PCM_8KHZ', 'STANDARD_AUDIO_FORMAT_PCM_16KHZ',
                            'STANDARD_AUDIO_FORMAT_PCM_22KHZ']:
            file_type = '.pcm'
        output_filepath = api_helper.create_audio_file(session_id=session_id, byte_array=audio_data,
                                                       file_type=file_type)

    api_helper.InteractionClose(session_id=session_id, interaction_id=interaction_id)
    api_helper.SessionClose(session_id=session_id)
    return audio_data_len, output_filepath


if __name__ == '__main__':

    # Create and initialize the API helper object that will be used to simplify the example code
    api_helper = LumenVoxSpeechApiHelper()
    api_helper.initialize_speech_api_helper()

    # Set to True to save the generated synthesized audio file
    save_audio_file = False

    ssml_text = api_helper.get_ssml_file_by_ref('test_data/mark_element.ssml')
    audio_data_len, output_filepath = tts_common(api_helper=api_helper,
                                                 language_code='en-us', voice='Chris',
                                                 audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                                                 text=ssml_text,
                                                 save_audio_file=save_audio_file)

    print("\nSynthesis completed with ", audio_data_len, "bytes")
    if save_audio_file:
        print(" - saved audio file to ", output_filepath)

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    api_helper.shutdown_speech_api_helper()

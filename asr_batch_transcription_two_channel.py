from lumenvox_helper_function import LumenVoxApiClient
import lumenvox.api.settings_pb2 as settings_msg

# use ASR batch interaction code from example script
from asr_batch_example import asr_batch_interaction
# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats

if __name__ == '__main__':
    # See asr_transcription_example for more information on transcription interactions.

    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # this is a headered WAV file
    audio_file = \
        '../test_data/Audio/en/first_1234_second_mouse_ulaw.wav'

    grammar_msgs = [
        LumenVoxApiClient.inline_grammar_by_file_ref(
            grammar_reference='../test_data/Grammar/en-US/en_transcription.grxml'),
    ]

    vad_settings = settings_msg.VadSettings()
    vad_settings.use_vad.value = True
    vad_settings.eos_delay_ms.value = 3200

    # audio consume settings where we read from the first channel
    audio_consume_settings_first = settings_msg.AudioConsumeSettings()
    audio_consume_settings_first.stream_start_location = 1
    audio_consume_settings_first.audio_consume_mode = 2
    audio_consume_settings_first.audio_channel.value = 0

    # should return 'one two three four'
    lumenvox_api.run_user_coroutine(
        asr_batch_interaction(
            lumenvox_api=lumenvox_api,
            audio_file=audio_file,
            audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_WAV,
            sample_rate_hertz=8000,
            language_code='en',
            grammar_messages=grammar_msgs,
            audio_consume_settings=audio_consume_settings_first,
            vad_settings=vad_settings
        ),
    )

    # audio consume settings where we read from the second channel
    audio_consume_settings_second = settings_msg.AudioConsumeSettings()
    audio_consume_settings_second.stream_start_location = 1
    audio_consume_settings_second.audio_consume_mode = 2
    audio_consume_settings_second.audio_channel.value = 1

    # should return 'mouse'
    lumenvox_api.run_user_coroutine(
        asr_batch_interaction(
            lumenvox_api=lumenvox_api,
            audio_file=audio_file,
            audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_WAV,
            sample_rate_hertz=8000,
            language_code='en',
            grammar_messages=grammar_msgs,
            audio_consume_settings=audio_consume_settings_second,
            vad_settings=vad_settings
        ),
    )

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    lumenvox_api.shutdown_lumenvox_api_client()

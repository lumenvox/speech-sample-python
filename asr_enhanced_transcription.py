from lumenvox_helper_function import LumenVoxApiClient

# Use transcription interaction code provided in asr_transcription_example
from asr_transcription_example import asr_transcription_session


if __name__ == '__main__':
    # See asr_transcription_example for more information on transcription interactions.

    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # List of embedded grammars. At least one is needed for enhanced transcription interactions.
    embedded_grammars = [
        LumenVoxApiClient.inline_grammar_by_file_ref(grammar_reference='../test_data/Grammar/en-US/ABNFDigits.gram'),
        LumenVoxApiClient.define_grammar(builtin_voice_grammar=4),   # built-in "digits" grammar (see common.proto)
        LumenVoxApiClient.inline_grammar_by_file_ref(
            grammar_reference='../test_data/Grammar/en-US/the_man_was_one_hundred_years_old.grxml'
        ),
        LumenVoxApiClient.inline_grammar_by_file_ref(grammar_reference='../test_data/Grammar/en-US/en_animals.gram')
    ]

    audio_file = \
        '../test_data/Audio/en/transcription/passphrase_the_man_was_one_hundred_years_old_passcode_4127_ulaw.raw'

    lumenvox_api.run_user_coroutine(
        asr_transcription_session(lumenvox_api,
                                  language_code='en',
                                  audio_ref=audio_file,
                                  chunk_size=4000,
                                  embedded_grammars=embedded_grammars,
                                  ), )

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    lumenvox_api.shutdown_lumenvox_api_client()

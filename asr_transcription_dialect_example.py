from lumenvox_helper_function import LumenVoxApiClient

# Use transcription interaction code provided in asr_transcription_example
from asr_transcription_example import asr_transcription_session


if __name__ == '__main__':
    # Here we run two transcription interactions, one using EN-US, the other EN-GB.
    # See asr_transcription_example for more information on transcription interactions.

    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    audio_file = '../test_data/Audio/en/transcription/for_the_catalog_ulaw.raw'

    # EN-US interaction; note the words 'catalog', 'organize,' and 'color'.
    lumenvox_api.run_user_coroutine(
        asr_transcription_session(lumenvox_api,
                                  language_code='en-us',
                                  audio_ref=audio_file,
                                  chunk_size=4000,
                                  ), )

    # Here, in the EN-GB transcription, the words are 'catalogue', 'organise,' and 'colour.'
    lumenvox_api.run_user_coroutine(
        asr_transcription_session(lumenvox_api,
                                  language_code='en-gb',
                                  audio_ref=audio_file,
                                  chunk_size=4000,
                                  ), )

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    lumenvox_api.shutdown_lumenvox_api_client()

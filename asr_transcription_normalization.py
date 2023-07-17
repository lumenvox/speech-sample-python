from lumenvox_helper_function import LumenVoxApiClient
import lumenvox.api.settings_pb2 as settings_msg
from lumenvox.api.settings_pb2 import NormalizationSettings

# Use transcription interaction code provided in asr_transcription_example
from asr_transcription_example import asr_transcription_session


if __name__ == '__main__':
    # See asr_transcription_example for more information on transcription interactions.

    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # Define normalization settings here. These are how normalization is enabled.
    normalization_settings = NormalizationSettings()
    normalization_settings.enable_inverse_text.value = True
    normalization_settings.enable_redaction.value = True
    normalization_settings.enable_punctuation_capitalization.value = True

    # "Will the meeting take place on October 15?"
    audio_file = \
        '../test_data/Audio/en/transcription/meeting.raw'

    # Note that we get four output strings (verbalized, verbalized_redacted, final, final_redacted) in addition to the
    # transcript.
    lumenvox_api.run_user_coroutine(
        asr_transcription_session(lumenvox_api,
                                  language_code='en',
                                  audio_ref=audio_file,
                                  chunk_size=4000,
                                  normalization_settings=normalization_settings)
    )

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    lumenvox_api.shutdown_lumenvox_api_client()

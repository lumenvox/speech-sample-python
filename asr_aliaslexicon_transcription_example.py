# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats

from lumenvox_helper_function import LumenVoxApiClient

# import the interaction function from asr_batch_example since we're using batch here
from asr_batch_example import asr_batch_interaction


if __name__ == '__main__':
    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # Inline grammar text, using a lexicon reference to a public XML file.
    # The lexicon file contains words 'zero', 'oh', and 'naught' as aliases for the grapheme 'Zero'
    inline_grammar_text = \
        """<?xml version='1.0'?>
        <grammar xml:lang="en" version="1.0" root="root" mode="voice"
                 xmlns="http://www.w3.org/2001/06/grammar"
                 tag-format="semantics/1.0.2006">

            <meta name="TRANSCRIPTION_ENGINE" content="V2"/>
            <lexicon uri="https://assets.lumenvox.com/lexicon/zero_lexicon.xml"/>       
            <rule id="root" scope="public">
                <item>

                </item>
            </rule>
        </grammar>
        """

    # Audio file saying "zero, oh, naught"; should be returned as "Zero Zero Zero" per the grammar and lexicon above
    audio_file = '../test_data/Audio/en/transcription/zero_oh_naught.raw'

    grammar_msgs = [
        LumenVoxApiClient.define_grammar(inline_grammar_text=inline_grammar_text)
    ]

    # the function asr_batch_interaction creates session, and runs an interaction
    # this needs to be passed as a coroutine into lumenvox_api.run_user_coroutine, so that the event loop
    # to handle gRPC async messages is created
    lumenvox_api.run_user_coroutine(
        asr_batch_interaction(lumenvox_api=lumenvox_api,
                              audio_file='../test_data/Audio/en/transcription/zero_oh_naught.raw',
                              audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW,
                              sample_rate_hertz=8000,
                              language_code='en',
                              grammar_messages=grammar_msgs,
                              ), )

    lumenvox_api.shutdown_lumenvox_api_client()

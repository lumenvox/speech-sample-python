"""
Transcription TSV Script.
This script will run interactions based on the provided TSV file and write the results to the specified TSV.

This script utilizes code written in the transcription_sample.py script. Refer to that script and the linked documents
for more information on running Transcription interactions.

Refer to the integration diagrams found here:
https://developer.lumenvox.com/asr-integration#section/INTEGRATION-WORKFLOWS/Transcription

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/asr-configuration
"""

import sys

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code.
import lumenvox_api_handler

# Our custom helper functions.
from helpers import settings_helper

# Import code needed to interact with the API.
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences.
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ

from transcription_sample import TranscriptionInteractionData
from transcription_sample import transcription


def process_interactions(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient, tsv_read_file_path: str,
                         tsv_result_file_path: str, extensions: list = None, normalization_enabled: bool = False):
    # Define an audio format for ULAW 8kHz. See the audio_helper file referenced above for more information on the
    # data within these messages.
    audio_format_msg = AUDIO_FORMAT_ULAW_8KHZ

    # Define variables to use for audio consume settings. This will affect the processing type (Batch/Streaming) and
    # determine when we push audio.
    # Since the function handles streaming, we will need AUDIO_CONSUME_MODE_STREAMING.
    audio_consume_mode = settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING

    # A stream start location of STREAM_START_LOCATION_INTERACTION_CREATED or
    # STREAM_START_LOCATION_BEGIN_PROCESSING_CALL is required for ASR streaming functionality
    stream_start_location = (
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    audio_consume_settings = (
        settings_helper.define_audio_consume_settings(audio_consume_mode=audio_consume_mode,
                                                      stream_start_location=stream_start_location))
    recognition_settings = settings_helper.define_recognition_settings()
    vad_settings = settings_helper.define_vad_settings(use_vad=False)

    normalization_settings = None

    # Open the result file in the specified path and write the first line.
    results_tsv = open(tsv_result_file_path, "a")

    tsv_header_string = "audio_file_ref\tinteraction_id\tfinal_result_status\ttranscript\tword_confidence_scores\n"

    if normalization_enabled:
        # Modify header string to include normalization content.
        tsv_header_string = tsv_header_string.rstrip('\n')  # Strip out the \n
        tsv_header_string += "\tnorm_verbalized\tnorm_verbalized_redacted\tnorm_final\tnorm_final_redacted\n"

        # Define Normalization settings if enabled.
        normalization_settings = (
            settings_helper.define_normalization_settings(
                enable_inverse_text=True,
                enable_redaction=True,
                enable_punctuation_capitalization=True))

    results_tsv.write(tsv_header_string)

    # Loop through files referenced in TSV and run ASR interactions.
    with (open(tsv_read_file_path) as tsv_file):
        first_line_read = False
        filepath = ''

        # Loop through each line in file.
        for line in tsv_file:
            # skip first line of file
            if not first_line_read:
                first_line_read = True
                continue

            split_line = line.split('\t')
            # Take out any line-ending characters or tabs from the string. This is needed to check for extensions.
            split_line[0] = split_line[0].rstrip('\n').rstrip('\r').rstrip('\t')

            # Grab the filepath from the TSV entry.
            # Check for extensions if provided.
            if extensions:
                for ext in extensions:
                    if split_line[0].endswith(ext):
                        filepath = split_line[0]
                        break
            else:
                filepath = split_line[0]

            if filepath:
                # Construct interaction data for the current audio file.
                interaction_data = TranscriptionInteractionData()
                interaction_data.language_code = 'en-us'
                interaction_data.audio_consume_settings = audio_consume_settings
                interaction_data.recognition_settings = recognition_settings
                interaction_data.vad_settings = vad_settings
                interaction_data.normalization_settings = normalization_settings
                interaction_data.audio_handler = \
                    AudioHandler(
                        audio_file_path=filepath,
                        audio_format=audio_format_msg,
                        lumenvox_api_client=lumenvox_api_client,
                        chunk_audio=True,
                        audio_push_chunk_size_bytes=4000,
                        audio_push_sleep_override=0.1,
                    )

                # Run the coroutine for the file referenced in the TSV.
                coroutine = transcription(lumenvox_api_client=lumenvox_api_client,
                                          transcription_interaction_data=interaction_data)

                # The function that handles the interaction will be run alongside the stream-reading tasks.
                # Upon finishing, the tasks will provide return values as a tuple. run_user_coroutine returns those
                # values, the first of which being the result needed for this script.
                loop_run_return_values = lumenvox_api_client.run_user_coroutine(user_coroutine=coroutine)
                final_result_msg = loop_run_return_values[0]

                # Write results to TSV file.
                write_result_info_to_tsv(tsv_file=results_tsv, result_msg=final_result_msg, audio_file_ref=filepath,
                                         normalization_enabled=normalization_enabled)


def write_result_info_to_tsv(tsv_file, result_msg, audio_file_ref: str, normalization_enabled: bool = False):
    """
    Write final result and related information to TSV file.
    :param normalization_enabled: Whether normalization has been enabled.
    :param audio_file_ref: Audio file path string.
    :param tsv_file: TSV file to write results to.
    :param result_msg: Result message returned from the API.
    """

    # Define array of fields with final result information.
    fields = [
        audio_file_ref,
        result_msg.interaction_id if result_msg else "No result\t",
        str(result_msg.final_result_status) if result_msg else "No result\t",
        result_msg.final_result.transcription_interaction_result.n_bests[0].asr_result_meta_data.transcript
        if result_msg else "No result\t"
    ]

    # Loop through words in results and pair them with confidence scores in a string.
    if result_msg:
        words = result_msg.final_result.transcription_interaction_result.n_bests[0].asr_result_meta_data.words

        word_conf_str = "{"

        for word in words:
            word_conf_str += word.word + " : " + str(word.confidence) + ", "

        # Remove last comma and space before adding '}'
        word_conf_str = word_conf_str[:-2] + "}\t"
    else:
        word_conf_str = "No result\t"

    fields.append(word_conf_str)

    # Add normalization result contents if enabled.
    if normalization_enabled:
        if result_msg:
            normalized_result = result_msg.final_result.transcription_interaction_result.n_bests[0].normalized_result

            fields.append(normalized_result.verbalized)
            fields.append(normalized_result.verbalized_redacted)
            fields.append(normalized_result.final)
            fields.append(normalized_result.final_redacted)
        else:
            for num in range(4):
                fields.append("No result\t")

    # Populate a string that will be inserted as a line in the results TSV.
    fields_str = ''
    for f in fields:
        fields_str += (f + '\t')

    fields_str = fields_str.rstrip('\t')    # Strip last \t before newline.
    fields_str += '\n'
    tsv_file.write(fields_str)


def print_available_sys_args():
    """
    Print system arguments upon error.
    :return:
    """
    print("sys.argv[1] - TSV file to get audio file paths from")
    print("sys.argv[2] - TSV file to write to")
    print("(optional) sys.argv[3:] - Normalization flag and Audio file extensions to limit to.")
    print("Ex.:")
    print('python3 transcription_tsv.py "C:\test_audio_ref_file.tsv" results.tsv -norm 1 -ext .raw -ext .ulaw')


if __name__ == '__main__':
    """
    Modified version of the ASR batch sample script to process multiple audio files and write results to TSV.
    sys.argv[1] - TSV file to get audio file paths from.
    sys.argv[2] - TSV file to write to.
    (optional) sys.argv[3:] - Normalization flag and Audio file extensions to limit to.
        "-norm 1" - enable normalization
        "-ext .ulaw -ext .alaw" - File extensions 

    Ex.:
    python3 transcription_tsv.py "C:\test_audio_ref_file.tsv" results.tsv -norm 1 -ext .raw -ext .ulaw

    The TSV that is read should only contain the header followed by a list of the audio files on each line.
    Example:
    audio_file_ref
    C:\audio1.raw
    C:\audio2.raw
    C:\audio3.raw

    """

    if len(sys.argv) < 3:
        print("Invalid number of arguments")
        print_available_sys_args()

        sys.exit()

    tsv_file_path = sys.argv[1]
    tsv_result_path = sys.argv[2]

    # This will grab the list of other arguments if one or more were provided.
    other_options: list = None if (len(sys.argv) < 4) else sys.argv[3:]

    enable_normalization = False
    file_extensions = None

    if other_options:
        # Iterate through other provided arguments and determine normalization flag/
        for i in range(len(other_options)):
            try:
                if other_options[i] == '-norm':
                    enable_normalization = True if int(other_options[i + 1]) else False
                if other_options[i] == '-ext':
                    if not file_extensions:
                        file_extensions = []
                    file_extensions.append(other_options[i + 1])
            except IndexError:
                print("Arguments incorrectly formatted.")
                print_available_sys_args()

    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    # Run through interactions here (and specify different grammars or settings if need be).
    process_interactions(lumenvox_api_client=lumenvox_api, tsv_read_file_path=tsv_file_path,
                         tsv_result_file_path=tsv_result_path, extensions=file_extensions,
                         normalization_enabled=enable_normalization)

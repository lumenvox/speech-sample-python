"""
ASR Batch TSV Script.
This script will run interactions based on the provided TSV file and write the results to the specified TSV.

This script utilizes code written in the asr_batch_sample.py script. Refer to that script and the linked documents
for more information on running ASR interactions.

Example to run:
python3 asr_batch_transcription_tsv.py "C:\test_audio_ref_file.tsv" results.tsv .raw .ulaw

Refer to the integration diagrams found here:
https://developer.lumenvox.com/4.6.0/asr-integration#section/INTEGRATION-WORKFLOWS/ASR

Further information on how to handle sessions, interactions and audio handling can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects

Further information on the API calls / proto file can be found here:
https://developer.lumenvox.com/4.6.0/asr-lumenvox.proto

Further information on configuration settings can be found here:
https://developer.lumenvox.com/4.6.0/asr-configuration
"""
import sys

# Import protocol buffer messages from settings.
import lumenvox.api.settings_pb2 as settings_msg

# LumenVox API handling code.
import lumenvox_api_handler

# Our custom helper functions.
from helpers import grammar_helper
from helpers import settings_helper

# Import code needed to interact with the API.
from lumenvox_api_handler import LumenVoxApiClient

# Import AudioHandling code to assist with AudioPush sequences.
from helpers.audio_helper import AudioHandler
# Import the AudioFormat used in this file.
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ

# Import InteractionData and ASR batch function from the asr_batch_sample.py script.
from asr_batch_sample import AsrInteractionData
from asr_batch_sample import asr_batch


def process_interactions(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient, tsv_read_file_path: str,
                         tsv_result_file_path: str, extensions: list = None):
    """
    Function to run interactions in a loop based on the contents provided in tsv_read_file_path.
    Specify grammars and settings in this particular function if necessary.

    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    :param tsv_read_file_path: Path to TSV file listing audio files to run interactions on.
    :param tsv_result_file_path: Path to TSV to save results to.
    :param extensions: List of strings for limiting the extensions to use.
    """

    # Specify grammars here.
    grammar_msgs = [
        grammar_helper.inline_grammar_by_file_ref(
            grammar_reference='../sample_data/Grammar/en-US/en_transcription.grxml')
    ]

    # Define an audio format for ULAW 8kHz. See the audio_helper file referenced above for more information on the
    # data within these messages.
    audio_format_msg = AUDIO_FORMAT_ULAW_8KHZ

    # Define settings here. See the other ASR/Transcription sample scripts for more information.
    audio_consume_mode = settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_BATCH
    # A stream start location of STREAM_START_LOCATION_STREAM_BEGIN is required for ASR batch processing.
    stream_start_location = (
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_STREAM_BEGIN)

    audio_consume_settings = (
        settings_helper.define_audio_consume_settings(audio_consume_mode=audio_consume_mode,
                                                      stream_start_location=stream_start_location))
    recognition_settings = settings_helper.define_recognition_settings()
    vad_settings = settings_helper.define_vad_settings(use_vad=True)

    # Open the result file in the specified path and write the first line.
    results_tsv = open(tsv_result_file_path, "a")
    results_tsv.write("audio_file_ref\tinteraction_id\tfinal_result_status\ttranscript\n")

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
                # Take out any line-ending characters or tabs from the string.
                filepath = filepath.rstrip('\n').rstrip('\r').rstrip('\t')

                # Construct interaction data for the current audio file.
                interaction_data = AsrInteractionData()
                interaction_data.language_code = 'en-us'
                interaction_data.audio_consume_settings = audio_consume_settings
                interaction_data.recognition_settings = recognition_settings
                interaction_data.vad_settings = vad_settings
                interaction_data.audio_handler = \
                    AudioHandler(
                        audio_file_path=filepath,
                        audio_format=audio_format_msg,
                        lumenvox_api_client=lumenvox_api_client,
                        chunk_audio=False)
                interaction_data.grammar_messages = grammar_msgs

                # Run the coroutine for the file referenced in the TSV.
                coroutine = asr_batch(lumenvox_api_client=lumenvox_api_client,
                                      asr_interaction_data=interaction_data)

                # The function that handles the interaction will be run alongside the stream-reading tasks.
                # Upon finishing, the tasks will provide return values as a tuple. run_user_coroutine returns those
                # values, the first of which being the result needed for this script.
                loop_run_return_values = lumenvox_api_client.run_user_coroutine(user_coroutine=coroutine)
                final_result_msg = loop_run_return_values[0]

                # Write results to TSV file.
                write_result_info_to_tsv(tsv_file=results_tsv, result_msg=final_result_msg, audio_file_ref=filepath)


def write_result_info_to_tsv(tsv_file, result_msg, audio_file_ref: str):
    """
    Write final result and related information to TSV file.
    :param audio_file_ref: Audio file path string.
    :param tsv_file: TSV file to write results to.
    :param result_msg: Result message returned from the API.
    """

    # Define array of fields with final result information.
    fields = [
        audio_file_ref,
        result_msg.interaction_id,
        str(result_msg.final_result_status) if result_msg else 'No result',
        result_msg.final_result.asr_interaction_result.n_bests[0].asr_result_meta_data.transcript
        if result_msg else 'No result'
    ]

    # Populate a string that will be inserted as a line in the results TSV.
    fields_str = ''
    for f in fields:
        fields_str += (f + '\t') if (fields[-1] != f) else f

    fields_str += '\n'
    tsv_file.write(fields_str)


if __name__ == '__main__':
    """
    Modified version of the ASR batch sample script to process multiple audio files and write results to TSV.
    sys.argv[1] - TSV file to get audio file paths from.
    sys.argv[2] - TSV file to write to.
    (optional) sys.argv[3:] - Audio file extensions to limit to.
    
    Ex.:
    python3 asr_batch_transcription_tsv.py "C:\test_audio_ref_file.tsv" results.tsv .raw .ulaw
    
    The TSV that is read should only contain the header followed by a list of the audio files on each line.
    Example:
    audio_file_ref
    C:\audio1.raw
    C:\audio2.raw
    C:\audio3.raw

    """

    if len(sys.argv) < 3:
        print("Invalid number of arguments")
        print("sys.argv[1] - TSV file to get audio file paths from")
        print("sys.argv[2] - TSV file to write to")
        print("(optional) sys.argv[3:] - Audio file extensions to limit to")

        sys.exit()

    tsv_file_path = sys.argv[1]
    tsv_result_path = sys.argv[2]

    # This will grab the list of extensions if one or more are provided.
    file_extensions: list = None if (len(sys.argv) < 4) else sys.argv[3:]

    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()

    # Run through interactions here (and specify different grammars or settings if need be).
    process_interactions(lumenvox_api_client=lumenvox_api, tsv_read_file_path=tsv_file_path,
                         tsv_result_file_path=tsv_result_path, extensions=file_extensions)

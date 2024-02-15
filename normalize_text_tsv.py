"""
Normalize Text Sample
This script will run interactions based on the provided TSV file and write the results to the specified TSV.
See the normalize_text_sample.py script for more details on the process, as this script borrows heavily from its
contents.

Example command:
py normalize_text_from_tsv.py input.tsv output.tsv

Further information on text normalization can be located here:
https://developer.lumenvox.com/4.6.0/asr-functional-overview#section/Transcription-ASR-Post-Processing

Further information on how to handle sessions & interactions can be found here:
https://developer.lumenvox.com/4.6.0/platform#section/Platform-Objects
"""
import sys

# LumenVox API handling code.
import lumenvox_api_handler

# Our custom helper functions for settings.
from helpers import settings_helper

# Import code needed to interact with the API.
from lumenvox_api_handler import LumenVoxApiClient

# Import class to hold NormalizeText interaction data, and the function that carries out the interaction process.
from normalize_text_sample import NormalizeTextInteractionData
from normalize_text_sample import normalize_text


def process_interactions(lumenvox_api_client: lumenvox_api_handler.LumenVoxApiClient, tsv_read_file_path: str,
                         tsv_result_file_path: str):
    """
    Function to run interactions in a loop based on the contents provided in tsv_read_file_path.
    Specify settings in this particular function if necessary.
    :param lumenvox_api_client: Our class that interacts with the LumenVox API and wraps its gRPC functions.
    :param tsv_read_file_path: Path to TSV file listing transcriptions to run interactions on.
    :param tsv_result_file_path: Path to TSV to save results to.
    """
    results_tsv = open(tsv_result_file_path, "a")
    results_tsv.write("Reference\ttranscript_text\tverbalized\tverbalized_redacted\tfinal\tfinal_redacted\n")

    # Define the settings we want the normalization to use.
    normalization_settings = (
        settings_helper.define_normalization_settings(
            enable_inverse_text=True,
            enable_redaction=True,
            enable_punctuation_capitalization=True))

    # Loop through files referenced in TSV and run ASR interactions.
    with (open(tsv_read_file_path) as tsv_file):
        first_line_read = False

        # Loop through each line in file.
        for line in tsv_file:
            # Skip first line of file.
            if not first_line_read:
                first_line_read = True
                continue

            # Splits lines over tabs into array.
            split_line = line.split('\t')

            reference_value = split_line[0]

            # Strip any possible '\n' or '\r' character from the end to prevent formatting errors.
            transcript = split_line[1].rstrip('\n').rstrip('\r')

            # Construct interaction data for each NormalizeText interaction.
            interaction_data = NormalizeTextInteractionData()
            interaction_data.transcript = transcript
            interaction_data.normalization_settings = normalization_settings
            interaction_data.language_code = 'en'

            # Set up a coroutine to run the interaction based on the TSV entry.
            # This will be used to run through the interaction process defined in the normalize_text_sample.py script.
            coroutine = \
                normalize_text(lumenvox_api_client=lumenvox_api_client,
                               normalize_text_interaction_data=interaction_data)

            # The function that handles the interaction will be run alongside the stream-reading tasks.
            # Upon finishing, the tasks will provide return values as a tuple. run_user_coroutine returns those values,
            # the first of which being the result needed for this script.
            loop_run_return_values = lumenvox_api_client.run_user_coroutine(user_coroutine=coroutine)
            final_result_msg = loop_run_return_values[0]

            # Write final result, reference value and transcript to TSV.
            write_result_info_to_tsv(tsv_file=results_tsv, result_msg=final_result_msg,
                                     reference_value=reference_value, transcript=transcript)


def write_result_info_to_tsv(tsv_file, result_msg, reference_value: str, transcript: str):
    """
    Write final result and related information to TSV file.
    :param transcript: Transcript that normalization was used on.
    :param reference_value: Reference value for the transcript.
    :param tsv_file: TSV file to write results to.
    :param result_msg: Result message returned from the API.
    """

    # Define array of fields with final result information.
    # If no result was provided in time, it will be represented in the result TSV.
    if not result_msg:
        fields = [reference_value, transcript, "", "", "", "", ""]
        fields[2:] = ['no result'] * (len(fields) - 2)
    else:
        fields = [
            reference_value,
            transcript.rstrip(),
            result_msg.final_result.normalize_text_result.normalized_result.verbalized,
            result_msg.final_result.normalize_text_result.normalized_result.verbalized_redacted,
            result_msg.final_result.normalize_text_result.normalized_result.final,
            result_msg.final_result.normalize_text_result.normalized_result.final_redacted
        ]

    # Populate a string that will be inserted as a line in the results TSV.
    fields_str = ''
    for f in fields:
        fields_str += (f + '\t')

    # Remove the tab character from end of line.
    fields_str = fields_str[:-1]
    # Add new line character at the end.
    fields_str += '\n'
    tsv_file.write(fields_str)


if __name__ == '__main__':
    """
    Modified version of the Normalize Text sample script to allow for reading from TSV and outputting results to TSV.
    sys.argv[1] - TSV file to read from
    sys.argv[2] - TSV file to write to
    
    The TSV being read will need to be of following format, with tabs as separators and a header for the first line:
    reference	transcript
    0	will the meeting take place on october fifteenth
    1	my email address is a b c at gmail dot com

    Ex.: 
    py normalize_text_from_tsv.py input.tsv output.tsv
    """

    if len(sys.argv) < 3:
        print("Invalid number of arguments")
        print("sys.argv[1] - TSV file to read from")
        print("sys.argv[2] - TSV file to write to")

        sys.exit()

    tsv_file_path = sys.argv[1]
    tsv_result_path = sys.argv[2]

    # Initialize the LumenVoxApiClient class which houses the underlying read/write API functions, as well as allow the
    # user to run sessions as tasks along with other tasks to read responses from the API.
    lumenvox_api = LumenVoxApiClient()
    process_interactions(tsv_read_file_path=tsv_file_path, tsv_result_file_path=tsv_result_path,
                         lumenvox_api_client=lumenvox_api)

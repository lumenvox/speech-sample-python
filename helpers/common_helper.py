""" Helper functions
This file contains functions useful for interacting with the LumenVox API.
"""

# common.proto messages.
import lumenvox.api.common_pb2 as common_msg
# optional_values.proto messages
import lumenvox.api.optional_values_pb2 as optional_values
# interaction.proto messages.
import lumenvox.api.interaction_pb2 as interaction_msg

""" Optional Values
The following three functions wrap over the 'Optional' types prevalent in the LumenVox protocol buffer files.
See optional_values.proto for more information.
"""


def optional_bool(value: bool) -> optional_values.OptionalBool:
    """
    Returns OptionalBool message containing the given value.
    """
    return optional_values.OptionalBool(value=value)


def optional_string(value: str) -> optional_values.OptionalString:
    """
    Returns OptionalString message containing the given value.
    """
    return optional_values.OptionalString(value=value)


def optional_int32(value: int) -> optional_values.OptionalInt32:
    """
    Returns OptionalInt32 message containing the given value.
    """
    return optional_values.OptionalInt32(value=value)


"""Other helpers
"""


def define_transcription_phrase_list(phrases: list = None,
                                     global_phrase_list: str = None,
                                     session_phrase_list: str = None) -> interaction_msg.TranscriptionPhraseList:
    """
    Construct a TranscriptionPhraseList message (interaction.proto).
    :param phrases: Optional list of strings containing words and phrases.
    :param global_phrase_list: Optional reference to previously defined global phrase list(s) (common.proto).
    :param session_phrase_list: Optional reference to previously defined session phrase list(s) (common.proto).
    :return: TranscriptionPhraseList message (interaction.proto).
    """
    transcription_phrase_list = interaction_msg.TranscriptionPhraseList(
        phrases=phrases,
        # Check if the variable is None before providing a Phrase List message.
        global_phrase_list=
        common_msg.PhraseList(phrase_list_label=global_phrase_list) if global_phrase_list else None,
        # Check if the variable is None before providing a Phrase List message.
        session_phrase_list=
        common_msg.PhraseList(phrase_list_label=session_phrase_list) if session_phrase_list else None)

    return transcription_phrase_list

""" Grammar Helpers
As grammars are commonplace in LumenVox call flows, it may save time to have additional helpers to wrap over and
provide grammar messages.
"""

# This library is used for file opening.
import os

# common.proto messages.
import lumenvox.api.common_pb2 as common_msg


def define_grammar(grammar_url: str = None, inline_grammar_text: str = None, global_grammar_label: str = None,
                   session_grammar_label: str = None, builtin_voice_grammar: int = None,
                   builtin_dtmf_grammar: int = None, label: str = None) -> common_msg.Grammar:
    """
    Build a grammar message (defined in common.proto).
    Returns grammar message.

    :param grammar_url: A grammar URL to be loaded.
    :param inline_grammar_text: A string containing the raw grammar text.
    :param global_grammar_label: Reference to a previously defined "global" grammar.
    :param session_grammar_label: Reference to a previously defined "session" grammar.
    :param builtin_voice_grammar: Reference to a "builtin" voice grammar.
    :param builtin_dtmf_grammar: Reference to a "builtin" DTMF grammar.
    :param label: Optional label assigned to grammar, used for error reporting.
    """

    grammar_msg = common_msg.Grammar()

    if grammar_url:
        grammar_msg.grammar_url = grammar_url
    elif inline_grammar_text:
        grammar_msg.inline_grammar_text = inline_grammar_text
    elif global_grammar_label:
        grammar_msg.global_grammar_label = global_grammar_label
    elif session_grammar_label:
        grammar_msg.session_grammar_label = session_grammar_label
    elif builtin_voice_grammar:
        grammar_msg.builtin_voice_grammar = builtin_voice_grammar
    elif builtin_dtmf_grammar:
        grammar_msg.builtin_dtmf_grammar = builtin_dtmf_grammar

    if label:
        grammar_msg.label.value = label

    return grammar_msg


def inline_grammar_by_file_ref(grammar_reference) -> common_msg.Grammar:
    """
    Load text contents of grammar file into grammar message (common.proto) and return grammar message
    """
    return common_msg.Grammar(
        inline_grammar_text=get_grammar_file_by_ref(grammar_reference=grammar_reference))


def get_grammar_file_by_ref(grammar_reference) -> str:
    """
    Opens the referenced grammar file and returns the contents as a string.

    :param grammar_reference: File path reference to a grammar file.
    :return: String to be used as inline-grammar data.
    """

    if os.path.isfile(grammar_reference):
        # Running from test folder
        grammar_file_path = grammar_reference
    else:
        # Running from command line in parent folder (remove first .)
        grammar_file_path = grammar_reference[1:]

    # Read as UTF-8 by default
    with open(grammar_file_path, 'r', encoding='utf-8') as file:
        data = file.read()

    # Handle ISO-8859-1 encoded grammars...
    if 'iso-8859-1' in data[:70].lower():
        with open(grammar_file_path, 'r', encoding='iso-8859-1') as file:
            data = file.read()
    return data

""" Settings
This file includes functions for wrapping over settings protocol buffer messages found in settings.proto.
These functions aren't necessary, as the messages can be formed directly, but help to highlight the data fields present
within the messages.
"""

# settings.proto messages.
import lumenvox.api.settings_pb2 as settings_msg

# Import optional value functions from common_helper.
from helpers.common_helper import optional_bool
from helpers.common_helper import optional_int32
from helpers.common_helper import optional_string


def define_general_interaction_settings(secure_context: bool = None, custom_interaction_data: str = None,
                                        logging_tag: list = None) -> settings_msg.GeneralInteractionSettings:
    """
    This function wraps a GeneralInteractionSettings message. See settings.proto for more information.
    :param secure_context: Optional value, determines whether to enable secure context.
    :param custom_interaction_data: Optional, not used by LumenVox.
    :param logging_tag: Optional tag for logging. Reserved for future use.
    :return: Provides a GeneralInteractionSettings message (see settings.proto).
    """
    general_interaction_settings = settings_msg.GeneralInteractionSettings()

    general_interaction_settings.secure_context.value = secure_context
    general_interaction_settings.custom_interaction_data.value = custom_interaction_data
    general_interaction_settings.logging_tag = logging_tag

    return general_interaction_settings


def define_grammar_settings(
        default_tag_format: int = settings_msg.GrammarSettings.TagFormat.TAG_FORMAT_SEMANTICS_1_2006,
        ssl_verify_peer: bool = None, load_grammar_timeout_ms: int = None) \
        -> settings_msg.GrammarSettings:
    """
    Construct a GrammarSettings message. See settings.proto for more information.
    :param default_tag_format: The tag-format for loaded grammars. default: TagFormat.TAG_FORMAT_SEMANTICS_1_2006
    :param ssl_verify_peer: If true, https grammar url must have a valid certificate.  default: True
    :param load_grammar_timeout_ms: Timeout to wait for grammar load.  default: 200000ms.
    :return: GrammarSettings protocol buffer message (settings.proto).
    """
    grammar_settings = settings_msg.GrammarSettings(
        default_tag_format=default_tag_format,
        ssl_verify_peer=optional_bool(ssl_verify_peer),
        load_grammar_timeout_ms=optional_int32(load_grammar_timeout_ms))

    return grammar_settings


def define_recognition_settings(max_alternatives: int = None, trim_silence_value: int = None,
                                enable_partial_results: bool = None, confidence_threshold: int = None,
                                decode_timeout: int = None) -> settings_msg.RecognitionSettings:
    """
    Construct a RecognitionSettings message. See settings.proto for more information.
    The defaults are set in the function definition

    :param decode_timeout: Number of milliseconds the ASR should await results before timing out.
    :param max_alternatives: Maximum number of recognition hypotheses to be returned. Default: 1
    :param trim_silence_value: how aggressively the ASR trims leading silence from input audio.
    :param enable_partial_results: When true, partial results callbacks will be enabled for the interaction.
    :param confidence_threshold: Confidence threshold. Range 0 to 1000; applies to grammar based asr interactions.
    :return: RecognitionSettings protocol buffer message (settings.proto).
    """
    recognition_settings = settings_msg.RecognitionSettings(
        max_alternatives=optional_int32(max_alternatives) if max_alternatives is not None else None,
        trim_silence_value=optional_int32(trim_silence_value) if trim_silence_value is not None else None,
        enable_partial_results=optional_bool(enable_partial_results) if enable_partial_results is not None else None,
        confidence_threshold=optional_int32(confidence_threshold) if confidence_threshold is not None else None,
        decode_timeout=optional_int32(decode_timeout) if decode_timeout is not None else None)

    return recognition_settings


def define_normalization_settings(enable_inverse_text: bool = None, enable_punctuation_capitalization: bool = None,
                                  enable_redaction: bool = None, request_timeout_ms: int = None,
                                  enable_srt_generation: bool = None, enable_vtt_generation: bool = None) \
        -> settings_msg.NormalizationSettings:
    """
    Constructs a NormalizationSettings message. See settings.proto for more information.
    :param enable_vtt_generation: Set to true to enable generation of VTT file (WebVTT file format).
    :param enable_srt_generation: Set to true to enable generation of SRT file (SubRip file format).
    :param request_timeout_ms: Number of milliseconds text normalization should await results before timing out.
    :param enable_inverse_text: Set to true to enable inverse text normalization.
    :param enable_punctuation_capitalization: Set to true to enable punctuation and capitalization normalization.
    :param enable_redaction: Set to true to enable redaction of sensitive information.
    :return: NormalizationSettings protocol buffer message (settings.proto).
    """
    normalization_settings = settings_msg.NormalizationSettings(
        enable_inverse_text=optional_bool(enable_inverse_text) if enable_inverse_text is not None else None,
        enable_punctuation_capitalization=optional_bool(enable_punctuation_capitalization)
        if enable_punctuation_capitalization is not None else None,
        enable_redaction=optional_bool(enable_redaction) if enable_redaction is not None else None,
        request_timeout_ms=optional_int32(request_timeout_ms) if request_timeout_ms is not None else None,
        enable_srt_generation=optional_bool(enable_srt_generation) if enable_srt_generation is not None else None,
        enable_vtt_generation=optional_bool(enable_vtt_generation) if enable_vtt_generation is not None else None)

    return normalization_settings


def define_audio_consume_settings(audio_channel: int = None,
                                  audio_consume_mode: int = None,
                                  stream_start_location: int = None,
                                  start_offset_ms: int = None, audio_consume_max_ms: int = None) \
        -> settings_msg.AudioConsumeSettings:
    """
    Constructs an AudioConsumeSettings message. See settings.proto for more information.
    The defaults are set in the function definition

    :param audio_channel: For multi-channel audio, this is the channel number being referenced (Default: 0).
    :param audio_consume_mode: Which audio mode to use.
    :param stream_start_location: Specify where audio consume starts when "streaming" mode is used.
    :param start_offset_ms: Optional offset in milliseconds to adjust the audio start point. (Default: 0)
    :param audio_consume_max_ms: Optional maximum audio to process. Value of 0 means process all audio sent.
    :return: AudioConsumeSettings protocol buffer message (settings.proto).
    """
    audio_consume_settings = settings_msg.AudioConsumeSettings(
        audio_channel=optional_int32(audio_channel) if audio_channel is not None else None,
        audio_consume_mode=audio_consume_mode,
        stream_start_location=stream_start_location,
        start_offset_ms=optional_int32(start_offset_ms) if start_offset_ms is not None else None,
        audio_consume_max_ms=optional_int32(audio_consume_max_ms) if audio_consume_max_ms is not None else None)

    return audio_consume_settings


def define_vad_settings(use_vad: bool = True, barge_in_timeout_ms: int = None, end_of_speech_timeout_ms: int = None,
                        noise_reduction_mode: int = None, bargein_threshold: int = None, eos_delay_ms: int = None,
                        snr_sensitivity: int = None, stream_init_delay: int = None, volume_sensitivity: int = None,
                        wind_back_ms: int = None) -> settings_msg.VadSettings:
    """
    Constructs a VadSettings message. See settings.proto for more information.
    :param use_vad: Enables VAD processing.
    :param barge_in_timeout_ms: Maximum silence, in ms, allowed while waiting for user input (barge-in) before a
        timeout is reported.
    :param end_of_speech_timeout_ms: The time to check for an end-of-speech event.
    :param noise_reduction_mode: (Enum. value) Determines the type of noise reduction used.
    :param bargein_threshold: Affects barge-in sensitivity.
    :param eos_delay_ms: Milliseconds of silence after speech before processing begins.
    :param snr_sensitivity: Determines how much louder the speaker must be than the background noise in order to trigger
        barge-in.
    :param stream_init_delay: Time in milliseconds to determine the acoustic environment for VAD processing.
    :param volume_sensitivity: The volume required to trigger barge-in.
    :param wind_back_ms: The length of audio to be wound back at the beginning of voice activity.
    :return: VadSettings protocol buffer message (settings.proto).
    """
    vad_settings = settings_msg.VadSettings(
        use_vad=optional_bool(use_vad) if use_vad is not None else None,
        barge_in_timeout_ms=optional_int32(barge_in_timeout_ms) if barge_in_timeout_ms is not None else None,
        bargein_threshold=optional_int32(bargein_threshold) if bargein_threshold is not None else None,
        noise_reduction_mode=noise_reduction_mode,
        end_of_speech_timeout_ms=optional_int32(end_of_speech_timeout_ms)
        if end_of_speech_timeout_ms is not None else None,
        eos_delay_ms=optional_int32(eos_delay_ms) if eos_delay_ms is not None else None,
        snr_sensitivity=optional_int32(snr_sensitivity) if snr_sensitivity is not None else None,
        stream_init_delay=optional_int32(stream_init_delay) if stream_init_delay is not None else None,
        volume_sensitivity=optional_int32(volume_sensitivity) if volume_sensitivity is not None else None,
        wind_back_ms=optional_int32(wind_back_ms) if wind_back_ms is not None else None)

    return vad_settings


def define_amd_settings(amd_enable: bool = None, fax_enable: bool = None, sit_enable: bool = None,
                        busy_enable: bool = None, tone_detect_timeout_ms: int = None) -> settings_msg.AmdSettings:
    """
    Constructs an AmdSettings message. See settings.proto for more information.
    :param amd_enable: Enable answering machine beep detection.
    :param fax_enable: Enable fax tone detection.
    :param sit_enable: Enable SIT detection.
    :param busy_enable: Enable busy tone detection.
    :param tone_detect_timeout_ms: Maximum number of milliseconds the tone detection algorithm should listen for input
        before timing out.
    :return: AmdSettings protocol buffer message (settings.proto).
    """
    amd_settings = settings_msg.AmdSettings(
        amd_enable=optional_bool(amd_enable) if amd_enable is not None else None,
        fax_enable=optional_bool(fax_enable) if fax_enable is not None else None,
        sit_enable=optional_bool(sit_enable) if sit_enable is not None else None,
        busy_enable=optional_bool(busy_enable) if busy_enable is not None else None,
        tone_detect_timeout_ms=optional_int32(tone_detect_timeout_ms)
        if (tone_detect_timeout_ms or tone_detect_timeout_ms == 0) else None)

    return amd_settings


def define_cpa_settings(human_residence_time_ms: int = None, human_business_time_ms: int = None,
                        unknown_silence_timeout_ms: int = None, max_time_from_connect_ms: int = None) \
        -> settings_msg.CpaSettings:
    """
    Constructs a CpaSettings message. See settings.proto for more information.

    :param human_residence_time_ms: Maximum amount of speech for human residence classification.
    :param human_business_time_ms:  Maximum amount of speech for human business classification.
    :param unknown_silence_timeout_ms: Maximum amount of silence to allow before human speech is detected.
    :param max_time_from_connect_ms: Maximum amount of time the CPA algorithm is allowed to perform human or
        machine classification.
    :return: CpaSettings protocol buffer message (settings.proto).
    """
    cpa_settings = settings_msg.CpaSettings(
        human_residence_time_ms=optional_int32(human_residence_time_ms)
        if human_residence_time_ms is not None else None,
        human_business_time_ms=optional_int32(human_business_time_ms) if human_business_time_ms is not None else None,
        unknown_silence_timeout_ms=optional_int32(unknown_silence_timeout_ms)
        if unknown_silence_timeout_ms is not None else None,
        max_time_from_connect_ms=optional_int32(max_time_from_connect_ms)
        if max_time_from_connect_ms is not None else None)

    return cpa_settings


def define_tts_inline_synthesis_settings(voice: str = None, synth_emphasis_level: str = None,
                                         synth_prosody_pitch: str = None, synth_prosody_contour: str = None,
                                         synth_prosody_rate: str = None, synth_prosody_duration: str = None,
                                         synth_prosody_volume: str = None, synth_voice_age: str = None,
                                         synth_voice_gender: str = None) -> settings_msg.TtsInlineSynthesisSettings:
    """
     Constructs a TtsInlineSynthesisSettings message. See settings.proto for more information.
    :param voice: Optional voice (if using simple text, or if not specified within SSML).
    :param synth_emphasis_level: The strength of the emphasis used in the voice during synthesis.
    :param synth_prosody_pitch: The pitch of the audio being synthesized.
    :param synth_prosody_contour: The contour of the audio being synthesized.
    :param synth_prosody_rate: The speaking rate of the audio being synthesized.
    :param synth_prosody_duration: The duration of time it will take for the synthesized text to play.
    :param synth_prosody_volume: The volume of the audio being synthesized.
    :param synth_voice_age: The age of the voice used for synthesis.
    :param synth_voice_gender: The default TTS gender to use if none is specified.
    :return: TtsInlineSynthesisSettings protocol buffer message (settings.proto).
    """

    tts_inline_synthesis_settings = settings_msg.TtsInlineSynthesisSettings(
        voice=optional_string(voice) if voice else None,
        synth_emphasis_level=optional_string(synth_emphasis_level) if synth_emphasis_level else None,
        synth_prosody_pitch=optional_string(synth_prosody_pitch) if synth_prosody_pitch else None,
        synth_prosody_contour=optional_string(synth_prosody_contour) if synth_prosody_contour else None,
        synth_prosody_rate=optional_string(synth_prosody_rate) if synth_prosody_rate else None,
        synth_prosody_duration=optional_string(synth_prosody_duration) if synth_prosody_duration else None,
        synth_prosody_volume=optional_string(synth_prosody_volume) if synth_prosody_volume else None,
        synth_voice_age=optional_string(synth_voice_age) if synth_voice_age else None,
        synth_voice_gender=optional_string(synth_voice_gender) if synth_voice_gender else None
    )

    return tts_inline_synthesis_settings

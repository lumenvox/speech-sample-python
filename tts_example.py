import asyncio
import sys
import uuid

# common.proto messages
import lumenvox.api.common_pb2 as common_msg
# settings.proto messages
import lumenvox.api.settings_pb2 as settings_msg
# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats

from lumenvox_helper_function import LumenVoxApiClient, save_tts_test_audio_flag


async def create_api_session(lumenvox_api,
                             audio_format: int = None, sample_rate_hertz: int = None,
                             deployment_id: str = None, operator_id: str = None, correlation_id: str = None,
                             ):
    """
    Creates LumenVox API session.  Sets up sesssion audio parameters.

    @param lumenvox_api: Helper class for LumenVox client api
    @param audio_format: Audio format for the session to use
    @param sample_rate_hertz: audio sample rate
    @param deployment_id: unique UUID of the deployment to use for the session
      (default deployment id will be used if not specified)
    @param operator_id: optional unique UUID can be used to track who is making API calls
    @param correlation_id: optional UUID can be used to track individual API calls
    @return: None
    """

    # generate new session stream and session
    session_stream, session_id = await lumenvox_api.session_init(deployment_id=deployment_id,
                                                                 operator_id=operator_id,
                                                                 correlation_id=correlation_id)

    await lumenvox_api.session_set_inbound_audio_format(session_stream=session_stream,
                                                        audio_format=audio_format, sample_rate_hertz=sample_rate_hertz)

    return session_stream, session_id


async def tts_interaction(lumenvox_api,
                          text: str = None, voice: str = None, language_code: str = None,
                          audio_format: int = None, sample_rate_hertz: int = None,
                          tts_output_file_name: str = None,
                          deployment_id: str = None, operator_id: str = None, correlation_id: str = None,

                          ):
    """
    Common ASR (batch processing) coroutine

    @param lumenvox_api: Helper class for LumenVox client api
    @param audio_file: audio file to use for session audio
    @param audio_format: audio format enum from StandardAudioFormat
    @param sample_rate_hertz: audio sample rate
    @param language_code: two or four character code specifying the language of the interaction
    @param deployment_id: unique UUID of the deployment to use for the session
    @param operator_id: optional unique UUID can be used to track who is making API calls
    @param correlation_id: optional UUID can be used to track individual API calls
      (default deployment id will be used if not specified)
    """

    # create session and set up audio codec and sample rate
    # audio format and sample rate here are not for tts
    # when a session is set up, the potential inbound audio format is define for the session
    # if you are also doing ASR or other processing in the same session as TTS
    # you can have different audio formats for inbound audio
    # and outbound TTS audio
    session_stream, session_id = await create_api_session(lumenvox_api,
                                                          audio_format=audio_format,
                                                          sample_rate_hertz=sample_rate_hertz,
                                                          deployment_id=deployment_id,
                                                          operator_id=operator_id,
                                                          correlation_id=correlation_id)

    if not language_code:
        language_code = 'en-us'

    # specify tts voice to use
    inline_synth_settings = lumenvox_api.define_tts_inline_synthesis_settings(voice=voice)

    # create tts interaction, specify settings, tts text, and audio format for tts
    await lumenvox_api.interaction_create_tts(session_stream=session_stream, language=language_code,
                                              inline_text=text,
                                              audio_format=audio_format, sample_rate_hertz=sample_rate_hertz,
                                              tts_inline_synthesis_settings=inline_synth_settings,
                                              )

    # wait for response containing interaction ID to be returned
    r = await lumenvox_api.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = r.interaction_create_tts.interaction_id
    print("interaction_id extracted from interaction_create_tts response is:", interaction_id)

    # retrieve results, final results in this case signal tts audio is ready to pull
    await lumenvox_api.get_session_final_result(session_stream=session_stream, wait=30)

    # this helper function sends the API message AudioPullRequest, then waits for all the AudioPullResponse
    # messages, which contain the TTS audio
    audio_bytes = await lumenvox_api.audio_pull_all(session_stream=session_stream, audio_id=interaction_id)

    # if specified, save output to file
    if tts_output_file_name:
        with open(tts_output_file_name, "wb") as binary_file:
            binary_file.write(audio_bytes)

    await lumenvox_api.handle_interaction_close_all(session_stream=session_stream, interaction_id=interaction_id)


if __name__ == '__main__':
    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    ssml_text = lumenvox_api.get_ssml_file_by_ref('../test_data/ssml/mark_element.ssml')

    lumenvox_api.run_user_coroutine(
        tts_interaction(lumenvox_api,
                        language_code='en-us', voice='Chris',
                        audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW,
                        sample_rate_hertz=8000,
                        # ssml_text=ssml_text,  # optionally use this instead of the text parameter
                        text="Hello World",
                        tts_output_file_name="tts_test.ulaw"
                        ), )

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    lumenvox_api.shutdown_lumenvox_api_client()

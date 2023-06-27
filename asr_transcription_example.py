import asyncio
import time
from threading import Thread
# settings.proto messages
import lumenvox.api.settings_pb2 as settings_msg

from lumenvox_helper_function import LumenVoxApiClient


def push_audio_thread(lumenvox_api, session_stream, audio_ref, chunk_size):
    """
    In order to show how audio may be streamed from another thread, asynchronously,
    this function is called as a thread to stream in audio with a sleep between sending
    a packet to mimic streaming

    This relies on global variables audio_thread_stream_audio to stop and start streaming
      and audio_thread_stop to stop thread
      In production code, this would not be recommended

    @param lumenvox_api: String reference to audio file
    @param session_stream: Session stream to use if session is already available
    @param audio_ref: Audio file name
    @param chunk_size: Number of bytes to split audio data into
    @return: None
    """
    audio_buffer = lumenvox_api.load_audio_buffer(filename=audio_ref, chunk_bytes=chunk_size)

    more_bytes = True

    chunk_counter = 0
    while more_bytes:
        if audio_thread_stream_audio:
            # the call to push audio needs to be done in the event loop created for lumenvox_api
            # in order to do this from a different thread, and in a thread-safe way
            # run_coroutine_threadsafe is being used
            coroutine = lumenvox_api.audio_push_from_buffer(session_stream=session_stream,
                                                             audio_buffer=audio_buffer)
            future = asyncio.run_coroutine_threadsafe(coroutine, lumenvox_api.loop)
            more_bytes = future.result(90)
            chunk_counter += 1
            print("sending audio chunk ", chunk_counter, " more bytes = ", str(more_bytes))
        time.sleep(0.1)
        if audio_thread_stop:
            break
    print("audio streaming thread shutting down")


async def create_api_session(lumenvox_api,
                             audio_ref: str,
                             audio_format: int = None, sample_rate_hertz: int = None,
                             chunk_size: int = 4000,
                             deployment_id: str = None, operator_id: str = None, correlation_id: str = None,
                             ):
    """
    Creates LumenVox API session.
    Also creates a separate thread to stream audio into the session
    The audio thread will begin streaming audio when the global variable audio_thread_stream_audio is set to True

    @param lumenvox_api: Helper class for LumenVox client api
    @param audio_ref: String reference to audio file
    @param chunk_size: Number of bytes to split audio data into
    @param audio_format: Audio format for the session to use
    @param sample_rate_hertz: Sample rate for session's audio
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

    global audio_thread_stream_audio
    audio_thread_stream_audio = False

    global audio_thread_stop
    audio_thread_stop = False

    _thread = Thread(target=push_audio_thread, args=(lumenvox_api, session_stream, audio_ref, chunk_size))
    _thread.start()

    return session_stream, session_id


async def asr_transcription_session(lumenvox_api,
                                    audio_ref: str,
                                    language_code: str = None,
                                    phrases: list = None,
                                    phrase_list_settings: settings_msg.PhraseListSettings = None,
                                    chunk_size: int = 4000,
                                    audio_format: int = None, sample_rate_hertz: int = None,
                                    deployment_id: str = None, operator_id: str = None, correlation_id: str = None,
                                    ):
    """
    Function to open session, and run test transcription interaction

    @param lumenvox_api: Helper class for LumenVox client api
    @param audio_ref: String reference to audio file
    @param language_code: Two or four character code to specify language used
    @param chunk_size: Number of bytes to split audio data into
    @param audio_format: Audio format for the session to use
    @param deployment_id: unique UUID of the deployment to use for the session
      (default deployment id will be used if not specified)
    @param operator_id: optional unique UUID can be used to track who is making API calls
    @param correlation_id: optional UUID can be used to track individual API calls
    @return: None
    """

    # create session and set up audio streaming thread
    session_stream, session_id = await create_api_session(lumenvox_api,
                                                          audio_ref, audio_format, sample_rate_hertz, chunk_size,
                                                          deployment_id, operator_id, correlation_id)

    # run one transcription interaction
    await asr_transcription_interaction(lumenvox_api, session_stream, language_code, phrases, phrase_list_settings)

    # Signal the audio streaming thread to shut down, if still running
    global audio_thread_stop
    audio_thread_stop = True

    await lumenvox_api.session_close_all(session_stream=session_stream)
    lumenvox_api.set_streams_sets_to_none()


async def asr_transcription_interaction(lumenvox_api, session_stream,
                                        language_code: str = None,
                                        phrases: list = None,
                                        phrase_list_settings: settings_msg.PhraseListSettings = None,
                                        ):
    """
    Function to run test transcription interaction

    @param lumenvox_api: Helper class for LumenVox client api
    @param session_stream: Handle to the session stream
    @param language_code: Two or four character code to specify language used
    @param phrases: Optional words and phrase list to use when transcribing
    @return: None
    """

    # set default language code if none is provided
    if not language_code:
        language_code = 'en-us'

    # Use voice activity detection, an eos of 3210 will allow longer pauses between words
    vad_settings = lumenvox_api.define_vad_settings(use_vad=True, eos_delay_ms=3210)

    # Recognition settings can be used to enable partial results
    recognition_settings = lumenvox_api.define_recognition_settings(enable_partial_results=False)

    # audio will be streamed, any audio streamed after the interaction is created, will be processed
    audio_consume_settings = lumenvox_api.define_audio_consume_settings(
        audio_consume_mode=settings_msg.AudioConsumeSettings.AudioConsumeMode.AUDIO_CONSUME_MODE_STREAMING,
        stream_start_location=
        settings_msg.AudioConsumeSettings.StreamStartLocation.STREAM_START_LOCATION_INTERACTION_CREATED)

    # create a transcription interaction with supplied settings
    await lumenvox_api.interaction_create_transcription(session_stream=session_stream,
                                                        language=language_code,
                                                        audio_consume_settings=audio_consume_settings,
                                                        vad_settings=vad_settings,
                                                        phrases=phrases,
                                                        recognition_settings=recognition_settings,
                                                        phrase_list_settings=phrase_list_settings)

    # wait for response containing interaction ID to be returned
    r = await lumenvox_api.get_session_general_response(session_stream=session_stream, wait=3)
    interaction_id = r.interaction_create_transcription.interaction_id
    print("interaction_id extracted from interaction_create_transcription", interaction_id)

    # Signal the audio streaming thread to begin streaming audio
    global audio_thread_stream_audio
    audio_thread_stream_audio = True

    # wait for final result message to be returned
    result = await lumenvox_api.get_session_final_result(session_stream=session_stream, wait=30)

    # Signal the audio streaming thread to stop streaming audio
    audio_thread_stream_audio = False

    await lumenvox_api.close_interaction_and_validate(session_stream=session_stream, interaction_id=interaction_id)


if __name__ == '__main__':
    # Create and initialize the API helper object that will be used to simplify the example code
    lumenvox_api = LumenVoxApiClient()
    lumenvox_api.initialize_lumenvox_api()

    # the function asr_transcription_session creates session, and runs an interaction
    # this needs to be passed as a coroutine into lumenvox_api.run_user_coroutine, so that the event loop
    # to handle gRPC async messages is created

    lumenvox_api.run_user_coroutine(
        asr_transcription_session(lumenvox_api, language_code='en',
                                  audio_ref='../test_data/Audio/en/transcription/the_great_gatsby_1_minute.ulaw',
                                  chunk_size=4000,
                                  ), )

    # Note that if the above code encounters a problem, the following may not be called, and the callback thread
    # running inside the helper may not be told to stop. You should ensure this happens in production code.
    lumenvox_api.shutdown_lumenvox_api_client()

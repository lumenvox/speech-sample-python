# LumenVox Speech API

## Python sample code test results

The following screenshots and information are related to the python sample code
that is publicly available in GitHub:

[https://github.com/lumenvox/speech-sample-python](https://github.com/lumenvox/speech-sample-python)

This is a sample project that demonstrates how to communicate with the LumenVox
Speech API over gRPC using the published `speech.proto` definition file.

This sample code is written using Python, which was selected for its simplicity
to clearly show interactions with the API.

gRPC supports many programming languages the choice should be driven by your
business needs, not these simplistic examples.

Creating and using a virtual environment for a Python project helps a lot and
allows to use the project dependencies file a bit easier.

For the examples included, PyCharm Community Edition was used to view and run
the tests, but other IDEs can be used to run the sample code.  PyCharm is an 
Integrated Development Environment, that allows viewing, editing, compiling and 
debugging programs.

## Python Project Structure (PyCharm)

![alt text](images/projstruct.jpg "Python Project Structure")

We can see the Python Project tree structure using PyCharm, we can see the
`protobufs` folder that contains the `speech.proto` file that defines all available
calls and procedures available in the speech API, then the Test Data including
the python scripts for each of the tests we will be running, asr, transcription,
cpa & amd, tts.

At the bottom, we see the virtual environment enabled for this project including
the different scripts for the examples to be tested. In the top section on the
left side, we see 2 files in
the `/lumenvox/api/speech/v1/` directory below your project root. These files
are:

* speech_pb2.py
* speech_pb2_grpc.py

These were automatically generated via the make_stubs.py script included in the
venv folder, based on the `speech.proto` file, this is the actual process of
compiling the `speech.proto` file to be used in a Python environment, a similar
process must be followed with other programming languages as required.

Additionally, the test_data folder now includes the different grammar and
audio files used in our examples.

Now our python applications can talk to the LumenVox Speech API using gRPC.
And we can test using our IDE

## Code Samples

These tables show the different samples that are available and their
corresponding test data required for the examples to run successfully.
There are 4 tests for ASR, and a simple TTS test, as you can see below:

Sample code provided for testing ASR capabilities:

| ASR script                      | grammar                 | audio(ulaw 8khz)                | results                                       |
|---------------------------------|-------------------------|---------------------------------|-----------------------------------------------|
| asr\_batch\_example.py          | en\_digits.grxml        | 1234.ulaw                       | transcript and confidence score for each word |
| asr\_streaming\_example.py      | en\_digits.grxml        | 1234.ulaw                       | transcript and confidence score for each word |
| asr\_transcription\_example.py  | en\_transcription.grxml | OSR\_us\_000\_oo37\_8k.ulaw     | transcript and confidence score for each word |
| cpa\_amd\_streaming\_example.py | default\_cpa.grxml      | human\_residence.ulaw           | cpa: confidence, transcript HUMAN RESIDENCE   |
| default\_amd.grxml              | fax\_tone\_short.ulaw   | cpa: confidence, transcript FAX |

Sample code provided for testing TTS capabilities:

| TTS script      | ssml       | voice | results                                         |
|-----------------|------------|-------|-------------------------------------------------|
| tts\_example.py | ssml\_text | Chris | synthesis results, words, sentences, Voice used |

## Running Python scripts

The provided samples folder can be opened as a project in an IDE like PyCharm
and then run from within it, assuming that Python is installed and operational
in the system.

![alt text](images/runpy.jpg "Running .py from PyCharm")

If you are not using an IDE, you can run via terminal (i.e. SSH or PowerShell)
using python as shown here:
```shell
python.exe python_sample_name.py
```

or specifying the installation path for python if it is not defined in your
path:
```shell
"C:\path\to\python\python.exe" "C:/path/to/python_sample_code/asr_batch_example.py"
```

## asr_batch.py

This is part of the asr_batch script, we can see different calls for creating a
session, creating an audio stream as defined in our proto file, what we want to
focus on here are the settings for this, AUDIO_CONSUME_MODE is set to BATCH mode
as opposed to STREAM mode which will be described further:

```python
session_id = api_helper.SessionCreate()
print('1. session_id from SessionCreate: ', session_id)

api_helper.AudioStreamCreate(session_id=session_id, audio_format=audio_format)
print('2. Called AudioStreamCreate - no response expected')

audio_data_to_push = api_helper.get_audio_file(audio_file_path=audio_file)
api_helper.AudioStreamPush(session_id=session_id, audio_data=audio_data_to_push)
print('3. Called AudioStreamPush - no response expected')

grammar_ids = api_helper.load_grammar_helper(session_id=session_id, language_code=language_code,
                                             grammar_file_path=grammar_file_path, grammar_url=grammar_url)

interaction_id = api_helper.InteractionCreateASR(session_id=session_id, interaction_ids=grammar_ids)
print('4. interaction_id extracted from InteractionCreateASR response is: ', interaction_id)

# add setting for batch decoding.
interaction_test_json_string = '{"INTERACTION_AUDIO_CONSUME": ' \
                               '{' \
                               '   "AUDIO_CONSUME_MODE": "BATCH", ' \
                               '   "AUDIO_CONSUME_START_MODE":"STREAM_BEGIN"} ' \
                               '}'
api_helper.InteractionSetSettings(session_id=session_id, interaction_id=interaction_id,
                                  json_settings_string=interaction_test_json_string)
```

Further down in the code we can also see the options that are available with
this sample.

The `en_digits.grxml` is used along with the audio file `1234.ulaw`, both in the
test_data directory within the structure of our project, in this example.
We also notice we are using standard audio, ulaw at 8khz, and the language is
English.

> Note: this is just a view of the asr_batch script, behind scenes you can
> notice there are some references to the api_helper, which is used for all
> included examples to simplify the amount of coding needed to run and
> understand how to interact with the API.
> 
> The api_helper is the file that handles gRPC requests in the tests we are
> running.

```python
result = asr_batch_common(api_helper=api_helper,
                          grammar_file_path='test_data/en_digits.grxml',
                          audio_file='test_data/1234.ulaw',
                          audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                          language_code='en')

print(">>>> result returned:\n", json.dumps(result, indent=4, sort_keys=True))
```

This is the grammar file used for the `asr_batch.py` sample, a simple English
`digits` grammar:

```xml
<?xml version='1.0'?>
<grammar version='1.0'
	tag-format='semantics/1.0.2006'
	mode='voice' xml:lang='en-US'
	root='root'
	xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
	xsi:schemaLocation='http://www.w3.org/TR/speech-grammar/grammar.xsd'
	xmlns='http://www.w3.org/2001/06/grammar'>

	<rule id='digit'>
		<one-of>
			<item>ZERO<tag>out="0";</tag></item>
			<item>ONE<tag>out="1";</tag></item>
			<item>TWO<tag>out="2";</tag></item>
			<item>THREE<tag>out="3";</tag></item>
			<item>FOUR<tag>out="4";</tag></item>
			<item>FIVE<tag>out="5";</tag></item>
			<item>SIX<tag>out="6";</tag></item>
			<item>SEVEN<tag>out="7";</tag></item>
			<item>EIGHT<tag>out="8";</tag></item>
			<item>NONE<tag>out="9";</tag></item>
		</one-of>
	</rule>

	<rule id='root'>
	    <tag>var digits="";</tag>
		<item repeat="1-10">
			<ruleref uri='#digit'/>
			<tag>digits+=rules.latest(); digits += " ";</tag>
		</item>
	    <tag>out=digits;</tag>
	</rule>

</grammar>
```

## asr_batch.py results:

These are the results presented after successfully running the `asr_batch.py` 
sample:

```shell
>> session_id in response_handler:  2893fa1a-225a-4dcb-b7c2-af2e4a3929d2
1. session_id from SessionCreate:  2893fa1a-225a-4dcb-b7c2-af2e4a3929d2
2. Called AudioStreamCreate - no response expected
3. Called AudioStreamPush - no response expected
>> RESULT CALLBACK in response_handler
4. interaction_id extracted from InteractionCreateASR response is:  6a8d5b8c-b1c8-4339-b314-4141e82f3d01
session id before InteractionBeginProcessing:  2893fa1a-225a-4dcb-b7c2-af2e4a3929d2
5. called InteractionBeginProcessing for ASR (no response expected) interaction_id:  6a8d5b8c-b1c8-4339-b314-4141e82f3d01
>> PARTIAL RESULT CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
>> RESULT CALLBACK in response_handler
6. Final Results ready: True
>>>> result returned:
 {
    "final_results": [
        {
            "n_bests": [
                {
                    "confidence": 988,
                    "duration": 3,
                    "phrase": {
                        "transcript": "ONE TWO THREE FOUR",
                        "words": [
                            {
                                "confidence": 688,
                                "duration": 0.5,
                                "start_time": 1.9,
                                "word": "ONE"
                            },
                            {
                                "confidence": 978,
                                "duration": 0.5,
                                "start_time": 2.66,
                                "word": "TWO"
                            },
                            {
                                "confidence": 460,
                                "duration": 0.6,
                                "start_time": 3.44,
                                "word": "THREE"
                            },
                            {
                                "confidence": 830,
                                "duration": 0.56,
                                "start_time": 4.34,
                                "word": "FOUR"
                            }
                        ]
                    },
                    "semantic_interpretations": [
                        {
                            "custom_interpretation": "[object Object]",
                            "grammar_label": "file:///usr/bin/Buffer_Grammar",
                            "input_text": "ONE TWO THREE FOUR",
                            "interpretation": "1 2 3 4 ",
                            "language": "EN-US",
                            "mode": "voice",
                            "semantic_score": 728,
                            "tag_format": "semantics/1.0.2006",
                            "top_rule": "root"
                        }
                    ],
                    "start_time": 1.9
                }
            ]
        }
    ],
    "partial_results": [
        {
            "preview_results": [
                {
                    "transcript": "ONE TWO THREE FOUR",
                    "words": [
                        {
                            "confidence": 688,
                            "duration": 0.5,
                            "start_time": 1.9,
                            "word": "ONE"
                        },
                        {
                            "confidence": 978,
                            "duration": 0.5,
                            "start_time": 2.66,
                            "word": "TWO"
                        },
                        {
                            "confidence": 460,
                            "duration": 0.6,
                            "start_time": 3.44,
                            "word": "THREE"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.18,
                            "start_time": 4.34,
                            "word": "FOUR"
                        }
                    ]
                }
            ],
            "stable_results": [
                {}
            ]
        },
        {
            "stable_results": [
                {
                    "transcript": "ONE TWO THREE FOUR",
                    "words": [
                        {
                            "confidence": 688,
                            "duration": 0.5,
                            "start_time": 1.9,
                            "word": "ONE"
                        },
                        {
                            "confidence": 978,
                            "duration": 0.5,
                            "start_time": 2.66,
                            "word": "TWO"
                        },
                        {
                            "confidence": 460,
                            "duration": 0.6,
                            "start_time": 3.44,
                            "word": "THREE"
                        },
                        {
                            "confidence": 830,
                            "duration": 0.56,
                            "start_time": 4.34,
                            "word": "FOUR"
                        }
                    ]
                }
            ]
        }
    ]
}
```

## asr_streaming.py

This is a partial view of the `asr_streaming.py` sample code, just to notice 
how the `Audio_Consume_Mode` is set to streaming in this case, 

```python
session_id = api_helper.SessionCreate()
print('1. session_id from SessionCreate: ', session_id)

api_helper.AudioStreamCreate(session_id=session_id, audio_format=audio_format)
print('2. Called AudioStreamCreate - no response expected')

grammar_ids = api_helper.load_grammar_helper(session_id=session_id, language_code=language_code,
                                             grammar_file_path=grammar_file_path, grammar_url=grammar_url)

interaction_id = api_helper.InteractionCreateASR(session_id=session_id, interaction_ids=grammar_ids)
print('3. interaction_id extracted from InteractionCreateASR response is: ', interaction_id)

# Settings for streaming decodes
interaction_test_json_string = '{"INTERACTION_AUDIO_CONSUME": ' \
                               '{' \
                               '   "AUDIO_CONSUME_MODE": "STREAMING", ' \
                               '   "AUDIO_CONSUME_START_MODE":"STREAM_BEGIN"} ' \
                               '}'
api_helper.InteractionSetSettings(session_id=session_id, interaction_id=interaction_id,
                                  json_settings_string=interaction_test_json_string)
```

And this sample code is using the `digits.grxml` grammar file and the same
`1234.ulaw` audio file we used before:

```python
result = asr_streaming_common(api_helper=api_helper,
                              grammar_file_path='test_data/en_digits.grxml',
                              audio_file='test_data/1234.ulaw',
                              audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                              language_code='en')

print(">>>> result returned:\n", json.dumps(result, indent=4, sort_keys=True))
```

## asr_streaming.py results

In the results presented here we can see messages related to different audio
chunks that are being streamed, along with the partial results:

```shell
>> session_id in response_handler:  a50e4395-1e27-4344-a380-d41779bb0e87
1. session_id from SessionCreate:  a50e4395-1e27-4344-a380-d41779bb0e87
2. Called AudioStreamCreate - no response expected
>> RESULT CALLBACK in response_handler
3. interaction_id extracted from InteractionCreateASR response is:  11f77018-9078-47fc-b968-fa53272c8fe2
4. called InteractionBeginProcessing for ASR (no response expected) interaction_id:  11f77018-9078-47fc-b968-fa53272c8fe2
sending audio chunk  1  more bytes =  True
sending audio chunk  2  more bytes =  True
sending audio chunk  3  more bytes =  True
sending audio chunk  4  more bytes =  True
>> VAD CALLBACK in response_handler
sending audio chunk  5  more bytes =  True
## Got vad callback VAD_MESSAGE_EVENT_TYPE_BARGE_IN interaction_id 11f77018-9078-47fc-b968-fa53272c8fe2 session_id a50e4395-1e27-4344-a380-d41779bb0e87
sending audio chunk  6  more bytes =  True
sending audio chunk  7  more bytes =  True
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  8  more bytes =  True
## Got partial result callback for interaction_id 11f77018-9078-47fc-b968-fa53272c8fe2 session_id a50e4395-1e27-4344-a380-d41779bb0e87
sending audio chunk  9  more bytes =  True
sending audio chunk  10  more bytes =  True
sending audio chunk  11  more bytes =  True
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  12  more bytes =  True
## Got partial result callback for interaction_id 11f77018-9078-47fc-b968-fa53272c8fe2 session_id a50e4395-1e27-4344-a380-d41779bb0e87
>> VAD CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
>> RESULT CALLBACK in response_handler
sending audio chunk  13  more bytes =  True
## Got vad callback VAD_MESSAGE_EVENT_TYPE_END_OF_SPEECH interaction_id 11f77018-9078-47fc-b968-fa53272c8fe2 session_id a50e4395-1e27-4344-a380-d41779bb0e87
## Got partial result callback for interaction_id 11f77018-9078-47fc-b968-fa53272c8fe2 session_id a50e4395-1e27-4344-a380-d41779bb0e87
Partial results:  {'partial_results': [{'stable_results': [{}], 'preview_results': [{'words': [{'start_time': 0.54, 'duration': 0.5, 'word': 'ONE', 'confidence': 989}, {'start_time': 1.28, 'duration': 0.14, 'word': 'TWO', 'confidence': 1}], 'transcript': 'ONE TWO'}]}, {'stable_results': [{}], 'preview_results': [{'words': [{'start_time': 0.54, 'duration': 0.5, 'word': 'ONE', 'confidence': 989}, {'start_time': 1.28, 'duration': 0.5, 'word': 'TWO', 'confidence': 913}, {'start_time': 2.08, 'duration': 0.6, 'word': 'THREE', 'confidence': 423}, {'start_time': 2.98, 'duration': 0.18, 'word': 'FOUR', 'confidence': 1}], 'transcript': 'ONE TWO THREE FOUR'}]}, {'stable_results': [{'words': [{'start_time': 0.54, 'duration': 0.5, 'word': 'ONE', 'confidence': 989}, {'start_time': 1.28, 'duration': 0.5, 'word': 'TWO', 'confidence': 913}, {'start_time': 2.08, 'duration': 0.6, 'word': 'THREE', 'confidence': 423}, {'start_time': 2.98, 'duration': 0.56, 'word': 'FOUR', 'confidence': 589}], 'transcript': 'ONE TWO THREE FOUR'}]}], 'final_results': [{'n_bests': [{'phrase': {'words': [{'start_time': 0.54, 'duration': 0.5, 'word': 'ONE', 'confidence': 989}, {'start_time': 1.28, 'duration': 0.5, 'word': 'TWO', 'confidence': 913}, {'start_time': 2.08, 'duration': 0.6, 'word': 'THREE', 'confidence': 423}, {'start_time': 2.98, 'duration': 0.56, 'word': 'FOUR', 'confidence': 589}], 'transcript': 'ONE TWO THREE FOUR'}, 'start_time': 0.54, 'duration': 3, 'confidence': 989, 'semantic_interpretations': [{'custom_interpretation': '[object Object]', 'interpretation': '1 2 3 4 ', 'mode': 'voice', 'grammar_label': 'file:///usr/bin/Buffer_Grammar', 'language': 'EN-US', 'tag_format': 'semantics/1.0.2006', 'top_rule': 'root', 'input_text': 'ONE TWO THREE FOUR', 'semantic_score': 710}]}]}]}
## Got InteractionFinalResultsReadyMessage for ASR interaction_id  11f77018-9078-47fc-b968-fa53272c8fe2
5. Completed streaming audio
6. Final Results ready: True
>>>> result returned:
 {
    "final_results": [
        {
            "n_bests": [
                {
                    "confidence": 989,
                    "duration": 3,
                    "phrase": {
                        "transcript": "ONE TWO THREE FOUR",
                        "words": [
                            {
                                "confidence": 989,
                                "duration": 0.5,
                                "start_time": 0.54,
                                "word": "ONE"
                            },
                            {
                                "confidence": 913,
                                "duration": 0.5,
                                "start_time": 1.28,
                                "word": "TWO"
                            },
                            {
                                "confidence": 423,
                                "duration": 0.6,
                                "start_time": 2.08,
                                "word": "THREE"
                            },
                            {
                                "confidence": 589,
                                "duration": 0.56,
                                "start_time": 2.98,
                                "word": "FOUR"
                            }
                        ]
                    },
                    "semantic_interpretations": [
                        {
                            "custom_interpretation": "[object Object]",
                            "grammar_label": "file:///usr/bin/Buffer_Grammar",
                            "input_text": "ONE TWO THREE FOUR",
                            "interpretation": "1 2 3 4 ",
                            "language": "EN-US",
                            "mode": "voice",
                            "semantic_score": 710,
                            "tag_format": "semantics/1.0.2006",
                            "top_rule": "root"
                        }
                    ],
                    "start_time": 0.54
                }
            ]
        }
    ],
    "partial_results": [
        {
            "preview_results": [
                {
                    "transcript": "ONE TWO",
                    "words": [
                        {
                            "confidence": 989,
                            "duration": 0.5,
                            "start_time": 0.54,
                            "word": "ONE"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.14,
                            "start_time": 1.28,
                            "word": "TWO"
                        }
                    ]
                }
            ],
            "stable_results": [
                {}
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "ONE TWO THREE FOUR",
                    "words": [
                        {
                            "confidence": 989,
                            "duration": 0.5,
                            "start_time": 0.54,
                            "word": "ONE"
                        },
                        {
                            "confidence": 913,
                            "duration": 0.5,
                            "start_time": 1.28,
                            "word": "TWO"
                        },
                        {
                            "confidence": 423,
                            "duration": 0.6,
                            "start_time": 2.08,
                            "word": "THREE"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.18,
                            "start_time": 2.98,
                            "word": "FOUR"
                        }
                    ]
                }
            ],
            "stable_results": [
                {}
            ]
        },
        {
            "stable_results": [
                {
                    "transcript": "ONE TWO THREE FOUR",
                    "words": [
                        {
                            "confidence": 989,
                            "duration": 0.5,
                            "start_time": 0.54,
                            "word": "ONE"
                        },
                        {
                            "confidence": 913,
                            "duration": 0.5,
                            "start_time": 1.28,
                            "word": "TWO"
                        },
                        {
                            "confidence": 423,
                            "duration": 0.6,
                            "start_time": 2.08,
                            "word": "THREE"
                        },
                        {
                            "confidence": 589,
                            "duration": 0.56,
                            "start_time": 2.98,
                            "word": "FOUR"
                        }
                    ]
                }
            ]
        }
    ]
}
```

## asr_transcription.py

This example is also set for audio streaming mode, the main difference here is
the grammar file that is used to define the transcription mode to be enabled.
Note that some sample audio used for the transcription example is courtesy of
the [Open Speech Repository](https://www.voiptroubleshooter.com/open_speech/index.html)

Please visit their website for details and conditions of use:

```python
# Audio sample courtesy of Open Speech Repository: https://www.voiptroubleshooter.com/open_speech/index.html
result = asr_transcription_common(api_helper=api_helper,
                                  grammar_file_path='test_data/en_transcription.grxml',
                                  audio_file='test_data/OSR_us_000_0037_8k.ulaw',
                                  audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                                  language_code='en')
```

The grammar file used `en_transcription.grxml`, shown below, activates the
ASR transcription mode:

```xml
<?xml version='1.0'?>
<grammar xml:lang="en" version="1.0" root="root" mode="voice"
         xmlns="http://www.w3.org/2001/06/grammar"
         tag-format="semantics/1.0.2006">

	<meta name="TRANSCRIPTION_ENGINE" content="V2"/>

	<rule id="root" scope="public">
		<ruleref special="NULL"/>
	</rule>
</grammar>
```

## asr_transcription.py results

These are the results returned by the script, with the different audio chunks,
partial results, and final results with overall and individual confidence
scores:

```shell
>> session_id in response_handler:  63fc6f9c-35a9-420e-9acf-bb4623db1d20
1. session_id from SessionCreate:  63fc6f9c-35a9-420e-9acf-bb4623db1d20
2. Called AudioStreamCreate - no response expected
>> RESULT CALLBACK in response_handler
3. interaction_id extracted from InteractionCreateASR response is:  d471fcbc-2e0e-4005-b17a-ead76fdca9da
4. called InteractionBeginProcessing for ASR (no response expected) interaction_id:  d471fcbc-2e0e-4005-b17a-ead76fdca9da
sending audio chunk  1  more bytes =  True
sending audio chunk  2  more bytes =  True
sending audio chunk  3  more bytes =  True
>> VAD CALLBACK in response_handler
sending audio chunk  4  more bytes =  True
## Got vad callback VAD_MESSAGE_EVENT_TYPE_BARGE_IN interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  5  more bytes =  True
sending audio chunk  6  more bytes =  True
sending audio chunk  7  more bytes =  True
sending audio chunk  8  more bytes =  True
sending audio chunk  9  more bytes =  True
sending audio chunk  10  more bytes =  True
sending audio chunk  11  more bytes =  True
sending audio chunk  12  more bytes =  True
sending audio chunk  13  more bytes =  True
sending audio chunk  14  more bytes =  True
sending audio chunk  15  more bytes =  True
sending audio chunk  16  more bytes =  True
sending audio chunk  17  more bytes =  True
sending audio chunk  18  more bytes =  True
sending audio chunk  19  more bytes =  True
sending audio chunk  20  more bytes =  True
sending audio chunk  21  more bytes =  True
sending audio chunk  22  more bytes =  True
sending audio chunk  23  more bytes =  True
sending audio chunk  24  more bytes =  True
sending audio chunk  25  more bytes =  True
sending audio chunk  26  more bytes =  True
sending audio chunk  27  more bytes =  True
sending audio chunk  28  more bytes =  True
sending audio chunk  29  more bytes =  True
sending audio chunk  30  more bytes =  True
sending audio chunk  31  more bytes =  True
sending audio chunk  32  more bytes =  True
sending audio chunk  33  more bytes =  True
sending audio chunk  34  more bytes =  True
sending audio chunk  35  more bytes =  True
sending audio chunk  36  more bytes =  True
sending audio chunk  37  more bytes =  True
sending audio chunk  38  more bytes =  True
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  39  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
>> PARTIAL RESULT CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  40  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
>> PARTIAL RESULT CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  41  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
>> PARTIAL RESULT CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  42  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  43  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  44  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  45  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  46  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  47  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  48  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  49  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  50  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  51  more bytes =  True
sending audio chunk  52  more bytes =  True
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  53  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  54  more bytes =  True
sending audio chunk  55  more bytes =  True
sending audio chunk  56  more bytes =  True
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  57  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  58  more bytes =  True
sending audio chunk  59  more bytes =  True
sending audio chunk  60  more bytes =  True
>> PARTIAL RESULT CALLBACK in response_handler
sending audio chunk  61  more bytes =  True
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
sending audio chunk  62  more bytes =  True
>> VAD CALLBACK in response_handler
>> PARTIAL RESULT CALLBACK in response_handler
>> RESULT CALLBACK in response_handler
sending audio chunk  63  more bytes =  True
## Got vad callback VAD_MESSAGE_EVENT_TYPE_END_OF_SPEECH interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
## Got partial result callback for interaction_id d471fcbc-2e0e-4005-b17a-ead76fdca9da session_id 63fc6f9c-35a9-420e-9acf-bb4623db1d20
Partial results:  {'partial_results': [{'stable_results': [{}], 'preview_results': [{'words': [{'start_time': 0.3, 'duration': 0.12, 'word': 'THE', 'confidence': 991}, {'start_time': 0.48, 'duration': 0.28, 'word': 'STORE', 'confidence': 789}, {'start_time': 0.8, 'duration': 0.06, 'word': 'OF', 'confidence': 990}, {'start_time': 0.96, 'duration': 0.42, 'word': 'WALLS', 'confidence': 973}, {'start_time': 1.46, 'duration': 0.18, 'word': 'WERE', 'confidence': 824}], 'transcript': 'THE STORE OF WALLS WERE'}]}, {'stable_results': [{'words': [{'start_time': 0.3, 'duration': 0.12, 'word': 'THE', 'confidence': 991}, {'start_time': 0.48, 'duration': 0.28, 'word': 'STORE', 'confidence': 789}, {'start_time': 0.8, 'duration': 0.06, 'word': 'OF', 'confidence': 990}, {'start_time': 0.96, 'duration': 0.42, 'word': 'WALLS', 'confidence': 973}, {'start_time': 1.46, 'duration': 0.18, 'word': 'WERE', 'confidence': 824}, {'start_time': 1.7, 'duration': 0.28, 'word': 'LINED', 'confidence': 15}], 'transcript': 'THE STORE OF WALLS WERE LINED'}], 'preview_results': [{'words': [{'start_time': 2.02, 'duration': 0.14, 'word': 'WITH', 'confidence': 978}, {'start_time': 2.24, 'duration': 0.36, 'word': 'COLOURED', 'confidence': 429}, {'start_time': 2.66, 'duration': 0.72, 'word': 'FROCKS', 'confidence': 969}, {'start_time': 3.44, 'duration': 0.08, 'word': 'THE', 'confidence': 987}], 'transcript': 'WITH COLOURED FROCKS THE'}]}, {'stable_results': [{'words': [{'start_time': 2.02, 'duration': 0.14, 'word': 'WITH', 'confidence': 978}, {'start_time': 2.24, 'duration': 0.36, 'word': 'COLOURED', 'confidence': 429}, {'start_time': 2.66, 'duration': 0.72, 'word': 'FROCKS', 'confidence': 969}, {'start_time': 3.44, 'duration': 0.08, 'word': 'THE', 'confidence': 987}], 'transcript': 'WITH COLOURED FROCKS THE'}], 'preview_results': [{'words': [{'start_time': 3.6, 'duration': 0.32, 'word': 'PEACE', 'confidence': 432}, {'start_time': 3.96, 'duration': 0.34, 'word': 'LEAGUE', 'confidence': 951}, {'start_time': 4.4, 'duration': 0.34, 'word': 'MET', 'confidence': 241}, {'start_time': 4.8, 'duration': 0.12, 'word': 'TO', 'confidence': 991}, {'start_time': 4.96, 'duration': 0.4, 'word': 'DISCUSS', 'confidence': 983}, {'start_time': 5.38, 'duration': 0.16, 'word': 'THEIR', 'confidence': 981}], 'transcript': 'PEACE LEAGUE MET TO DISCUSS THEIR'}]}, {'stable_results': [{'words': [{'start_time': 3.6, 'duration': 0.32, 'word': 'PEACE', 'confidence': 432}, {'start_time': 3.96, 'duration': 0.34, 'word': 'LEAGUE', 'confidence': 951}, {'start_time': 4.4, 'duration': 0.34, 'word': 'MET', 'confidence': 241}, {'start_time': 4.8, 'duration': 0.12, 'word': 'TO', 'confidence': 991}, {'start_time': 4.96, 'duration': 0.4, 'word': 'DISCUSS', 'confidence': 983}], 'transcript': 'PEACE LEAGUE MET TO DISCUSS'}], 'preview_results': [{'words': [{'start_time': 5.38, 'duration': 0.16, 'word': 'THEIR', 'confidence': 981}, {'start_time': 5.6, 'duration': 0.64, 'word': 'PLANS', 'confidence': 981}, {'start_time': 6.28, 'duration': 0.1, 'word': 'THE', 'confidence': 991}, {'start_time': 6.44, 'duration': 0.4, 'word': 'RISE', 'confidence': 988}, {'start_time': 6.88, 'duration': 0.12, 'word': 'TO', 'confidence': 991}, {'start_time': 7.06, 'duration': 0.26, 'word': 'FAME', 'confidence': 983}], 'transcript': 'THEIR PLANS THE RISE TO FAME'}]}, {'stable_results': [{'words': [{'start_time': 5.38, 'duration': 0.16, 'word': 'THEIR', 'confidence': 981}, {'start_time': 5.6, 'duration': 0.64, 'word': 'PLANS', 'confidence': 981}, {'start_time': 6.28, 'duration': 0.1, 'word': 'THE', 'confidence': 991}, {'start_time': 6.44, 'duration': 0.4, 'word': 'RISE', 'confidence': 988}, {'start_time': 6.88, 'duration': 0.12, 'word': 'TO', 'confidence': 991}, {'start_time': 7.06, 'duration': 0.26, 'word': 'FAME', 'confidence': 983}, {'start_time': 7.38, 'duration': 0.06, 'word': 'OF', 'confidence': 991}], 'transcript': 'THEIR PLANS THE RISE TO FAME OF'}], 'preview_results': [{'words': [{'start_time': 7.54, 'duration': 0.04, 'word': 'A', 'confidence': 984}, {'start_time': 7.64, 'duration': 0.58, 'word': 'PERSON', 'confidence': 979}, {'start_time': 8.32, 'duration': 0.3, 'word': 'TAKES', 'confidence': 839}, {'start_time': 8.72, 'duration': 0.2, 'word': 'LUCK', 'confidence': 1}], 'transcript': 'A PERSON TAKES LUCK'}]}, {'stable_results': [{'words': [{'start_time': 7.54, 'duration': 0.04, 'word': 'A', 'confidence': 984}, {'start_time': 7.64, 'duration': 0.58, 'word': 'PERSON', 'confidence': 979}, {'start_time': 8.32, 'duration': 0.3, 'word': 'TAKES', 'confidence': 839}], 'transcript': 'A PERSON TAKES'}], 'preview_results': [{'words': [{'start_time': 8.72, 'duration': 0.58, 'word': 'LUCK', 'confidence': 893}, {'start_time': 9.56, 'duration': 0.3, 'word': 'PAPER', 'confidence': 831}, {'start_time': 9.92, 'duration': 0.14, 'word': 'IS', 'confidence': 987}, {'start_time': 10.1, 'duration': 0.68, 'word': 'SCARCE', 'confidence': 464}, {'start_time': 10.9, 'duration': 0.2, 'word': 'SO', 'confidence': 990}, {'start_time': 11.1, 'duration': 0.18, 'word': 'RIGHT', 'confidence': 1}], 'transcript': 'LUCK PAPER IS SCARCE SO RIGHT'}]}, {'stable_results': [{'words': [{'start_time': 8.72, 'duration': 0.58, 'word': 'LUCK', 'confidence': 893}, {'start_time': 9.56, 'duration': 0.3, 'word': 'PAPER', 'confidence': 831}, {'start_time': 9.92, 'duration': 0.14, 'word': 'IS', 'confidence': 987}, {'start_time': 10.1, 'duration': 0.68, 'word': 'SCARCE', 'confidence': 464}, {'start_time': 10.9, 'duration': 0.2, 'word': 'SO', 'confidence': 990}], 'transcript': 'LUCK PAPER IS SCARCE SO'}], 'preview_results': [{'words': [{'start_time': 11.1, 'duration': 0.42, 'word': 'RIGHT', 'confidence': 157}, {'start_time': 11.6, 'duration': 0.2, 'word': 'WITH', 'confidence': 991}, {'start_time': 11.8, 'duration': 0.24, 'word': 'MUCH', 'confidence': 914}, {'start_time': 12.2, 'duration': 0.58, 'word': 'CARE', 'confidence': 973}, {'start_time': 12.9, 'duration': 0.12, 'word': 'THE', 'confidence': 960}, {'start_time': 13.1, 'duration': 0.16, 'word': 'QUICK', 'confidence': 1}], 'transcript': 'RIGHT WITH MUCH CARE THE QUICK'}]}, {'stable_results': [{'words': [{'start_time': 11.1, 'duration': 0.42, 'word': 'RIGHT', 'confidence': 157}, {'start_time': 11.6, 'duration': 0.2, 'word': 'WITH', 'confidence': 991}, {'start_time': 11.8, 'duration': 0.24, 'word': 'MUCH', 'confidence': 914}, {'start_time': 12.2, 'duration': 0.58, 'word': 'CARE', 'confidence': 973}, {'start_time': 12.9, 'duration': 0.12, 'word': 'THE', 'confidence': 960}, {'start_time': 13.1, 'duration': 0.4, 'word': 'QUICK', 'confidence': 975}, {'start_time': 13.6, 'duration': 0.46, 'word': 'FOX', 'confidence': 931}], 'transcript': 'RIGHT WITH MUCH CARE THE QUICK FOX'}], 'preview_results': [{'words': [{'start_time': 14.1, 'duration': 0.28, 'word': 'JUMPED', 'confidence': 987}, {'start_time': 14.5, 'duration': 0.1, 'word': 'ON', 'confidence': 973}, {'start_time': 14.6, 'duration': 0.08, 'word': 'THE', 'confidence': 992}, {'start_time': 14.7, 'duration': 0.4, 'word': 'SLEEPING', 'confidence': 658}], 'transcript': 'JUMPED ON THE SLEEPING'}]}, {'stable_results': [{'words': [{'start_time': 14.1, 'duration': 0.28, 'word': 'JUMPED', 'confidence': 987}, {'start_time': 14.5, 'duration': 0.1, 'word': 'ON', 'confidence': 973}, {'start_time': 14.6, 'duration': 0.08, 'word': 'THE', 'confidence': 992}, {'start_time': 14.7, 'duration': 0.4, 'word': 'SLEEPING', 'confidence': 658}, {'start_time': 15.2, 'duration': 0.5, 'word': 'CAT', 'confidence': 976}, {'start_time': 15.8, 'duration': 0.1, 'word': 'THE', 'confidence': 982}], 'transcript': 'JUMPED ON THE SLEEPING CAT THE'}], 'preview_results': [{'words': [{'start_time': 16, 'duration': 0.34, 'word': 'NOZZLE', 'confidence': 180}, {'start_time': 16.4, 'duration': 0.06, 'word': 'OF', 'confidence': 992}, {'start_time': 16.5, 'duration': 0.08, 'word': 'THE', 'confidence': 992}, {'start_time': 16.6, 'duration': 0.3, 'word': 'FIRE', 'confidence': 986}, {'start_time': 16.9, 'duration': 0.12, 'word': 'HO', 'confidence': 1}], 'transcript': 'NOZZLE OF THE FIRE HO'}]}, {'stable_results': [{'words': [{'start_time': 16, 'duration': 0.34, 'word': 'NOZZLE', 'confidence': 180}, {'start_time': 16.4, 'duration': 0.06, 'word': 'OF', 'confidence': 992}, {'start_time': 16.5, 'duration': 0.08, 'word': 'THE', 'confidence': 992}, {'start_time': 16.6, 'duration': 0.3, 'word': 'FIRE', 'confidence': 986}], 'transcript': 'NOZZLE OF THE FIRE'}], 'preview_results': [{'words': [{'start_time': 16.9, 'duration': 0.36, 'word': 'HOSE', 'confidence': 321}, {'start_time': 17.3, 'duration': 0.18, 'word': 'WAS', 'confidence': 887}, {'start_time': 17.6, 'duration': 0.3, 'word': 'BRIGHT', 'confidence': 463}, {'start_time': 18, 'duration': 0.64, 'word': 'BRASS', 'confidence': 954}], 'transcript': 'HOSE WAS BRIGHT BRASS'}]}, {'stable_results': [{'words': [{'start_time': 16.9, 'duration': 0.36, 'word': 'HOSE', 'confidence': 321}, {'start_time': 17.3, 'duration': 0.18, 'word': 'WAS', 'confidence': 887}, {'start_time': 17.6, 'duration': 0.3, 'word': 'BRIGHT', 'confidence': 463}, {'start_time': 18, 'duration': 0.64, 'word': 'BRASS', 'confidence': 954}, {'start_time': 18.9, 'duration': 0.36, 'word': 'SCREW', 'confidence': 166}, {'start_time': 19.3, 'duration': 0.08, 'word': 'THE', 'confidence': 956}], 'transcript': 'HOSE WAS BRIGHT BRASS SCREW THE'}], 'preview_results': [{'words': [{'start_time': 19.4, 'duration': 0.26, 'word': 'ROUND', 'confidence': 587}, {'start_time': 19.7, 'duration': 0.32, 'word': 'CAP', 'confidence': 277}, {'start_time': 20.2, 'duration': 0.14, 'word': 'ON', 'confidence': 988}, {'start_time': 20.4, 'duration': 0.12, 'word': 'AS', 'confidence': 977}, {'start_time': 20.5, 'duration': 0.22, 'word': 'TIGHT', 'confidence': 967}, {'start_time': 20.8, 'duration': 0.1, 'word': 'AS', 'confidence': 987}], 'transcript': 'ROUND CAP ON AS TIGHT AS'}]}, {'stable_results': [{'words': [{'start_time': 19.4, 'duration': 0.26, 'word': 'ROUND', 'confidence': 587}, {'start_time': 19.7, 'duration': 0.32, 'word': 'CAP', 'confidence': 277}, {'start_time': 20.2, 'duration': 0.14, 'word': 'ON', 'confidence': 988}, {'start_time': 20.4, 'duration': 0.12, 'word': 'AS', 'confidence': 977}, {'start_time': 20.5, 'duration': 0.22, 'word': 'TIGHT', 'confidence': 967}, {'start_time': 20.8, 'duration': 0.1, 'word': 'AS', 'confidence': 987}, {'start_time': 20.9, 'duration': 0.66, 'word': 'NEEDED', 'confidence': 990}, {'start_time': 21.7, 'duration': 0.3, 'word': 'TIME', 'confidence': 990}], 'transcript': 'ROUND CAP ON AS TIGHT AS NEEDED TIME'}], 'preview_results': [{'words': [{'start_time': 22, 'duration': 0.28, 'word': 'BRINGS', 'confidence': 978}, {'start_time': 22.4, 'duration': 0.12, 'word': 'AS', 'confidence': 875}, {'start_time': 22.5, 'duration': 0.24, 'word': 'MANY', 'confidence': 790}], 'transcript': 'BRINGS AS MANY'}]}, {'stable_results': [{}], 'preview_results': [{'words': [{'start_time': 22, 'duration': 0.28, 'word': 'BRINGS', 'confidence': 978}, {'start_time': 22.4, 'duration': 0.12, 'word': 'US', 'confidence': 973}, {'start_time': 22.5, 'duration': 0.24, 'word': 'MANY', 'confidence': 965}, {'start_time': 22.8, 'duration': 0.76, 'word': 'CHANGES', 'confidence': 969}, {'start_time': 23.9, 'duration': 0.1, 'word': 'THE', 'confidence': 991}, {'start_time': 24.1, 'duration': 0.36, 'word': 'PURPLE', 'confidence': 644}, {'start_time': 24.5, 'duration': 0.24, 'word': 'TIDE', 'confidence': 270}], 'transcript': 'BRINGS US MANY CHANGES THE PURPLE TIDE'}]}, {'stable_results': [{'words': [{'start_time': 22, 'duration': 0.28, 'word': 'BRINGS', 'confidence': 978}, {'start_time': 22.4, 'duration': 0.12, 'word': 'US', 'confidence': 973}, {'start_time': 22.5, 'duration': 0.24, 'word': 'MANY', 'confidence': 965}, {'start_time': 22.8, 'duration': 0.76, 'word': 'CHANGES', 'confidence': 969}, {'start_time': 23.9, 'duration': 0.1, 'word': 'THE', 'confidence': 991}, {'start_time': 24.1, 'duration': 0.36, 'word': 'PURPLE', 'confidence': 644}, {'start_time': 24.5, 'duration': 0.24, 'word': 'TIDE', 'confidence': 270}], 'transcript': 'BRINGS US MANY CHANGES THE PURPLE TIDE'}], 'preview_results': [{'words': [{'start_time': 24.8, 'duration': 0.18, 'word': 'WAS', 'confidence': 465}, {'start_time': 25.1, 'duration': 0.22, 'word': 'TEN', 'confidence': 991}, {'start_time': 25.3, 'duration': 0.26, 'word': 'YEARS', 'confidence': 422}, {'start_time': 25.6, 'duration': 0.52, 'word': 'OLD', 'confidence': 985}, {'start_time': 26.5, 'duration': 0.18, 'word': 'MEN', 'confidence': 13}], 'transcript': 'WAS TEN YEARS OLD MEN'}]}, {'stable_results': [{'words': [{'start_time': 24.8, 'duration': 0.18, 'word': 'WAS', 'confidence': 465}, {'start_time': 25.1, 'duration': 0.22, 'word': 'TEN', 'confidence': 991}, {'start_time': 25.3, 'duration': 0.26, 'word': 'YEARS', 'confidence': 422}, {'start_time': 25.6, 'duration': 0.52, 'word': 'OLD', 'confidence': 985}], 'transcript': 'WAS TEN YEARS OLD'}], 'preview_results': [{'words': [{'start_time': 26.5, 'duration': 0.3, 'word': 'MEN', 'confidence': 699}, {'start_time': 26.8, 'duration': 0.42, 'word': 'THINK', 'confidence': 775}, {'start_time': 27.3, 'duration': 0.12, 'word': 'AND', 'confidence': 991}, {'start_time': 27.5, 'duration': 0.46, 'word': 'PLAN', 'confidence': 355}, {'start_time': 28, 'duration': 0.12, 'word': 'AND', 'confidence': 988}, {'start_time': 28.2, 'duration': 0.4, 'word': 'SOMETIME', 'confidence': 1}], 'transcript': 'MEN THINK AND PLAN AND SOMETIME'}]}, {'stable_results': [{'words': [{'start_time': 26.5, 'duration': 0.3, 'word': 'MEN', 'confidence': 699}, {'start_time': 26.8, 'duration': 0.42, 'word': 'THINK', 'confidence': 775}, {'start_time': 27.3, 'duration': 0.12, 'word': 'AND', 'confidence': 991}, {'start_time': 27.5, 'duration': 0.46, 'word': 'PLAN', 'confidence': 355}, {'start_time': 28, 'duration': 0.12, 'word': 'AND', 'confidence': 988}, {'start_time': 28.2, 'duration': 0.5, 'word': 'SOMETIMES', 'confidence': 540}, {'start_time': 28.8, 'duration': 0.5, 'word': 'ACT', 'confidence': 988}], 'transcript': 'MEN THINK AND PLAN AND SOMETIMES ACT'}]}], 'final_results': [{'n_bests': [{'phrase': {'words': [{'start_time': 0.3, 'duration': 0.12, 'word': 'THE', 'confidence': 991}, {'start_time': 0.48, 'duration': 0.28, 'word': 'STORE', 'confidence': 789}, {'start_time': 0.8, 'duration': 0.06, 'word': 'OF', 'confidence': 990}, {'start_time': 0.96, 'duration': 0.42, 'word': 'WALLS', 'confidence': 973}, {'start_time': 1.46, 'duration': 0.18, 'word': 'WERE', 'confidence': 824}, {'start_time': 1.7, 'duration': 0.28, 'word': 'LINED', 'confidence': 15}, {'start_time': 2.02, 'duration': 0.14, 'word': 'WITH', 'confidence': 978}, {'start_time': 2.24, 'duration': 0.36, 'word': 'COLOURED', 'confidence': 429}, {'start_time': 2.66, 'duration': 0.72, 'word': 'FROCKS', 'confidence': 969}, {'start_time': 3.44, 'duration': 0.08, 'word': 'THE', 'confidence': 987}, {'start_time': 3.6, 'duration': 0.32, 'word': 'PEACE', 'confidence': 432}, {'start_time': 3.96, 'duration': 0.34, 'word': 'LEAGUE', 'confidence': 951}, {'start_time': 4.4, 'duration': 0.34, 'word': 'MET', 'confidence': 241}, {'start_time': 4.8, 'duration': 0.12, 'word': 'TO', 'confidence': 991}, {'start_time': 4.96, 'duration': 0.4, 'word': 'DISCUSS', 'confidence': 983}, {'start_time': 5.38, 'duration': 0.16, 'word': 'THEIR', 'confidence': 981}, {'start_time': 5.6, 'duration': 0.64, 'word': 'PLANS', 'confidence': 981}, {'start_time': 6.28, 'duration': 0.1, 'word': 'THE', 'confidence': 991}, {'start_time': 6.44, 'duration': 0.4, 'word': 'RISE', 'confidence': 988}, {'start_time': 6.88, 'duration': 0.12, 'word': 'TO', 'confidence': 991}, {'start_time': 7.06, 'duration': 0.26, 'word': 'FAME', 'confidence': 983}, {'start_time': 7.38, 'duration': 0.06, 'word': 'OF', 'confidence': 991}, {'start_time': 7.54, 'duration': 0.04, 'word': 'A', 'confidence': 984}, {'start_time': 7.64, 'duration': 0.58, 'word': 'PERSON', 'confidence': 979}, {'start_time': 8.32, 'duration': 0.3, 'word': 'TAKES', 'confidence': 839}, {'start_time': 8.72, 'duration': 0.58, 'word': 'LUCK', 'confidence': 893}, {'start_time': 9.56, 'duration': 0.3, 'word': 'PAPER', 'confidence': 831}, {'start_time': 9.92, 'duration': 0.14, 'word': 'IS', 'confidence': 987}, {'start_time': 10.1, 'duration': 0.68, 'word': 'SCARCE', 'confidence': 464}, {'start_time': 10.9, 'duration': 0.2, 'word': 'SO', 'confidence': 990}, {'start_time': 11.1, 'duration': 0.42, 'word': 'RIGHT', 'confidence': 157}, {'start_time': 11.6, 'duration': 0.2, 'word': 'WITH', 'confidence': 991}, {'start_time': 11.8, 'duration': 0.24, 'word': 'MUCH', 'confidence': 914}, {'start_time': 12.2, 'duration': 0.58, 'word': 'CARE', 'confidence': 973}, {'start_time': 12.9, 'duration': 0.12, 'word': 'THE', 'confidence': 960}, {'start_time': 13.1, 'duration': 0.4, 'word': 'QUICK', 'confidence': 975}, {'start_time': 13.6, 'duration': 0.46, 'word': 'FOX', 'confidence': 931}, {'start_time': 14.1, 'duration': 0.28, 'word': 'JUMPED', 'confidence': 987}, {'start_time': 14.5, 'duration': 0.1, 'word': 'ON', 'confidence': 973}, {'start_time': 14.6, 'duration': 0.08, 'word': 'THE', 'confidence': 992}, {'start_time': 14.7, 'duration': 0.4, 'word': 'SLEEPING', 'confidence': 658}, {'start_time': 15.2, 'duration': 0.5, 'word': 'CAT', 'confidence': 976}, {'start_time': 15.8, 'duration': 0.1, 'word': 'THE', 'confidence': 982}, {'start_time': 16, 'duration': 0.34, 'word': 'NOZZLE', 'confidence': 180}, {'start_time': 16.4, 'duration': 0.06, 'word': 'OF', 'confidence': 992}, {'start_time': 16.5, 'duration': 0.08, 'word': 'THE', 'confidence': 992}, {'start_time': 16.6, 'duration': 0.3, 'word': 'FIRE', 'confidence': 986}, {'start_time': 16.9, 'duration': 0.36, 'word': 'HOSE', 'confidence': 321}, {'start_time': 17.3, 'duration': 0.18, 'word': 'WAS', 'confidence': 887}, {'start_time': 17.6, 'duration': 0.3, 'word': 'BRIGHT', 'confidence': 463}, {'start_time': 18, 'duration': 0.64, 'word': 'BRASS', 'confidence': 954}, {'start_time': 18.9, 'duration': 0.36, 'word': 'SCREW', 'confidence': 166}, {'start_time': 19.3, 'duration': 0.08, 'word': 'THE', 'confidence': 956}, {'start_time': 19.4, 'duration': 0.26, 'word': 'ROUND', 'confidence': 587}, {'start_time': 19.7, 'duration': 0.32, 'word': 'CAP', 'confidence': 277}, {'start_time': 20.2, 'duration': 0.14, 'word': 'ON', 'confidence': 988}, {'start_time': 20.4, 'duration': 0.12, 'word': 'AS', 'confidence': 977}, {'start_time': 20.5, 'duration': 0.22, 'word': 'TIGHT', 'confidence': 967}, {'start_time': 20.8, 'duration': 0.1, 'word': 'AS', 'confidence': 987}, {'start_time': 20.9, 'duration': 0.66, 'word': 'NEEDED', 'confidence': 990}, {'start_time': 21.7, 'duration': 0.3, 'word': 'TIME', 'confidence': 990}, {'start_time': 22, 'duration': 0.28, 'word': 'BRINGS', 'confidence': 978}, {'start_time': 22.4, 'duration': 0.12, 'word': 'US', 'confidence': 973}, {'start_time': 22.5, 'duration': 0.24, 'word': 'MANY', 'confidence': 965}, {'start_time': 22.8, 'duration': 0.76, 'word': 'CHANGES', 'confidence': 969}, {'start_time': 23.9, 'duration': 0.1, 'word': 'THE', 'confidence': 991}, {'start_time': 24.1, 'duration': 0.36, 'word': 'PURPLE', 'confidence': 644}, {'start_time': 24.5, 'duration': 0.24, 'word': 'TIDE', 'confidence': 270}, {'start_time': 24.8, 'duration': 0.18, 'word': 'WAS', 'confidence': 465}, {'start_time': 25.1, 'duration': 0.22, 'word': 'TEN', 'confidence': 991}, {'start_time': 25.3, 'duration': 0.26, 'word': 'YEARS', 'confidence': 422}, {'start_time': 25.6, 'duration': 0.52, 'word': 'OLD', 'confidence': 985}, {'start_time': 26.5, 'duration': 0.3, 'word': 'MEN', 'confidence': 699}, {'start_time': 26.8, 'duration': 0.42, 'word': 'THINK', 'confidence': 775}, {'start_time': 27.3, 'duration': 0.12, 'word': 'AND', 'confidence': 991}, {'start_time': 27.5, 'duration': 0.46, 'word': 'PLAN', 'confidence': 355}, {'start_time': 28, 'duration': 0.12, 'word': 'AND', 'confidence': 988}, {'start_time': 28.2, 'duration': 0.5, 'word': 'SOMETIMES', 'confidence': 540}, {'start_time': 28.8, 'duration': 0.5, 'word': 'ACT', 'confidence': 988}], 'transcript': 'THE STORE OF WALLS WERE LINED WITH COLOURED FROCKS THE PEACE LEAGUE MET TO DISCUSS THEIR PLANS THE RISE TO FAME OF A PERSON TAKES LUCK PAPER IS SCARCE SO RIGHT WITH MUCH CARE THE QUICK FOX JUMPED ON THE SLEEPING CAT THE NOZZLE OF THE FIRE HOSE WAS BRIGHT BRASS SCREW THE ROUND CAP ON AS TIGHT AS NEEDED TIME BRINGS US MANY CHANGES THE PURPLE TIDE WAS TEN YEARS OLD MEN THINK AND PLAN AND SOMETIMES ACT'}, 'start_time': 0.3, 'duration': 29, 'confidence': 989}]}]}
## Got InteractionFinalResultsReadyMessage for ASR interaction_id  d471fcbc-2e0e-4005-b17a-ead76fdca9da
5. Completed streaming audio
6. Final Results ready: True
>>>> result returned:
 {
    "final_results": [
        {
            "n_bests": [
                {
                    "confidence": 989,
                    "duration": 29,
                    "phrase": {
                        "transcript": "THE STORE OF WALLS WERE LINED WITH COLOURED FROCKS THE PEACE LEAGUE MET TO DISCUSS THEIR PLANS THE RISE TO FAME OF A PERSON TAKES LUCK PAPER IS SCARCE SO RIGHT WITH MUCH CARE THE QUICK FOX JUMPED ON THE SLEEPING CAT THE NOZZLE OF THE FIRE HOSE WAS BRIGHT BRASS SCREW THE ROUND CAP ON AS TIGHT AS NEEDED TIME BRINGS US MANY CHANGES THE PURPLE TIDE WAS TEN YEARS OLD MEN THINK AND PLAN AND SOMETIMES ACT",
                        "words": [
                            {
                                "confidence": 991,
                                "duration": 0.12,
                                "start_time": 0.3,
                                "word": "THE"
                            },
                            {
                                "confidence": 789,
                                "duration": 0.28,
                                "start_time": 0.48,
                                "word": "STORE"
                            },
                            {
                                "confidence": 990,
                                "duration": 0.06,
                                "start_time": 0.8,
                                "word": "OF"
                            },
                            {
                                "confidence": 973,
                                "duration": 0.42,
                                "start_time": 0.96,
                                "word": "WALLS"
                            },
                            {
                                "confidence": 824,
                                "duration": 0.18,
                                "start_time": 1.46,
                                "word": "WERE"
                            },
                            {
                                "confidence": 15,
                                "duration": 0.28,
                                "start_time": 1.7,
                                "word": "LINED"
                            },
                            {
                                "confidence": 978,
                                "duration": 0.14,
                                "start_time": 2.02,
                                "word": "WITH"
                            },
                            {
                                "confidence": 429,
                                "duration": 0.36,
                                "start_time": 2.24,
                                "word": "COLOURED"
                            },
                            {
                                "confidence": 969,
                                "duration": 0.72,
                                "start_time": 2.66,
                                "word": "FROCKS"
                            },
                            {
                                "confidence": 987,
                                "duration": 0.08,
                                "start_time": 3.44,
                                "word": "THE"
                            },
                            {
                                "confidence": 432,
                                "duration": 0.32,
                                "start_time": 3.6,
                                "word": "PEACE"
                            },
                            {
                                "confidence": 951,
                                "duration": 0.34,
                                "start_time": 3.96,
                                "word": "LEAGUE"
                            },
                            {
                                "confidence": 241,
                                "duration": 0.34,
                                "start_time": 4.4,
                                "word": "MET"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.12,
                                "start_time": 4.8,
                                "word": "TO"
                            },
                            {
                                "confidence": 983,
                                "duration": 0.4,
                                "start_time": 4.96,
                                "word": "DISCUSS"
                            },
                            {
                                "confidence": 981,
                                "duration": 0.16,
                                "start_time": 5.38,
                                "word": "THEIR"
                            },
                            {
                                "confidence": 981,
                                "duration": 0.64,
                                "start_time": 5.6,
                                "word": "PLANS"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.1,
                                "start_time": 6.28,
                                "word": "THE"
                            },
                            {
                                "confidence": 988,
                                "duration": 0.4,
                                "start_time": 6.44,
                                "word": "RISE"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.12,
                                "start_time": 6.88,
                                "word": "TO"
                            },
                            {
                                "confidence": 983,
                                "duration": 0.26,
                                "start_time": 7.06,
                                "word": "FAME"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.06,
                                "start_time": 7.38,
                                "word": "OF"
                            },
                            {
                                "confidence": 984,
                                "duration": 0.04,
                                "start_time": 7.54,
                                "word": "A"
                            },
                            {
                                "confidence": 979,
                                "duration": 0.58,
                                "start_time": 7.64,
                                "word": "PERSON"
                            },
                            {
                                "confidence": 839,
                                "duration": 0.3,
                                "start_time": 8.32,
                                "word": "TAKES"
                            },
                            {
                                "confidence": 893,
                                "duration": 0.58,
                                "start_time": 8.72,
                                "word": "LUCK"
                            },
                            {
                                "confidence": 831,
                                "duration": 0.3,
                                "start_time": 9.56,
                                "word": "PAPER"
                            },
                            {
                                "confidence": 987,
                                "duration": 0.14,
                                "start_time": 9.92,
                                "word": "IS"
                            },
                            {
                                "confidence": 464,
                                "duration": 0.68,
                                "start_time": 10.1,
                                "word": "SCARCE"
                            },
                            {
                                "confidence": 990,
                                "duration": 0.2,
                                "start_time": 10.9,
                                "word": "SO"
                            },
                            {
                                "confidence": 157,
                                "duration": 0.42,
                                "start_time": 11.1,
                                "word": "RIGHT"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.2,
                                "start_time": 11.6,
                                "word": "WITH"
                            },
                            {
                                "confidence": 914,
                                "duration": 0.24,
                                "start_time": 11.8,
                                "word": "MUCH"
                            },
                            {
                                "confidence": 973,
                                "duration": 0.58,
                                "start_time": 12.2,
                                "word": "CARE"
                            },
                            {
                                "confidence": 960,
                                "duration": 0.12,
                                "start_time": 12.9,
                                "word": "THE"
                            },
                            {
                                "confidence": 975,
                                "duration": 0.4,
                                "start_time": 13.1,
                                "word": "QUICK"
                            },
                            {
                                "confidence": 931,
                                "duration": 0.46,
                                "start_time": 13.6,
                                "word": "FOX"
                            },
                            {
                                "confidence": 987,
                                "duration": 0.28,
                                "start_time": 14.1,
                                "word": "JUMPED"
                            },
                            {
                                "confidence": 973,
                                "duration": 0.1,
                                "start_time": 14.5,
                                "word": "ON"
                            },
                            {
                                "confidence": 992,
                                "duration": 0.08,
                                "start_time": 14.6,
                                "word": "THE"
                            },
                            {
                                "confidence": 658,
                                "duration": 0.4,
                                "start_time": 14.7,
                                "word": "SLEEPING"
                            },
                            {
                                "confidence": 976,
                                "duration": 0.5,
                                "start_time": 15.2,
                                "word": "CAT"
                            },
                            {
                                "confidence": 982,
                                "duration": 0.1,
                                "start_time": 15.8,
                                "word": "THE"
                            },
                            {
                                "confidence": 180,
                                "duration": 0.34,
                                "start_time": 16,
                                "word": "NOZZLE"
                            },
                            {
                                "confidence": 992,
                                "duration": 0.06,
                                "start_time": 16.4,
                                "word": "OF"
                            },
                            {
                                "confidence": 992,
                                "duration": 0.08,
                                "start_time": 16.5,
                                "word": "THE"
                            },
                            {
                                "confidence": 986,
                                "duration": 0.3,
                                "start_time": 16.6,
                                "word": "FIRE"
                            },
                            {
                                "confidence": 321,
                                "duration": 0.36,
                                "start_time": 16.9,
                                "word": "HOSE"
                            },
                            {
                                "confidence": 887,
                                "duration": 0.18,
                                "start_time": 17.3,
                                "word": "WAS"
                            },
                            {
                                "confidence": 463,
                                "duration": 0.3,
                                "start_time": 17.6,
                                "word": "BRIGHT"
                            },
                            {
                                "confidence": 954,
                                "duration": 0.64,
                                "start_time": 18,
                                "word": "BRASS"
                            },
                            {
                                "confidence": 166,
                                "duration": 0.36,
                                "start_time": 18.9,
                                "word": "SCREW"
                            },
                            {
                                "confidence": 956,
                                "duration": 0.08,
                                "start_time": 19.3,
                                "word": "THE"
                            },
                            {
                                "confidence": 587,
                                "duration": 0.26,
                                "start_time": 19.4,
                                "word": "ROUND"
                            },
                            {
                                "confidence": 277,
                                "duration": 0.32,
                                "start_time": 19.7,
                                "word": "CAP"
                            },
                            {
                                "confidence": 988,
                                "duration": 0.14,
                                "start_time": 20.2,
                                "word": "ON"
                            },
                            {
                                "confidence": 977,
                                "duration": 0.12,
                                "start_time": 20.4,
                                "word": "AS"
                            },
                            {
                                "confidence": 967,
                                "duration": 0.22,
                                "start_time": 20.5,
                                "word": "TIGHT"
                            },
                            {
                                "confidence": 987,
                                "duration": 0.1,
                                "start_time": 20.8,
                                "word": "AS"
                            },
                            {
                                "confidence": 990,
                                "duration": 0.66,
                                "start_time": 20.9,
                                "word": "NEEDED"
                            },
                            {
                                "confidence": 990,
                                "duration": 0.3,
                                "start_time": 21.7,
                                "word": "TIME"
                            },
                            {
                                "confidence": 978,
                                "duration": 0.28,
                                "start_time": 22,
                                "word": "BRINGS"
                            },
                            {
                                "confidence": 973,
                                "duration": 0.12,
                                "start_time": 22.4,
                                "word": "US"
                            },
                            {
                                "confidence": 965,
                                "duration": 0.24,
                                "start_time": 22.5,
                                "word": "MANY"
                            },
                            {
                                "confidence": 969,
                                "duration": 0.76,
                                "start_time": 22.8,
                                "word": "CHANGES"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.1,
                                "start_time": 23.9,
                                "word": "THE"
                            },
                            {
                                "confidence": 644,
                                "duration": 0.36,
                                "start_time": 24.1,
                                "word": "PURPLE"
                            },
                            {
                                "confidence": 270,
                                "duration": 0.24,
                                "start_time": 24.5,
                                "word": "TIDE"
                            },
                            {
                                "confidence": 465,
                                "duration": 0.18,
                                "start_time": 24.8,
                                "word": "WAS"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.22,
                                "start_time": 25.1,
                                "word": "TEN"
                            },
                            {
                                "confidence": 422,
                                "duration": 0.26,
                                "start_time": 25.3,
                                "word": "YEARS"
                            },
                            {
                                "confidence": 985,
                                "duration": 0.52,
                                "start_time": 25.6,
                                "word": "OLD"
                            },
                            {
                                "confidence": 699,
                                "duration": 0.3,
                                "start_time": 26.5,
                                "word": "MEN"
                            },
                            {
                                "confidence": 775,
                                "duration": 0.42,
                                "start_time": 26.8,
                                "word": "THINK"
                            },
                            {
                                "confidence": 991,
                                "duration": 0.12,
                                "start_time": 27.3,
                                "word": "AND"
                            },
                            {
                                "confidence": 355,
                                "duration": 0.46,
                                "start_time": 27.5,
                                "word": "PLAN"
                            },
                            {
                                "confidence": 988,
                                "duration": 0.12,
                                "start_time": 28,
                                "word": "AND"
                            },
                            {
                                "confidence": 540,
                                "duration": 0.5,
                                "start_time": 28.2,
                                "word": "SOMETIMES"
                            },
                            {
                                "confidence": 988,
                                "duration": 0.5,
                                "start_time": 28.8,
                                "word": "ACT"
                            }
                        ]
                    },
                    "start_time": 0.3
                }
            ]
        }
    ],
    "partial_results": [
        {
            "preview_results": [
                {
                    "transcript": "THE STORE OF WALLS WERE",
                    "words": [
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 0.3,
                            "word": "THE"
                        },
                        {
                            "confidence": 789,
                            "duration": 0.28,
                            "start_time": 0.48,
                            "word": "STORE"
                        },
                        {
                            "confidence": 990,
                            "duration": 0.06,
                            "start_time": 0.8,
                            "word": "OF"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.42,
                            "start_time": 0.96,
                            "word": "WALLS"
                        },
                        {
                            "confidence": 824,
                            "duration": 0.18,
                            "start_time": 1.46,
                            "word": "WERE"
                        }
                    ]
                }
            ],
            "stable_results": [
                {}
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "WITH COLOURED FROCKS THE",
                    "words": [
                        {
                            "confidence": 978,
                            "duration": 0.14,
                            "start_time": 2.02,
                            "word": "WITH"
                        },
                        {
                            "confidence": 429,
                            "duration": 0.36,
                            "start_time": 2.24,
                            "word": "COLOURED"
                        },
                        {
                            "confidence": 969,
                            "duration": 0.72,
                            "start_time": 2.66,
                            "word": "FROCKS"
                        },
                        {
                            "confidence": 987,
                            "duration": 0.08,
                            "start_time": 3.44,
                            "word": "THE"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "THE STORE OF WALLS WERE LINED",
                    "words": [
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 0.3,
                            "word": "THE"
                        },
                        {
                            "confidence": 789,
                            "duration": 0.28,
                            "start_time": 0.48,
                            "word": "STORE"
                        },
                        {
                            "confidence": 990,
                            "duration": 0.06,
                            "start_time": 0.8,
                            "word": "OF"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.42,
                            "start_time": 0.96,
                            "word": "WALLS"
                        },
                        {
                            "confidence": 824,
                            "duration": 0.18,
                            "start_time": 1.46,
                            "word": "WERE"
                        },
                        {
                            "confidence": 15,
                            "duration": 0.28,
                            "start_time": 1.7,
                            "word": "LINED"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "PEACE LEAGUE MET TO DISCUSS THEIR",
                    "words": [
                        {
                            "confidence": 432,
                            "duration": 0.32,
                            "start_time": 3.6,
                            "word": "PEACE"
                        },
                        {
                            "confidence": 951,
                            "duration": 0.34,
                            "start_time": 3.96,
                            "word": "LEAGUE"
                        },
                        {
                            "confidence": 241,
                            "duration": 0.34,
                            "start_time": 4.4,
                            "word": "MET"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 4.8,
                            "word": "TO"
                        },
                        {
                            "confidence": 983,
                            "duration": 0.4,
                            "start_time": 4.96,
                            "word": "DISCUSS"
                        },
                        {
                            "confidence": 981,
                            "duration": 0.16,
                            "start_time": 5.38,
                            "word": "THEIR"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "WITH COLOURED FROCKS THE",
                    "words": [
                        {
                            "confidence": 978,
                            "duration": 0.14,
                            "start_time": 2.02,
                            "word": "WITH"
                        },
                        {
                            "confidence": 429,
                            "duration": 0.36,
                            "start_time": 2.24,
                            "word": "COLOURED"
                        },
                        {
                            "confidence": 969,
                            "duration": 0.72,
                            "start_time": 2.66,
                            "word": "FROCKS"
                        },
                        {
                            "confidence": 987,
                            "duration": 0.08,
                            "start_time": 3.44,
                            "word": "THE"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "THEIR PLANS THE RISE TO FAME",
                    "words": [
                        {
                            "confidence": 981,
                            "duration": 0.16,
                            "start_time": 5.38,
                            "word": "THEIR"
                        },
                        {
                            "confidence": 981,
                            "duration": 0.64,
                            "start_time": 5.6,
                            "word": "PLANS"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.1,
                            "start_time": 6.28,
                            "word": "THE"
                        },
                        {
                            "confidence": 988,
                            "duration": 0.4,
                            "start_time": 6.44,
                            "word": "RISE"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 6.88,
                            "word": "TO"
                        },
                        {
                            "confidence": 983,
                            "duration": 0.26,
                            "start_time": 7.06,
                            "word": "FAME"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "PEACE LEAGUE MET TO DISCUSS",
                    "words": [
                        {
                            "confidence": 432,
                            "duration": 0.32,
                            "start_time": 3.6,
                            "word": "PEACE"
                        },
                        {
                            "confidence": 951,
                            "duration": 0.34,
                            "start_time": 3.96,
                            "word": "LEAGUE"
                        },
                        {
                            "confidence": 241,
                            "duration": 0.34,
                            "start_time": 4.4,
                            "word": "MET"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 4.8,
                            "word": "TO"
                        },
                        {
                            "confidence": 983,
                            "duration": 0.4,
                            "start_time": 4.96,
                            "word": "DISCUSS"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "A PERSON TAKES LUCK",
                    "words": [
                        {
                            "confidence": 984,
                            "duration": 0.04,
                            "start_time": 7.54,
                            "word": "A"
                        },
                        {
                            "confidence": 979,
                            "duration": 0.58,
                            "start_time": 7.64,
                            "word": "PERSON"
                        },
                        {
                            "confidence": 839,
                            "duration": 0.3,
                            "start_time": 8.32,
                            "word": "TAKES"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.2,
                            "start_time": 8.72,
                            "word": "LUCK"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "THEIR PLANS THE RISE TO FAME OF",
                    "words": [
                        {
                            "confidence": 981,
                            "duration": 0.16,
                            "start_time": 5.38,
                            "word": "THEIR"
                        },
                        {
                            "confidence": 981,
                            "duration": 0.64,
                            "start_time": 5.6,
                            "word": "PLANS"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.1,
                            "start_time": 6.28,
                            "word": "THE"
                        },
                        {
                            "confidence": 988,
                            "duration": 0.4,
                            "start_time": 6.44,
                            "word": "RISE"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 6.88,
                            "word": "TO"
                        },
                        {
                            "confidence": 983,
                            "duration": 0.26,
                            "start_time": 7.06,
                            "word": "FAME"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.06,
                            "start_time": 7.38,
                            "word": "OF"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "LUCK PAPER IS SCARCE SO RIGHT",
                    "words": [
                        {
                            "confidence": 893,
                            "duration": 0.58,
                            "start_time": 8.72,
                            "word": "LUCK"
                        },
                        {
                            "confidence": 831,
                            "duration": 0.3,
                            "start_time": 9.56,
                            "word": "PAPER"
                        },
                        {
                            "confidence": 987,
                            "duration": 0.14,
                            "start_time": 9.92,
                            "word": "IS"
                        },
                        {
                            "confidence": 464,
                            "duration": 0.68,
                            "start_time": 10.1,
                            "word": "SCARCE"
                        },
                        {
                            "confidence": 990,
                            "duration": 0.2,
                            "start_time": 10.9,
                            "word": "SO"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.18,
                            "start_time": 11.1,
                            "word": "RIGHT"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "A PERSON TAKES",
                    "words": [
                        {
                            "confidence": 984,
                            "duration": 0.04,
                            "start_time": 7.54,
                            "word": "A"
                        },
                        {
                            "confidence": 979,
                            "duration": 0.58,
                            "start_time": 7.64,
                            "word": "PERSON"
                        },
                        {
                            "confidence": 839,
                            "duration": 0.3,
                            "start_time": 8.32,
                            "word": "TAKES"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "RIGHT WITH MUCH CARE THE QUICK",
                    "words": [
                        {
                            "confidence": 157,
                            "duration": 0.42,
                            "start_time": 11.1,
                            "word": "RIGHT"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.2,
                            "start_time": 11.6,
                            "word": "WITH"
                        },
                        {
                            "confidence": 914,
                            "duration": 0.24,
                            "start_time": 11.8,
                            "word": "MUCH"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.58,
                            "start_time": 12.2,
                            "word": "CARE"
                        },
                        {
                            "confidence": 960,
                            "duration": 0.12,
                            "start_time": 12.9,
                            "word": "THE"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.16,
                            "start_time": 13.1,
                            "word": "QUICK"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "LUCK PAPER IS SCARCE SO",
                    "words": [
                        {
                            "confidence": 893,
                            "duration": 0.58,
                            "start_time": 8.72,
                            "word": "LUCK"
                        },
                        {
                            "confidence": 831,
                            "duration": 0.3,
                            "start_time": 9.56,
                            "word": "PAPER"
                        },
                        {
                            "confidence": 987,
                            "duration": 0.14,
                            "start_time": 9.92,
                            "word": "IS"
                        },
                        {
                            "confidence": 464,
                            "duration": 0.68,
                            "start_time": 10.1,
                            "word": "SCARCE"
                        },
                        {
                            "confidence": 990,
                            "duration": 0.2,
                            "start_time": 10.9,
                            "word": "SO"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "JUMPED ON THE SLEEPING",
                    "words": [
                        {
                            "confidence": 987,
                            "duration": 0.28,
                            "start_time": 14.1,
                            "word": "JUMPED"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.1,
                            "start_time": 14.5,
                            "word": "ON"
                        },
                        {
                            "confidence": 992,
                            "duration": 0.08,
                            "start_time": 14.6,
                            "word": "THE"
                        },
                        {
                            "confidence": 658,
                            "duration": 0.4,
                            "start_time": 14.7,
                            "word": "SLEEPING"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "RIGHT WITH MUCH CARE THE QUICK FOX",
                    "words": [
                        {
                            "confidence": 157,
                            "duration": 0.42,
                            "start_time": 11.1,
                            "word": "RIGHT"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.2,
                            "start_time": 11.6,
                            "word": "WITH"
                        },
                        {
                            "confidence": 914,
                            "duration": 0.24,
                            "start_time": 11.8,
                            "word": "MUCH"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.58,
                            "start_time": 12.2,
                            "word": "CARE"
                        },
                        {
                            "confidence": 960,
                            "duration": 0.12,
                            "start_time": 12.9,
                            "word": "THE"
                        },
                        {
                            "confidence": 975,
                            "duration": 0.4,
                            "start_time": 13.1,
                            "word": "QUICK"
                        },
                        {
                            "confidence": 931,
                            "duration": 0.46,
                            "start_time": 13.6,
                            "word": "FOX"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "NOZZLE OF THE FIRE HO",
                    "words": [
                        {
                            "confidence": 180,
                            "duration": 0.34,
                            "start_time": 16,
                            "word": "NOZZLE"
                        },
                        {
                            "confidence": 992,
                            "duration": 0.06,
                            "start_time": 16.4,
                            "word": "OF"
                        },
                        {
                            "confidence": 992,
                            "duration": 0.08,
                            "start_time": 16.5,
                            "word": "THE"
                        },
                        {
                            "confidence": 986,
                            "duration": 0.3,
                            "start_time": 16.6,
                            "word": "FIRE"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.12,
                            "start_time": 16.9,
                            "word": "HO"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "JUMPED ON THE SLEEPING CAT THE",
                    "words": [
                        {
                            "confidence": 987,
                            "duration": 0.28,
                            "start_time": 14.1,
                            "word": "JUMPED"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.1,
                            "start_time": 14.5,
                            "word": "ON"
                        },
                        {
                            "confidence": 992,
                            "duration": 0.08,
                            "start_time": 14.6,
                            "word": "THE"
                        },
                        {
                            "confidence": 658,
                            "duration": 0.4,
                            "start_time": 14.7,
                            "word": "SLEEPING"
                        },
                        {
                            "confidence": 976,
                            "duration": 0.5,
                            "start_time": 15.2,
                            "word": "CAT"
                        },
                        {
                            "confidence": 982,
                            "duration": 0.1,
                            "start_time": 15.8,
                            "word": "THE"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "HOSE WAS BRIGHT BRASS",
                    "words": [
                        {
                            "confidence": 321,
                            "duration": 0.36,
                            "start_time": 16.9,
                            "word": "HOSE"
                        },
                        {
                            "confidence": 887,
                            "duration": 0.18,
                            "start_time": 17.3,
                            "word": "WAS"
                        },
                        {
                            "confidence": 463,
                            "duration": 0.3,
                            "start_time": 17.6,
                            "word": "BRIGHT"
                        },
                        {
                            "confidence": 954,
                            "duration": 0.64,
                            "start_time": 18,
                            "word": "BRASS"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "NOZZLE OF THE FIRE",
                    "words": [
                        {
                            "confidence": 180,
                            "duration": 0.34,
                            "start_time": 16,
                            "word": "NOZZLE"
                        },
                        {
                            "confidence": 992,
                            "duration": 0.06,
                            "start_time": 16.4,
                            "word": "OF"
                        },
                        {
                            "confidence": 992,
                            "duration": 0.08,
                            "start_time": 16.5,
                            "word": "THE"
                        },
                        {
                            "confidence": 986,
                            "duration": 0.3,
                            "start_time": 16.6,
                            "word": "FIRE"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "ROUND CAP ON AS TIGHT AS",
                    "words": [
                        {
                            "confidence": 587,
                            "duration": 0.26,
                            "start_time": 19.4,
                            "word": "ROUND"
                        },
                        {
                            "confidence": 277,
                            "duration": 0.32,
                            "start_time": 19.7,
                            "word": "CAP"
                        },
                        {
                            "confidence": 988,
                            "duration": 0.14,
                            "start_time": 20.2,
                            "word": "ON"
                        },
                        {
                            "confidence": 977,
                            "duration": 0.12,
                            "start_time": 20.4,
                            "word": "AS"
                        },
                        {
                            "confidence": 967,
                            "duration": 0.22,
                            "start_time": 20.5,
                            "word": "TIGHT"
                        },
                        {
                            "confidence": 987,
                            "duration": 0.1,
                            "start_time": 20.8,
                            "word": "AS"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "HOSE WAS BRIGHT BRASS SCREW THE",
                    "words": [
                        {
                            "confidence": 321,
                            "duration": 0.36,
                            "start_time": 16.9,
                            "word": "HOSE"
                        },
                        {
                            "confidence": 887,
                            "duration": 0.18,
                            "start_time": 17.3,
                            "word": "WAS"
                        },
                        {
                            "confidence": 463,
                            "duration": 0.3,
                            "start_time": 17.6,
                            "word": "BRIGHT"
                        },
                        {
                            "confidence": 954,
                            "duration": 0.64,
                            "start_time": 18,
                            "word": "BRASS"
                        },
                        {
                            "confidence": 166,
                            "duration": 0.36,
                            "start_time": 18.9,
                            "word": "SCREW"
                        },
                        {
                            "confidence": 956,
                            "duration": 0.08,
                            "start_time": 19.3,
                            "word": "THE"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "BRINGS AS MANY",
                    "words": [
                        {
                            "confidence": 978,
                            "duration": 0.28,
                            "start_time": 22,
                            "word": "BRINGS"
                        },
                        {
                            "confidence": 875,
                            "duration": 0.12,
                            "start_time": 22.4,
                            "word": "AS"
                        },
                        {
                            "confidence": 790,
                            "duration": 0.24,
                            "start_time": 22.5,
                            "word": "MANY"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "ROUND CAP ON AS TIGHT AS NEEDED TIME",
                    "words": [
                        {
                            "confidence": 587,
                            "duration": 0.26,
                            "start_time": 19.4,
                            "word": "ROUND"
                        },
                        {
                            "confidence": 277,
                            "duration": 0.32,
                            "start_time": 19.7,
                            "word": "CAP"
                        },
                        {
                            "confidence": 988,
                            "duration": 0.14,
                            "start_time": 20.2,
                            "word": "ON"
                        },
                        {
                            "confidence": 977,
                            "duration": 0.12,
                            "start_time": 20.4,
                            "word": "AS"
                        },
                        {
                            "confidence": 967,
                            "duration": 0.22,
                            "start_time": 20.5,
                            "word": "TIGHT"
                        },
                        {
                            "confidence": 987,
                            "duration": 0.1,
                            "start_time": 20.8,
                            "word": "AS"
                        },
                        {
                            "confidence": 990,
                            "duration": 0.66,
                            "start_time": 20.9,
                            "word": "NEEDED"
                        },
                        {
                            "confidence": 990,
                            "duration": 0.3,
                            "start_time": 21.7,
                            "word": "TIME"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "BRINGS US MANY CHANGES THE PURPLE TIDE",
                    "words": [
                        {
                            "confidence": 978,
                            "duration": 0.28,
                            "start_time": 22,
                            "word": "BRINGS"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.12,
                            "start_time": 22.4,
                            "word": "US"
                        },
                        {
                            "confidence": 965,
                            "duration": 0.24,
                            "start_time": 22.5,
                            "word": "MANY"
                        },
                        {
                            "confidence": 969,
                            "duration": 0.76,
                            "start_time": 22.8,
                            "word": "CHANGES"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.1,
                            "start_time": 23.9,
                            "word": "THE"
                        },
                        {
                            "confidence": 644,
                            "duration": 0.36,
                            "start_time": 24.1,
                            "word": "PURPLE"
                        },
                        {
                            "confidence": 270,
                            "duration": 0.24,
                            "start_time": 24.5,
                            "word": "TIDE"
                        }
                    ]
                }
            ],
            "stable_results": [
                {}
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "WAS TEN YEARS OLD MEN",
                    "words": [
                        {
                            "confidence": 465,
                            "duration": 0.18,
                            "start_time": 24.8,
                            "word": "WAS"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.22,
                            "start_time": 25.1,
                            "word": "TEN"
                        },
                        {
                            "confidence": 422,
                            "duration": 0.26,
                            "start_time": 25.3,
                            "word": "YEARS"
                        },
                        {
                            "confidence": 985,
                            "duration": 0.52,
                            "start_time": 25.6,
                            "word": "OLD"
                        },
                        {
                            "confidence": 13,
                            "duration": 0.18,
                            "start_time": 26.5,
                            "word": "MEN"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "BRINGS US MANY CHANGES THE PURPLE TIDE",
                    "words": [
                        {
                            "confidence": 978,
                            "duration": 0.28,
                            "start_time": 22,
                            "word": "BRINGS"
                        },
                        {
                            "confidence": 973,
                            "duration": 0.12,
                            "start_time": 22.4,
                            "word": "US"
                        },
                        {
                            "confidence": 965,
                            "duration": 0.24,
                            "start_time": 22.5,
                            "word": "MANY"
                        },
                        {
                            "confidence": 969,
                            "duration": 0.76,
                            "start_time": 22.8,
                            "word": "CHANGES"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.1,
                            "start_time": 23.9,
                            "word": "THE"
                        },
                        {
                            "confidence": 644,
                            "duration": 0.36,
                            "start_time": 24.1,
                            "word": "PURPLE"
                        },
                        {
                            "confidence": 270,
                            "duration": 0.24,
                            "start_time": 24.5,
                            "word": "TIDE"
                        }
                    ]
                }
            ]
        },
        {
            "preview_results": [
                {
                    "transcript": "MEN THINK AND PLAN AND SOMETIME",
                    "words": [
                        {
                            "confidence": 699,
                            "duration": 0.3,
                            "start_time": 26.5,
                            "word": "MEN"
                        },
                        {
                            "confidence": 775,
                            "duration": 0.42,
                            "start_time": 26.8,
                            "word": "THINK"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 27.3,
                            "word": "AND"
                        },
                        {
                            "confidence": 355,
                            "duration": 0.46,
                            "start_time": 27.5,
                            "word": "PLAN"
                        },
                        {
                            "confidence": 988,
                            "duration": 0.12,
                            "start_time": 28,
                            "word": "AND"
                        },
                        {
                            "confidence": 1,
                            "duration": 0.4,
                            "start_time": 28.2,
                            "word": "SOMETIME"
                        }
                    ]
                }
            ],
            "stable_results": [
                {
                    "transcript": "WAS TEN YEARS OLD",
                    "words": [
                        {
                            "confidence": 465,
                            "duration": 0.18,
                            "start_time": 24.8,
                            "word": "WAS"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.22,
                            "start_time": 25.1,
                            "word": "TEN"
                        },
                        {
                            "confidence": 422,
                            "duration": 0.26,
                            "start_time": 25.3,
                            "word": "YEARS"
                        },
                        {
                            "confidence": 985,
                            "duration": 0.52,
                            "start_time": 25.6,
                            "word": "OLD"
                        }
                    ]
                }
            ]
        },
        {
            "stable_results": [
                {
                    "transcript": "MEN THINK AND PLAN AND SOMETIMES ACT",
                    "words": [
                        {
                            "confidence": 699,
                            "duration": 0.3,
                            "start_time": 26.5,
                            "word": "MEN"
                        },
                        {
                            "confidence": 775,
                            "duration": 0.42,
                            "start_time": 26.8,
                            "word": "THINK"
                        },
                        {
                            "confidence": 991,
                            "duration": 0.12,
                            "start_time": 27.3,
                            "word": "AND"
                        },
                        {
                            "confidence": 355,
                            "duration": 0.46,
                            "start_time": 27.5,
                            "word": "PLAN"
                        },
                        {
                            "confidence": 988,
                            "duration": 0.12,
                            "start_time": 28,
                            "word": "AND"
                        },
                        {
                            "confidence": 540,
                            "duration": 0.5,
                            "start_time": 28.2,
                            "word": "SOMETIMES"
                        },
                        {
                            "confidence": 988,
                            "duration": 0.5,
                            "start_time": 28.8,
                            "word": "ACT"
                        }
                    ]
                }
            ]
        }
    ]
}
```

## cpa_amd_streaming.py

`cpa_amd_streaming.py` is also based on ASR streaming mode, but using different
grammar file to activate `CPA` and `AMD` modes respectively used in this example.

`default_cpa.grxml` and `default_amd.grmxl` respectively, and we are using sample
audio files to be used for detecting a human residence and a fax tone.

```python
 # Should return "Human Residence" classification
result = cpa_amd_streaming_common(api_helper=api_helper,
                                  grammar_file_path='test_data/default_cpa.grxml',
                                  audio_file='test_data/human_residence.ulaw',
                                  audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                                  language_code='en')
print(">>>> CPA result returned:\n", json.dumps(result, indent=4, sort_keys=True))

# Should return "FAX" classification
result = cpa_amd_streaming_common(api_helper=api_helper,
                                  grammar_file_path='test_data/default_amd.grxml',
                                  audio_file='test_data/fax_tone_short.ulaw',
                                  audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                                  language_code='en')
print(">>>> AMD result returned:\n", json.dumps(result, indent=4, sort_keys=True))
```

This is the default cpa grammar file we are using for this test, we are using a
value if `1800` for human residence, `3000` for human business and above `3500` for
unknown silence

```xml
<?xml version='1.0'?> 

<!-- ************************************************************************************ -->
<!-- This is a special grammar used to switch decode modes to Call Progress Analysis mode --> 

<grammar xml:lang="en-US" version="1.0" root="root" mode="voice"
          xmlns="http://www.w3.org/2001/06/grammar"
          tag-format="semantics/1.0.2006">  

	<!-- ******************************************************************************** -->
	<!-- This value changes the detection mode to Call Progress Analysis                  -->
	<!-- ******************************************************************************** -->
	<meta name="STREAM|DETECTION_MODE" content="CPA"/> 

	<!-- ******************************************************************************** -->
	<!-- These values may be changed to customize CPA timeouts for certain states         -->
	<!-- ******************************************************************************** -->
	<meta name="STREAM|CPA_HUMAN_RESIDENCE_TIME"  content="1800"/>
	<meta name="STREAM|CPA_HUMAN_BUSINESS_TIME"  content="3000"/>
	<meta name="STREAM|CPA_UNKNOWN_SILENCE_TIMEOUT" content="3500"/>
	<!-- ******************************************************************************** -->
	<!-- These values may be changed to modify the semantic interpretations returned      -->
	<!-- ******************************************************************************** --> 

	<meta name="HUMAN_RESIDENCE_CUSTOM_INPUT_TEXT" content="HUMAN RESIDENCE"/>
	<meta name="HUMAN_BUSINESS_CUSTOM_INPUT_TEXT"  content="HUMAN BUSINESS"/>
	<meta name="UNKNOWN_SPEECH_CUSTOM_INPUT_TEXT"  content="UNKNOWN SPEECH"/>
	<meta name="UNKNOWN_SILENCE_CUSTOM_INPUT_TEXT" content="UNKNOWN SILENCE"/>    
	<rule id="root" scope="public">
	    <one-of>
	        <item>HUMAN RESIDENCE<tag>out="RESIDENCE"</tag>
	        </item>
	        <item>HUMAN BUSINESS<tag>out="BUSINESS"</tag>
	        </item>
	        <item>UNKNOWN SPEECH<tag>out="MACHINE"</tag>
	        </item>
	        <item>UNKNOWN SILENCE<tag>out="SILENCE"</tag>
	        </item> 
	    </one-of>
	</rule> 
</grammar>
```

This is the one for `AMD`, with the corresponding tags for each type of tone:

```xml
<?xml version='1.0'?>

<!-- **************************************************************************************** -->
<!-- This is a special grammar used to switch decode modes to tone detection mode             -->
<!-- **************************************************************************************** -->

<grammar xml:lang="en-US" version="1.0" root="root" mode="voice"
         xmlns="http://www.w3.org/2001/06/grammar"
         tag-format="semantics/1.0.2006"> 

	<!-- ******************************************************************************** -->
	<!-- This value changes the detection mode to tone detection mode                     -->
	<!-- ******************************************************************************** -->
	<meta name="STREAM|DETECTION_MODE"      content="Tone"/>


	<!-- ******************************************************************************** -->
	<!-- Activate/Deactivate AMD, FAX, SIT, BUSY detection                                      -->
	<!-- ******************************************************************************** -->
	<meta name="AMD_CUSTOM_ENABLE"          content="true"/>
	<meta name="FAX_CUSTOM_ENABLE"          content="true"/>
	<meta name="SIT_CUSTOM_ENABLE"          content="true"/>
	<meta name="BUSY_CUSTOM_ENABLE"         content="false"/>
	
	
	<!-- ******************************************************************************** -->
	<!-- These values may be changed to modify the semantic interpretations returned      -->
	<!-- ******************************************************************************** -->

	<!-- 
		The below meta tags map each state (AMD/FAX/SIT) to an input text in the SRGS 
		grammar below. This is the mechanism used to map each of the states to an input 
		text in the grammar.
		***************************************************************************** -->

	
	<meta name="AMD_CUSTOM_INPUT_TEXT"                      content="BEEP"/>
	<meta name="FAX_CUSTOM_INPUT_TEXT"                      content="FAX"/>
	<meta name="BUSY_CUSTOM_INPUT_TEXT"                     content="BUSY"/>

	<meta name="SIT_REORDER_LOCAL_CUSTOM_INPUT_TEXT"        content="SIT REORDER LOCAL"/>
	<meta name="SIT_VACANT_CODE_CUSTOM_INPUT_TEXT"          content="SIT VACANT CODE"/>
	<meta name="SIT_NO_CIRCUIT_LOCAL_CUSTOM_INPUT_TEXT"     content="SIT NO CIRCUIT LOCAL"/>
	<meta name="SIT_INTERCEPT_CUSTOM_INPUT_TEXT"            content="SIT INTERCEPT"/>
	<meta name="SIT_REORDER_DISTANT_CUSTOM_INPUT_TEXT"      content="SIT REORDER DISTANT"/>
	<meta name="SIT_NO_CIRCUIT_DISTANT_CUSTOM_INPUT_TEXT"   content="SIT NO CIRCUIT DISTANT"/>
	<meta name="SIT_OTHER_CUSTOM_INPUT_TEXT"                content="SIT OTHER"/>
	

	
	<!-- 
		Below is the SRGS grammar. If the input text is changed in any of them, the 
		appropriate changes need to be made to the above states to input text mapping. 
		The semantic interpretation can be changed as necessary by modifying the out  
		tags below.
		***************************************************************************** -->
	
	<rule id="root" scope="public">
		<one-of>
			<item>BEEP<tag>out="BEEP"</tag></item>
			<item>FAX<tag>out="FAX"</tag></item>
			<item>BUSY<tag>out="BUSY"</tag></item>
			<item>SPEECH<tag>out="SPEECH"</tag></item>
			
			<item>SIT REORDER LOCAL<tag>out="SIT"</tag></item>
			<item>SIT VACANT CODE<tag>out="SIT"</tag></item>
			<item>SIT NO CIRCUIT LOCAL<tag>out="SIT"</tag></item>
			<item>SIT INTERCEPT<tag>out="SIT"</tag></item>
			<item>SIT REORDER DISTANT<tag>out="SIT"</tag></item>
			<item>SIT NO CIRCUIT DISTANT<tag>out="SIT"</tag></item>
			<item>SIT OTHER<tag>out="SIT"</tag></item>
			
		</one-of>
	</rule>
	
</grammar>
```

## cpa_amd_streaming.py results

Below are the results of the sample script, including audio chunks corresponding
to the audio streaming.

We can see in the CPA results that show a confidence level of 990 for the human
residence audio file, then below that we see additional audio chunks now for the
fax sample audio file, and finally, the AMD results showing a confidence level
of 990 for FAX detection.

```shell
>> session_id in response_handler:  17826d23-3b2c-416b-b056-525068dc32f9
1. session_id from SessionCreate:  17826d23-3b2c-416b-b056-525068dc32f9
2. Called AudioStreamCreate - no response expected
>> RESULT CALLBACK in response_handler
3. interaction_id extracted from InteractionCreateASR response is:  83de0d93-2c27-4c4d-bd10-a5537a0156dc
4. called InteractionBeginProcessing for ASR (no response expected) interaction_id:  83de0d93-2c27-4c4d-bd10-a5537a0156dc
sending audio chunk  1  more bytes =  True
sending audio chunk  2  more bytes =  True
sending audio chunk  3  more bytes =  True
sending audio chunk  4  more bytes =  True
sending audio chunk  5  more bytes =  True
sending audio chunk  6  more bytes =  True
sending audio chunk  7  more bytes =  True
sending audio chunk  8  more bytes =  True
sending audio chunk  9  more bytes =  True
sending audio chunk  10  more bytes =  True
sending audio chunk  11  more bytes =  True
sending audio chunk  12  more bytes =  True
sending audio chunk  13  more bytes =  True
sending audio chunk  14  more bytes =  True
sending audio chunk  15  more bytes =  True
sending audio chunk  16  more bytes =  True
sending audio chunk  17  more bytes =  True
sending audio chunk  18  more bytes =  True
sending audio chunk  19  more bytes =  True
sending audio chunk  20  more bytes =  True
sending audio chunk  21  more bytes =  True
sending audio chunk  22  more bytes =  True
sending audio chunk  23  more bytes =  True
sending audio chunk  24  more bytes =  True
sending audio chunk  25  more bytes =  True
sending audio chunk  26  more bytes =  True
sending audio chunk  27  more bytes =  True
sending audio chunk  28  more bytes =  True
sending audio chunk  29  more bytes =  True
sending audio chunk  30  more bytes =  True
sending audio chunk  31  more bytes =  True
sending audio chunk  32  more bytes =  True
sending audio chunk  33  more bytes =  True
sending audio chunk  34  more bytes =  True
sending audio chunk  35  more bytes =  True
sending audio chunk  36  more bytes =  True
sending audio chunk  37  more bytes =  True
sending audio chunk  38  more bytes =  True
sending audio chunk  39  more bytes =  True
sending audio chunk  40  more bytes =  True
sending audio chunk  41  more bytes =  True
sending audio chunk  42  more bytes =  True
sending audio chunk  43  more bytes =  True
sending audio chunk  44  more bytes =  False
5. Completed streaming audio
6. Final Results ready: True
>>>> CPA result returned:
 {
    "final_results": [
        {
            "n_bests": [
                {
                    "confidence": 990,
                    "duration": 230,
                    "phrase": {
                        "transcript": "HUMAN RESIDENCE"
                    },
                    "semantic_interpretations": [
                        {
                            "custom_interpretation": "[object Object]",
                            "grammar_label": "file:///usr/bin/Buffer_Grammar",
                            "input_text": "HUMAN RESIDENCE",
                            "interpretation": "RESIDENCE",
                            "language": "EN-US",
                            "mode": "voice",
                            "tag_format": "semantics/1.0.2006",
                            "top_rule": "root"
                        }
                    ],
                    "start_time": 410
                }
            ]
        }
    ],
    "interaction_id": "83de0d93-2c27-4c4d-bd10-a5537a0156dc"
}
>> session_id in response_handler:  11933250-0ff3-4de9-9657-30879185adc2
1. session_id from SessionCreate:  11933250-0ff3-4de9-9657-30879185adc2
2. Called AudioStreamCreate - no response expected
>> RESULT CALLBACK in response_handler
3. interaction_id extracted from InteractionCreateASR response is:  8f9d7603-5e1e-410c-a924-613c772b4085
4. called InteractionBeginProcessing for ASR (no response expected) interaction_id:  8f9d7603-5e1e-410c-a924-613c772b4085
sending audio chunk  1  more bytes =  True
sending audio chunk  2  more bytes =  True
sending audio chunk  3  more bytes =  True
sending audio chunk  4  more bytes =  True
sending audio chunk  5  more bytes =  True
sending audio chunk  6  more bytes =  True
sending audio chunk  7  more bytes =  True
sending audio chunk  8  more bytes =  True
sending audio chunk  9  more bytes =  True
sending audio chunk  10  more bytes =  True
sending audio chunk  11  more bytes =  True
sending audio chunk  12  more bytes =  False
5. Completed streaming audio
6. Final Results ready: True
>>>> AMD result returned:
 {
    "final_results": [
        {
            "n_bests": [
                {
                    "confidence": 990,
                    "duration": 1030,
                    "phrase": {
                        "transcript": "FAX"
                    },
                    "semantic_interpretations": [
                        {
                            "custom_interpretation": "[object Object]",
                            "grammar_label": "file:///usr/bin/Buffer_Grammar",
                            "input_text": "FAX",
                            "interpretation": "FAX",
                            "language": "EN-US",
                            "mode": "voice",
                            "tag_format": "semantics/1.0.2006",
                            "top_rule": "root"
                        }
                    ],
                    "start_time": 210
                }
            ]
        }
    ],
    "interaction_id": "8f9d7603-5e1e-410c-a924-613c772b4085"
}

```
## tts_example.py

The TTS example is pretty straightforward, the text to be synthesized is defined
via SSML and the voice, audio format, and language are shown below.
The option to `save_audio_file` is set to `False` in this example, but it can be
modified to save the audio file to a local folder or drive.

```python
# Set to True to save the generated synthesized audio file
save_audio_file=False

ssml_text = api_helper.get_ssml_file_by_ref('test_data/mark_element.ssml')
audio_data_len, output_filepath = tts_common(api_helper=api_helper,
                                             language_code='en-us', voice='Chris',
                                             audio_format='STANDARD_AUDIO_FORMAT_ULAW_8KHZ',
                                             text=ssml_text,
                                             save_audio_file=save_audio_file)

print("\nSynthesis completed with ", audio_data_len, "bytes")
if save_audio_file:
    print(" - saved audio file to ", output_filepath)
```

This is the SSML file that is used for the TTS example. The idea is to
synthesize the phrase: `Go from here, to there!` using Chris’ voice.

```
<?xml version="1.0"?>
<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    version="1.1"
    xsi:schemaLocation="http://www.w3.org/2001/10/synthesis
    http://www.w3.org/TR/speech-synthesis11/synthesis.xsd"
    xml:lang="en-US">
<voice name="Chris">
    Go from
    <mark name="here"/>
    here, to
    <mark name="there"/>
    there!
</voice>
</speak>

```
## tts_example.py results

The audio synthesis results for the `tts_example.py` sample are shown below, in
this case showing there were 5 words successfully synthesized, 1 sentence, and
the voice used was `Chris`

```shell
>> session_id in response_handler:  04c37e79-dc2e-4574-afa1-f38f582362d7
1. session_id from SessionCreate:  04c37e79-dc2e-4574-afa1-f38f582362d7
>> RESULT CALLBACK in response_handler
Ignoring partial results while waiting for final_results
SSML marks synthesized:  2
 - mark Name: [ here ] at offset: 5131
 - mark Name: [ there ] at offset: 14254
Words synthesized:  5
Sentences synthesized:  1
Voice used:  Chris

Synthesis completed with  19220 bytes
```

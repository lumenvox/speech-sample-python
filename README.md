# LumenVox API Sample Code

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This is a sample project that demonstrates how to communicate with
the LumenVox API over gRPC using the published `.proto` definition
files.

It is designed to work optimally with a recent version of Python. 
We recommend at least version 3.9, but please refer to the latest
version available.

## Virtual Environment

Creating and using a virtual environment for your Python project will
help greatly, and allow you to utilize the project dependencies file
with ease.

Virtual Environments (or venv) is too deep a topic to cover here, so
please review online references of how best to create these. There are
several good guides available, such as this one:
https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/

We recommend you create a virtual environment for your project 
within the project root using something like the following:

```shell
python -m venv venv
```
This will create a `venv/` folder within your project which will be
used to hold the various modules used by the project.

Once you have created and activated your [venv](https://docs.python.org/3/library/venv.html),
you should initialize the environment using the provided 
`requirements.txt` file which describes the module dependencies. To
do this run:
```shell
pip install -r requirements.txt
```

## Quick Start

To learn how to use protobuf, please follow the excellent tutorials
provided by Google at:

[https://developers.google.com/protocol-buffers/docs/tutorials](https://developers.google.com/protocol-buffers/docs/tutorials)

or review their code samples in the [examples](https://github.com/protocolbuffers/protobuf/blob/main/examples)
directory.

### Working with .proto files

The .proto files are available to LumenVox customers and allow
access to the LumenVox API set of functionality.

Before using the .proto (protobuf definition) files, they need to
be `compiled` into a format that is compatible with the language
being used. In this case, Python.

See the [this page](https://github.com/protocolbuffers/protobuf)
for details about how to use protoc to generate the API stubs.

There is a helper script you can run to easily generate these files:
```shell
python make_stubs.py
```

This should generate files in the `/lumenvox/api/` and `/google/`
directories below your project root.

These files can be used by Python applications to talk to the
LumenVox API using the gRPC protocol. This is needed in order
to run the sample applications described here.

## TLS Connectivity

These samples assume TLS connectivity is used between the Python client
and your LumenVox API server. This is controlled by the `ENABLE_TLS` flag.

In order to make a valid TLS connection, you must create a certificate for
the server and assign it to the ingress. The public certificate (.crt) file
should be copied into the Python sample code project folder and named
`server.crt`. This file will be used to validate the server certificate
when using TLS connectivity. Without this, you may encounter TLS or SSL
errors when you try to connect.

> Note that this configuration also works with self-signed certificates,
> with the caveat that you should always use appropriate certificates in
> production, and understand the implications of using self-signed versus
> trusted CA-signed certificates.

Using connectivity without TLS being enabled is also possible if your
server is configured to support this, however the use of TLS is recommended.

Also, TLS connections are often on different ports than non-TLS, so if you
are switching between the two, you should be aware of this and assign your
`LUMENVOX_API_SERVICE` port value accordingly.

When using connections to a Kubernetes ingress, you often need to specify
the domain name connection rather than IP address, so that the ingress
can correctly route your requests. The example included in the code is
`lumenvox-api.testmachine.com`, however your Kubernetes configuration
will likely differ from this, so please use the correct setting. You may
also need to update your hosts file or DNS to correctly define this
domain name to the Kubernetes IP address, depending on your environment.

## LumenVox Helper Functions

The bulk of the relatively complex code that communicates with
the LumenVox API, along with a number of helper functions is
located in the `lumenvox_helper_function.py` file. This is used
for all examples, and greatly simplifies the amount of coding
needed to run and understand how to interact with the API.

Once you become more familiar with the API, you can look at how
these functions operate, and then work on your own specialized
functions instead if you prefer.

> Before running any tests, please be sure to specify the
> address of your target LumenVox server by updating the
> following settings in `lumenvox_helper_function.py`:
>
> * `LUMENVOX_API_SERVICE` address of your server
* `ENABLE_TLS` informs server that a certification should be validated
> * `deploymentid` your assigned deployment ID in the server
> * `operatorid` that you wish to use (identifies API user)

Note that if you do not know your assigned `deploymentid`, you may
try using the default installed with the system, which is the value
included in the file. If this works, you can practice with this, but
at some point you should remove this temporary startup deployment ID
and use a more permanent one.

Similarly, for the `operatorid`, if you do not have some identifier
that you wish to use for tracking who is making API requests, then
you can use the sample one included for now. In production, it is
best to use your own operator ID values to understand how or what is
making API calls, which can be seen in the logs.

Using this common helper code, you can see how relatively simple
it is to understand the steps involved in performing the following
example operations

### Callbacks

Callbacks form part of the LumenVox API. These are used to
communicate events and notifications from the speech system to the
API client.

Such callback messages are described towards the middle of the
included `session.proto` file in the `protobufs/lumenvox/api`
directory. These include:

* PartialResult
* FinalResult
* VadEvent
* SessionEvent

These are defined in the `SessionResponse` message type. The
most important callback message is the `SessionEvent`, which is also
the first message sent back to the API client after `SessionCreate`
is called. This session_id value for this message is used as a
parameter for other API calls.

### Threading Model

Since callbacks can be received at any time, it is generally practical
to use a worker thread to listen for these notifications and process
them when they arrive. In this sample code, such a worker thread is
started within the `run_user_coroutine` call.

Any callback messages received by the API client code (such as these
examples), will be received and handled by the session-specific 
`response_handler` routine, which in these examples, simply places the 
callback messages into the appropriate queues that correspond to the 
specified target session_id.

Note that this configuration should allow for multiple concurrent
session operations to be performed, however these simple examples
do not show this.

For production code, it is assumed that some more structured
approach is taken for processing these callback messages. The aim
of this sample code was simplicity using Python scripting that
many people will be familiar with.

### Audio Streaming

Note that in the examples performing audio streaming into the ASR,
a very simple loop is used with a small delay to emulate real-world
audio streaming from a production application.

For the sake of creating the simplest, and most easily understood
code, this approach was taken rather than creating another worker
thread to perform this audio streaming in the background.

### Production Applications

Throughout the included examples, the `en-US` language code was
selected, as well as the included grammars and other referenced
sample files, however if your system uses a different language,
you should modify the samples accordingly.

> Please note that the sample code purposefully contains no error
> or exception checking to make the code more easily read and 
> understood. 

It is assumed that application developers will implement their own
robust handling. It is also assumed that in production applications,
threading model and behavior would likely be handled in a more 
robust and/or scalable way than shown in these examples.

In other words, please don't simply copy these examples and use
them in production - this would not likely be optimal. These are
designed to be very simple examples.

### Language Independence

This sample code is written using Python, which was selected for
its simplicity to clearly show interactions with the API. Since
gRPC is used, many programming languages are automatically supported,
so your choice of these should be driven by your business needs,
not these simplistic examples.

See the [gRPC documentation](https://grpc.io/docs/languages/) for
details about supported languages and how to utilize protocol
buffers with those languages. The steps described here for Python
are very similar for other languages supported by gRPC.

If you are using another programming language, you will likely
need to create your own handler functions, or something similar
to the included LumenVox Speech Helper. Converting these functions
to other languages should be relatively straight-forward following
the comments.

### Sample Audio

Note that some sample audio used for the transcription example 
is courtesy of the [Open Speech Repository](https://www.voiptroubleshooter.com/open_speech/index.html).
Please visit their website for details and conditions of use.

## Batch Mode ASR Decode

See the `asr_batch_example.py` script for an example of how to
perform a batch-mode ASR decode using the Speech API.

A batch-mode decode does not use Voice Activity Detection (VAD)
and instead, loads all the audio into the system at once, then
decodes are processed without waiting for VAD activity to
trigger it. This may be faster in certain situations, however it
also behaves differently due to the way this is implemented.

## Streaming ASR Decode Example

See the `asr_streaming_example.py` script for an example of how to
perform a streaming-mode ASR decode using the Speech API.

A streaming-mode decode uses Voice Activity Detection (VAD),
and streams chunks of audio into the system, relying on
VAD to determine start and end of speech to trigger processing.

## Streaming Transcription Example

See the `asr_transcription_example.py` script for an example of
how to perform a streaming transcription using the Speech API.

Transcription is very similar to grammar-based ASR decodes,
but uses a special grammar file that is only used to trigger
transcription mode instead of grammar-based ASR decodes.

Transcription can be performed in realtime using this streaming
example, or it could be used in batch-mode operations similar to
how the Batch Mode ASR example is used. This batch-mode is sometimes
called offline transcription mode may be slightly more efficient
and faster than realtime streaming, but requires all the audio
be sent at once, so may or may not be suitable for your use case.

Partial results can be enabled using the `enable_partial_results`
field in RecognitionSettings. They are turned off by default, but
by setting `enable_partial_results.value` to `True`, partial
results can be received.

### `asr_transcription_multiple.py `

This script allows for running multiple streaming transcription interactions at once, given the audio files provided in
the system arguments. The results of the interactions will be written to the specified CSV file.

```shell
py asr_transcription_multiple.py ['name of file to write to'] [directory containing audio files] [optional: extensions to limit to]
# ex: 
# py asr_transcription_multiple.py transcription_results.csv C:\audio_files .ulaw
```

### Dialects
The `asr_transcription_dialect_example.py` uses the streaming transcription
code to demonstrate the differences between results based on dialect (ex. 
'en-us' vs. 'en-gb').

## Enhanced Transcription Example

See the `asr_enhanced_transcription.py` script for an example of
how to perform an enhanced transcription using the Speech API. This is 
based on the code used for the streaming transcription example.

Enhanced transcription is performed by including addition grammars to
the transcription interaction. Semantic interpretations will also be included
within the results should the content of the audio match any of the specified
grammars.

## Normalized Transcription Example
See the `asr_transcription_normalization.py` script for an example of
how to perform an enhanced transcription using the Speech API. This is 
based on the code used for the streaming transcription example.

Normalized transcription is performed by including normalization settings
upon interaction creation. This will include additional, normalization-specific
output, on top of the transcript received basic transcription.

## Transcription Using Alias
See the `asr_aliaslexicon_transcription_example.py` script for an example of
how to perform a transcription interaction with aliases. This is 
based on the code used for the batch ASR example, as this requires a grammar.

The grammar for aliases must include a URI reference to a lexicon XML, the
contents of which will be visible in the results should transcription include
words as aliases under a lexeme in the lexicon file.

## Text To Speech Example

The `tts_example.py` script demonstrated a simple TTS synthesis.
In the example, an SSML file is loaded, which contains SSML marks
to show some moderately complex functionality and the level of
details that can be returned from the synthesis result.

You can optionally request the synthesized audio be saved to disk
so that you can listen to it if desired.

## Grammar Parse Example

See the `grammar_parse_example.py` script for an example of how to
perform a grammar parse interaction using the Speech API.

Grammar parse interactions will also accept builtin grammars or 
URL-referenced grammars if one is not locally available. 

## Streaming CPA and AMD Decodes

See the `cpa_amd_streaming_example.py` script for an example of how to
perform a streaming-mode Call Progress Analysis (CPA) and Tone Detection
(AMD) decodes using the Speech API.

A streaming-mode decode uses Voice Activity Detection (VAD),
and streams chunks of audio into the system, relying on
VAD to determine start and end of speech to trigger processing.

The CPA example uses the default CPA grammar, which enables classification
of the following:

* Human Residence (human speech less than 1800ms)
* Human Business (human speech between 1800 and 3000ms)
* Unknown Speech (human speech > 3000ms - assumed to be "machine")
* Unknown Silence (no human speech)

The example include an audio of Human Residence, which is the expected result

For AMD testing, the sample uses the default AMD grammar, which can
classify a number of things, including

* FAX Tone
* Busy Tone (disabled by default)
* Special Information Tones (SIT)
* Answering machine beep

The example include a Fax tone audio, which is the expected result

## Voice Biometrics Example

The `vb_enroll_and_verify_example.py` script demonstrates an enrollment and
verification in the Voice Biometrics system. This example makes use of some
new audio files which can be found in the `test_data/VB` directory.

Note that in order for this test to work, you will need to define the correct
endpoints for both the Biometric API and the Management API. Like the Speech
API, you will need to update your hosts file or DNS to make this work.

## Normalize Text Example

See the `normalize_text_example.py` script for an example of how to
perform a "normalize text" interaction using the Speech API.

Normalize text interactions require a text transcript and normalization
settings to run. 


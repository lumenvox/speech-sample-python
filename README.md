# LumenVox API Sample Code

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This is a sample project that demonstrates how to communicate with
the LumenVox API over gRPC using the published `.proto` definition
files.

The sample code is designed to work with Python 3.10.

## Virtual Environment

Creating and using a virtual environment for your Python project will
help greatly, and allow you to utilize the project dependencies file
with ease.

Virtual Environments (or venv) are too deep a topic to cover here, so
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

To learn how to use protocol buffers or protobuf, please follow the excellent tutorials
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

See [this page](https://github.com/protocolbuffers/protobuf)
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
User connectivity data can be viewed or modified in `lumenvox_api_user_connection_data.py`.

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

## LumenVox API Handler and Helper Functions

The bulk of the code that communicates with the LumenVox API can be
found in lumenvox_api_handler.py. The majority of functions in this 
file are built to wrap over the RPCs and protocol buffer messages
used to interact with the API. Additionally, the code in
lumenvox_api_helper_common.py provides helper functions to ease the
use of common messages, such as grammars and settings. Both of these
files are used throughout the sample code. 

Upon gaining familiarity with the API, a user can examine the operations
these functions perform, and, if preferred, build more specialized 
solutions towards working with the API. 

> Before running any tests, please be sure to specify the
> address of your target LumenVox server by updating the
> following settings in `lumenvox_api_user_connection_data.py`:
>
> * `LUMENVOX_API_SERVICE_CONNECTION` address of your server
> * `ENABLE_TLS` informs server that a certification should be validated (and CERT_FILE should be modified accordingly)
> * `deployment_id` your assigned deployment ID in the server
> * `operator_id` that you wish to use (identifies API user)

Note that if you do not know your assigned `deployment_id`, you may
try using the default installed with the system, which is the value
included in the file. If this works, you can practice with this, but
at some point you should remove this temporary startup deployment ID
and use a more permanent one.

Similarly, for the `operator_id`, if you do not have some identifier
that you wish to use for tracking who is making API requests, then
you can use the sample one included for now. In production, it is
best to use your own operator ID values to understand how or what is
making API calls, which can be seen in the logs.

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

### Asyncio Use

Since callbacks can be received at any time, it is generally practical
to use a worker thread to listen for these notifications and process
them when they arrive. In this sample code, the `asyncio` library is used
to simulate threading processes; functions such as those that read from 
the API are split off into tasks or coroutines to simulate threading
functionality.

Any callback messages received by the API client code (such as these
samples), will be received and handled by tasks that read from the stream
(task_read_session_streams in lumenvox_api_handler.py, for example).
A task like this will place callback messages received from the API into
the appropriate queues define at the top of lumenvox_api_handler.py. 

Note that this configuration should allow for multiple concurrent
session operations to be performed, however these samples only demonstrate
single-session use.

For production code, it is assumed that some more structured
approach is taken for processing these callback messages. The aim
of this sample code was simplicity using Python scripting that
many people will be familiar with.

It should be noted that the use of `asyncio` libraries involves heavy use of
`await/async` syntax. For more information on `asyncio`, please refer to the
official Python documentation [here](https://docs.python.org/3.10/library/asyncio.html).

### Audio Streaming

Several sample files make use of audio streaming. To help achieve this, 
an `AudioHandler` class in audio_handler.py was created to facilitate the
audio streaming process. This process makes use of `asyncio` tasks to simulate
threading, sending audio concurrently while the main task waits for the result.
This approach was provided as a way to both send audio and track the state of the 
process in the sample code. Other approaches, however, may be used in production
environments. 

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

### Defining Audio Formats
Audio format types need to be defined in the code in order to be used in interactions. 
This can be done by referencing the `audio_formats.proto` file; the file contains an `AudioFormat` protocol buffer 
message. Inside the `AudioFormat` message, an enum is defined for types of standard audio formats, 
a `standard_audio_format` to be set to an enum value, and an optional `sample_rate_hertz` field required for certain 
types. 

If one were to define an audio format for ULAW 8kHz in the code, it would like the following:
```python
# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats
# Import optional_int32 helper definition.
from helpers.common_helper import optional_int32

# Audio format variable for ULAW 8kHz.
AUDIO_FORMAT_ULAW_8KHZ = audio_formats.AudioFormat(
    sample_rate_hertz=optional_int32(value=8000),
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_ULAW)
```

For the standard formats where the sample rate is not required to be specified (like WAV), it would look like this:
```python
# audio_formats.proto messages
import lumenvox.api.audio_formats_pb2 as audio_formats

# Audio format variable for ULAW 8kHz.
AUDIO_FORMAT_WAV = audio_formats.AudioFormat(
    standard_audio_format=audio_formats.AudioFormat.StandardAudioFormat.STANDARD_AUDIO_FORMAT_WAV)
```

The `helpers/audio_helper.py` file already provides some formats defined in a similar fashion to what was described
above. They can be imported in the sample scripts like this:
```python
# Import an AudioFormat variable defined in helpers/audio_helper.py
from helpers.audio_helper import AUDIO_FORMAT_ULAW_8KHZ
```


## Batch Mode ASR Decode

See the `asr_batch_sample.py` script for an example of how to
perform a batch-mode ASR decode using the Speech API.

An ASR interaction utilizing batch processing has its audio sent
all at once. All the audio sent before the interaction is created
is then processed. 

## Streaming ASR Decode Sample

See the `asr_streaming_sample.py` script for an example of how to
perform a streaming-mode ASR decode using the Speech API.

A streaming-mode decode uses Voice Activity Detection (VAD),
and streams chunks of audio into the system, relying on
VAD to determine start and end of speech to trigger processing.

## Transcription Streaming Sample

See the `transcription_sample.py` script for an example of
how to perform a streaming transcription using the Speech API.

Transcription is very similar to grammar-based ASR decodes,
but uses a special grammar file that is only used to trigger
transcription mode instead of grammar-based ASR decodes.

Transcription can be performed in realtime using this streaming
example, or it could be used in batch-mode operations similar to
how the Batch Mode ASR sample is used. This batch-mode is sometimes
called offline transcription mode may be slightly more efficient
and faster than realtime streaming, but requires all the audio
be sent at once, so may or may not be suitable for your use case.
Additionally, transcription with batch processing can be performed
by using a batch ASR interaction with a transcription grammar.

Partial results can be enabled using the `enable_partial_results`
field in RecognitionSettings. They are turned off by default, but
by setting `enable_partial_results.value` to `True`, partial
results can be received.

### Dialects
The `transcription_dialect_example.py` script uses the streaming transcription
code to demonstrate the differences between results based on dialect (ex. 
'en-us' vs. 'en-gb').

### Continuous Transcription
The `transcription_continuous.py` script uses the streaming transcription
code to demonstrate continuous transcription, where partial results are
returned.

## Enhanced Transcription Example

See the `enhanced_transcription_sample.py` script for an example of
how to perform an enhanced transcription using the Speech API. This is 
based on the code used for the streaming transcription example.

Enhanced transcription is performed by including addition grammars to
the transcription interaction. Semantic interpretations will also be included
within the results should the content of the audio match any of the specified
grammars.

## Normalized Transcription Example
See the `transcription_normalization_sample.py` script for an example of
how to perform an enhanced transcription using the Speech API. This is 
based on the code used for the streaming transcription example.

Normalized transcription is performed by including normalization settings
upon interaction creation. This will include additional, normalization-specific
output, on top of the transcript received basic transcription.

## Transcription Using Alias
See the `alias_lexicon_transcription_sample.py` script for an example of
how to perform a transcription interaction with aliases. This is 
based on the code used for the batch ASR example, as this requires a grammar.

The grammar for aliases must include a URI reference to a lexicon XML, the
contents of which will be visible in the results should transcription include
words as aliases under a lexeme in the lexicon file.

## Text To Speech Example

The `tts_sample.py` script demonstrated a simple TTS synthesis.
In the example, an SSML file is loaded, which contains SSML marks
to show some moderately complex functionality and the level of
details that can be returned from the synthesis result.

You can optionally request the synthesized audio be saved to disk
so that you can listen to it if desired.

## Grammar Parse Example

See the `grammar_parse_sample.py` script using the LumenVox API.

Grammar parse interactions will also accept builtin grammars or 
URL-referenced grammars if one is not locally available. 

## AMD and CPA Streaming Decodes

See the `amd_sample.py` or `cpa_sample.py` scripts for an example of how to
perform a streaming-mode Call Progress Analysis (CPA) and Tone Detection
(AMD) decodes using the LumenVox API.

A streaming-mode decode uses Voice Activity Detection (VAD),
and streams chunks of audio into the system, relying on
VAD to determine start and end of speech to trigger processing.

## Normalize Text Example

See the `normalize_text_sample.py` script for an example of how to
perform a "normalize text" interaction using the Speech API.

Normalize text interactions require a text transcript and normalization
settings to run. 

---
### Troubleshooting

**Note:** If a sample function fails to run with an error about pb2 file or anything
similar:
* Ensure that the protocol buffer files have been updated accordingly and their respective Python files are generated
    with `make_stubs.py`.
* Ensure that all the requirements have been installed in the virtual environment, and that the virtual environment 
    is activated upon running the samples.

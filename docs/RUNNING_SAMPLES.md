# Running Sample Code

This page will describe the process and other material involved in running the sample publicly available on GitHub.

The goal of this project is to demonstrate interaction with the LumenVox API via Python 3.9-3.10 and gRPC libraries. 
Due to its high-level nature, Python was chosen to more clearly demonstrate the routines that may take place when 
perform API interactions. As gRPC supports many other programming languages however, it should be emphasized that Python
was used only for sampling and that the choice of language for integration should be informed by business requirements.

It is assumed that the steps detailed in the "Virtual Environment" and "Quick Start" sections of the `README.md`
provided in the root of this project have been followed.

## Project Contents

The Python sample code scripts and LumenVox API handling code can be found at the root of this repository. Helper code
is placed within the `helpers` directory. The former will perform as the main entrypoint for LumenVox API interaction. 
Following the steps mentioned in "Virtual Environment" and "Quick Start" sections of the `README.md`, a `venv`, 
`google`, and `lumenvox` directory should also be present at the project root. 

Within the `venv` directory are the contents of the virtual environment and the libraries needed for the sample code.
`google` and `lumenvox` should contain the generated Python gRPC files that referenced in the sample code. 

Additionally, the `sample_data` directory exists to provide the audio and grammars used throughout the sample files. 

## Sample Scripts

There are a number of sample scripts provided in the root of this project; see the files with `_sample.py` at the end of
their name. These scripts showcase basic transactions with the LumenVox API, each containing a task function that will
perform an interaction in a new session.

It is worth noting that some scripts build upon or utilize code from other scripts. The 
`enhanced_transcription_sample.py` script, for example, utilizes interaction data and code from the 
`transcription_sample.py` to run a Transcription interaction with the inclusion of grammars. 

### Script Execution

All the sample scripts contain a `main` function (beginning with `if __name__ == '__main__':`) that is used to 
facilitate the initialization of the LumenVox API Client handler class found in 
[`lumenvox_api_handler.py`](../lumenvox_api_handler.py). From there, at least one function is run where a session and 
an interaction running within that session are created.

Each sample script comes with its own set of parameters, audio, and settings defined. Testing the scripts with other
audio files, text or grammars may require editing these variables, and the user is thus encouraged to read the comments
or any referenced external documentation before modifying the scripts. 

An IDE, such as PyCharm or Visual Studio code, will give the option, via interface, to the script from the main block of
code. 

Alternatively, the following command may be run to execute the script from shell or terminal, if the above option is not
available:
```shell
# To run amd_sample.py, for example:
python amd_sample.py
```
Depending on the system and its current installations, `python3` could also be `py`, `python3.9`, or `python3.10`.

Running the sample scripts will provide output involving messages sent and received to and from the LumenVox API. This 
includes the final results, though each script will manually print the final results for clarity. For best understanding
what these messages entail, it is highly recommended that the user read through not only the scripts and documentation, 
but also the protocol buffer files required to run the code in this project. The LumenVox protocol buffer files will
explicate the messages and their fields, enums, etc.; the files are heavily commented and will be helpful to
understanding the intricacies of client-side operations with the LumenVox API.

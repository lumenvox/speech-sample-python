import json
import requests as requests

from lumenvox_speech_helper import LumenVoxVBApiHelper


def vb_common():

    # Fetch an enrollment symbol and a verification symbol from the Management API.
    params = {
        "configurationName": 'vba_mvimp_en_US-2.1.13'  # NOTE: this may require some configuration
    }
    management_url = LumenVoxVBApiHelper.create_url('MGMT', 'http://{}/Management/{}/{}', 'ConfigurationSettings', 'BiometricConfiguration', params)

    vb_configuration = LumenVoxVBApiHelper.get_biometric_configuration(management_url)
    enrollment_symbol = json.loads(vb_configuration)['Enrollments'][0]['ConfigurationSymbol']
    verification_symbol = json.loads(vb_configuration)['Enrollments'][0]['Verifications'][0]['ConfigurationSymbol']

    print(
        f'Retrieved enrollment and verification symbols from {management_url}:',
        f'\tenrollment symbol: {enrollment_symbol}',
        f'\tverification symbol: {verification_symbol}',
        sep='\n'
    )

    # Next, create an identity using the API.
    params = {
        "identityTag": 'vb_enroll_example'
    }
    id_url = LumenVoxVBApiHelper.create_url('VB', "http://{}/biometric/{}/{}", "Identity", "CreateIdentity", params)

    headers = {
        'x-deployment-id': 'd80b9d9b-086f-42f0-a728-d95f39dc2229',
        'x-operator-id': '45bcb59c-b29a-449f-8349-8d6bdcbbeeba',
        'x-scopes': 'VB'
    }
    payload = {}

    response = requests.request("POST", id_url, headers=headers, data=payload, verify=False)
    identity_symbol = response.text.strip('"')

    print(f'Created Identity at {id_url}:\n\tidentity symbol: {identity_symbol}')

    # Perform the InitEnrollment call
    params = {
        "enrollmentSymbol": enrollment_symbol,
        "identitySymbol": identity_symbol,
        "enrollmentTag": 'vb_enroll_example',
        "audioFormat": 'Pcm8Khz'
    }
    vb_url = LumenVoxVBApiHelper.create_url('VB', "http://{}/biometric/{}/{}", "Active", "InitEnrollment", params)

    payload = {}

    response = requests.request("POST", vb_url, headers=headers, data=payload, verify=False)

    print(f'Initialized enrollment at {vb_url}:\n\tResponse: {response.text}')

    # save the retrieved session_id in a variable to be used to the next requests
    session_id = json.loads(response.text)["SessionId"]

    # Begin the enrollment process using provided audio files
    audio_files_for_the_enrollment = [
        'test_data/VB/8011_mvimp_en-US_V_00_E_M_7a5e_20200425120601_00_M_raw.pcm',
        'test_data/VB/8011_mvimp_en-US_V_00_E_M_7a5e_20200425120601_01_M_raw.pcm',
        'test_data/VB/8011_mvimp_en-US_V_00_E_M_7a5e_20200425120601_02_M_raw.pcm'
    ]
    for audio_file in audio_files_for_the_enrollment:
        aux_process_enrollment(audio_file, headers, session_id)

    # Finalize the enrollment
    params = {
        "sessionId": session_id
    }
    url = LumenVoxVBApiHelper.create_url('VB', "http://{}/biometric/{}/{}", "Active", "FinalizeEnrollment", params)

    response = requests.request("POST", url, headers=headers, verify=False)

    print(f'Finalized enrollment at {url}\n\tResponse: {response.text}')

    # Perform the InitVerification call
    params = {
        "verificationSymbol": verification_symbol,
        "identitySymbol": identity_symbol,
        "enrollmentTag": 'vb_enroll_example',
        "audioFormat": 'Pcm8Khz'
    }
    vb_url = LumenVoxVBApiHelper.create_url('VB', "http://{}/biometric/{}/{}", "Active", "InitVerification", params)

    payload = {}

    response = requests.request("POST", vb_url, headers=headers, data=payload, verify=False)

    print(f'Initialized verification at {vb_url}:\n\tResponse: {response.text}')

    # save the session id for the verification
    session_id = json.loads(response.text)["SessionId"]

    # Begin the verification process using provided audio files
    audio_files_for_the_verification = [
        'test_data/VB/8011_mvimp_en-US_V_00_V_M_0c9b_20200427084957_00_M_raw.pcm',
        # 'test_data/VB/8011_mvimp_en-US_V_00_V_M_0c9b_20200427084957_01_M_raw.pcm'
    ]
    for audio_file in audio_files_for_the_verification:
        aux_process_verification(audio_file, headers, session_id)

    # Finalize the verification
    params = {
        "sessionId": session_id
    }
    url = LumenVoxVBApiHelper.create_url('VB', "http://{}/biometric/{}/{}", "Active", "FinalizeVerification", params)

    response = requests.request("POST", url, headers=headers, verify=False)

    print(f'Finalized verification at {url}\n\tResponse: {response.text}')
    return "Enrollment and verification closed successfully"


def aux_process_enrollment(audio_file_to_encode, headers, session_id):
    params = {
        "sessionId": session_id
    }
    vb_url = LumenVoxVBApiHelper.create_url('VB', "http://{}/biometric/{}/{}", "Active", "ProcessEnrollment", params)

    d = dict(headers)
    d['Content-Type'] = 'application/json'
    # audio file is encoded as base64
    encoded_audio = api_helper.aux_wav_to_b64(audio_file_to_encode)
    payload = encoded_audio

    response = requests.request("POST", vb_url, headers=d, data=payload, verify=False)
    print(f'Processed enrollment at {vb_url}\n\tAudio file: {audio_file_to_encode}\n\tResult: {response.text}')
    return response


def aux_process_verification(audio_file_to_encode, headers, session_id):

    params = {
        "sessionId": session_id
    }
    vb_url = LumenVoxVBApiHelper.create_url('VB', "http://{}/biometric/{}/{}", "Active", "ProcessVerification", params)

    d = dict(headers)
    d['Content-Type'] = 'application/json'
    encoded_audio = api_helper.aux_wav_to_b64(audio_file_to_encode)
    payload = encoded_audio

    response = requests.request("POST", vb_url, headers=d, data=payload, verify=False)

    print(f'Processed verification at {vb_url}\n\tAudio file: {audio_file_to_encode}\n\tResult: {response.text}')
    return response


if __name__ == '__main__':

    # Create and initialize the API helper object that will be used to simplify the example code
    api_helper = LumenVoxVBApiHelper()
    result = vb_common()
    print(">>>> result returned:\n", json.dumps(result, indent=4, sort_keys=True, ensure_ascii=False))


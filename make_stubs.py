"""
This file imports the proto stub files in the correct locations (/lumenvox and /google from root).
"""
import os


def import_proto_files():
    # Find and import all .proto files in the protobuf folder (from git submodule).
    grpc_protos = [
        'lumenvox/api/reporting.proto',
        'lumenvox/api/lumenvox.proto',
    ]  # Add more proto files to this list as needed.

    for proto_input in grpc_protos:
        print('Generating stubs for ', proto_input)
        os.system('python -m grpc_tools.protoc -I . -I protobufs '
                  '--python_out=. '
                  '--grpc_python_out=. '
                  '--proto_path=protobufs '
                  '{}'.format(proto_input))

    lumenvox_protos = ['lumenvox/api/interaction.proto',
                       'lumenvox/api/audio_formats.proto',
                       'lumenvox/api/common.proto',
                       'lumenvox/api/global.proto',
                       'lumenvox/api/interaction.proto',
                       'lumenvox/api/optional_values.proto',
                       'lumenvox/api/results.proto',
                       'lumenvox/api/session.proto',
                       'lumenvox/api/settings.proto',
                       ]  # Add more proto files to this list as needed

    for proto_input in lumenvox_protos:
        print('Generating stubs for ', proto_input)
        os.system('python -m grpc_tools.protoc -I . -I protobufs '
                  '--python_out=. '
                  '--proto_path=protobufs '
                  '{}'.format(proto_input))

    # Generate/import google proto files
    google_api_path = './google/api'
    google_api_path_exists = os.path.exists(google_api_path)
    if not google_api_path_exists:
        os.makedirs(google_api_path)
    google_api_path = './google/protobuf'
    google_api_path_exists = os.path.exists(google_api_path)
    if not google_api_path_exists:
        os.makedirs(google_api_path)

    google_api_protos = ['google/api/annotations.proto',
                         'google/api/http.proto',
                         'google/protobuf/any.proto',
                         'google/protobuf/descriptor.proto',
                         'google/protobuf/empty.proto',
                         'google/protobuf/struct.proto',
                         'google/protobuf/timestamp.proto',
                         'google/rpc/code.proto',
                         'google/rpc/error_details.proto',
                         'google/rpc/status.proto',
                         ]
    for proto_input in google_api_protos:
        print('Generating stubs for ', proto_input)
        os.system('python -m grpc_tools.protoc -I . -I protobufs '
                  '--python_out=. '
                  '--grpc_python_out=. '
                  '--proto_path=protobufs '
                  '{}'.format(proto_input))


if __name__ == '__main__':
    import_proto_files()

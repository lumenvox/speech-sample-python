import os


# Generates the proto stub files in the correct location (/lumenvox/api/speech/v1/ from project root).
def generate_proto_files():

    os.system('python -m grpc_tools.protoc -I . -I protobufs '
              '--python_out=. '
              '--grpc_python_out=. '
              '--proto_path=protobufs '
              'lumenvox/api/speech/v1/speech.proto')


if __name__ == '__main__':
    generate_proto_files()

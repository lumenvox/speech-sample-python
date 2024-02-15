""" User Connection Data

This files serves to hold variables needed for gRPC and LumenVox API connectivity.
"""

# Define your target machine IP address here. On a default setup (using Docker for example), the port for the LumenVox
# API service would be :8280 (:443 reserved for TLS connectivity only).
LUMENVOX_API_SERVICE_CONNECTION = '127.0.0.1:8280'

# Use this to enable TLS connectivity to the service.
ENABLE_TLS = False
# If TLS connectivity is enabled, a path to a certificate file should be referenced as well.
CERT_FILE = './certs/server.crt'

# Default deployment and operator UUIDs.
# This should be changed to match the deployment_id assigned to your system, or defined separately in the sample files.
deployment_id = 'd80b9d9b-086f-42f0-a728-d95f39dc2229'
operator_id = 'a69c7ee5-ac2d-40c2-9524-8fb0f5e5e7fd'

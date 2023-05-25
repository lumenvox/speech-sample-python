FROM python:3.9-slim

ARG APP_USER=appuser

# Configure user, install run dependencies and update CA certificates
RUN adduser --disabled-password --gecos "" ${APP_USER} && \
    set -ex && \
    RUN_DEPS="libpcre3 mime-support" && \
    seq 1 8 | xargs -I{} mkdir -p /usr/share/man/man{} && \
    apt-get update && apt-get install -y --no-install-recommends $RUN_DEPS && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# define where the same code will be installed
WORKDIR /code/

# Copy all files (excluding any mentioned in .dockerignore) to /code/
COPY . .

# define where the virtual environment will be
ENV VIRTUAL_ENV=/code/venv

# Generate virtual environment, activate it, install dependencies and create proto stubs
RUN python3 -m venv $VIRTUAL_ENV && \
    . $VIRTUAL_ENV/bin/activate && \
    pip install -r requirements.txt && \
    python make_stubs.py

# Make sure the virtual environment is at the beginning of the path
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Add alias for ll and configure the virtual environment to be active when user logs in
RUN echo "alias ll='ls -la --color-auto'" >> ~/.bashrc && \
    echo "source $VIRTUAL_ENV/bin/activate" >> ~/.bashrc && \
    echo "echo You need to configure your LUMENVOX_API_SERVICE before running tests" >> ~/.bashrc && \
    echo "echo See README.md for details..." >> ~/.bashrc

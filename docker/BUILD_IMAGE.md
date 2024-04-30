# Building Docker Image

It is possible to create a Docker image that contains these test scripts
if needed. There is one published on DockerHub which can be downloaded
to your local machine using:

```shell
docker pull lumenvox/speech-sample-python 
```

Please review the attached Dockerfile to see how this is configured. If
you wish to create this using a different base image, this should be
relatively simple to do.

## Building The Image

If you wish to build your own version of this image, you can use the
following command from the project root:

```shell
docker build -f docker/Dockerfile -t lumenvox/speech-sample-python .
```

## Running the Container

You can run the container using:

```shell
docker run -ti --rm lumenvox/speech-sample-python bash 
```

Please review the various README.md and related files to understand
how to configure your tests and connectivity.

## Docker-compose

You can also use the attached docker-compose.yml file
to run the image, by typing:

```shell
docker-compose up -d
```

Then you can attach to the running container to
run tests with:

```shell
docker exec -ti speech-sample-python bash
```

To stop the running container when you are finished,
use:

```shell
docker-compose down
```

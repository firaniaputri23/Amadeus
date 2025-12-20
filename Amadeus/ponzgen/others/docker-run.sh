#!/bin/bash

set -e

IMAGE_NAME="agent-service"
CONTAINER_NAME="agent-service-container"
PORT=8080
DOCKER_PORT=8080

docker build -t $IMAGE_NAME .

if [ "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:$DOCKER_PORT \
    $IMAGE_NAME

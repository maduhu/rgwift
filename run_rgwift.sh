#!/bin/bash

trap : SIGTERM SIGINT

PYTHONPATH=app python server/swift-middleware-server            \
                                --verbose                       \
                                etc/rgwift-server.conf.sample   &
RGWIFT_PID=$!

wait ${RGWIFT_PID}

if [ $? -gt 128 ]
then
    # interrupted
    kill ${RGWIFT_PID}
fi

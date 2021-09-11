#!/bin/bash

if [ -z ${WATCHDOG_TIMER_SECONDS+x} ]
then
  WATCHDOG_TIMER_SECONDS=300
fi

echo "Sleeping for ${WATCHDOG_TIMER_SECONDS} seconds ..."
sleep ${WATCHDOG_TIMER_SECONDS}

echo "Gently killing Firefox ..."
pkill -f firefox
sleep 10
echo "Killing Firefox ..."
pkill -9 -f firefox
sleep 10
echo "Gently killing Python ..."
pkill -f python
sleep 10
echo "Killing Python ..."
pkill -9 -f python

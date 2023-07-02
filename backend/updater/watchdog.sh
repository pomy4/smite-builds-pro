#!/bin/bash

SECONDS=3600
echo "WATCHDOG: Sleeping for $SECONDS seconds ..."
sleep $SECONDS

echo "WATCHDOG: Killing Chrome ..."
pkill -f chrome
sleep 10

echo "WATCHDOG: Force killing Chrome ..."
pkill -9 -f chrome
sleep 10

echo "WATCHDOG: Killing Python ..."
pkill -f python
sleep 10

echo "WATCHDOG: Force killing Python ..."
pkill -9 -f python

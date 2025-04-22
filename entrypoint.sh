#!/bin/sh
tc qdisc add dev eth0 root handle 1: htb default 12
tc class add dev eth0 parent 1: classid 1:12 htb rate $TRANSFER_RATE
exec "$@"
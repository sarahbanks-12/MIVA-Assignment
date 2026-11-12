#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for instance in standby primary; do
 if [ -f ".runtime/$instance/postmaster.pid" ]; then
  pg_ctl -D ".runtime/$instance" stop -m fast
 fi
done
if [ -f .runtime/redis.pid ]; then
 recorded_pid=$(cat .runtime/redis.pid)
 running_pid=$(redis-cli -h 127.0.0.1 -p 56403 INFO server | tr -d '\r' | sed -n 's/^process_id://p')
 if [ "$recorded_pid" = "$running_pid" ]; then redis-cli -h 127.0.0.1 -p 56403 SHUTDOWN; fi
fi

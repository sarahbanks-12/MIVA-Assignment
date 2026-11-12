#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export LC_ALL="${LC_ALL:-C}"
[ -d .runtime/primary ] && [ -d .runtime/standby ] || { echo 'No complete lab found. Use run_lab.sh in a fresh checkout.' >&2; exit 1; }
for item in 'primary 55503' 'standby 55504'; do
 read -r instance port <<< "$item"
 if ! pg_ctl -D ".runtime/$instance" status >/dev/null 2>&1; then
  pg_ctl -D ".runtime/$instance" -l ".runtime/$instance.log" -o "-p $port -h 127.0.0.1 -k /tmp" start
 fi
done
if [ ! -f .runtime/redis.pid ]; then
 redis-server portfolio-4-nosql/redis.conf --dir "$PWD/.runtime" --daemonize yes --pidfile "$PWD/.runtime/redis.pid" --logfile "$PWD/.runtime/redis.log"
fi

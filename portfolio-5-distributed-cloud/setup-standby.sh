#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export LC_ALL="${LC_ALL:-C}"
# Dedicated local lab only; refuses to overwrite an existing standby.
if [ -e .runtime/standby ]; then
  echo 'Standby directory already exists; inspect it before rebuilding.' >&2
  exit 1
fi
pg_basebackup -h 127.0.0.1 -p 55503 -U portfolio -D .runtime/standby -R -X stream -c fast
pg_ctl -D .runtime/standby -l .runtime/standby.log -o '-p 55504 -h 127.0.0.1 -k /tmp' start

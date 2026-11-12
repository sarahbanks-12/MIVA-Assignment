#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# PostgreSQL refuses to start on macOS when no valid locale is set in the environment.
export LC_ALL="${LC_ALL:-C}"
for tool in initdb pg_ctl createdb psql pg_basebackup redis-server redis-cli; do
 command -v "$tool" >/dev/null || { echo "Missing dependency: $tool" >&2; exit 1; }
done
[ -x .venv/bin/python ] || { echo 'Create .venv and install requirements first.' >&2; exit 1; }
[ ! -e .runtime/primary ] || { echo 'Existing lab detected. Use a fresh checkout to reproduce without deleting data.' >&2; exit 1; }
.venv/bin/python - <<'PY'
import socket
for port in (55503,55504,56403):
 with socket.socket() as s:
  if s.connect_ex(('127.0.0.1',port))==0:raise SystemExit(f'Port {port} is in use; stop the other lab before running this one.')
PY
mkdir -p .runtime portfolio-1-database-design/evidence portfolio-2-query-optimisation/evidence
initdb -D .runtime/primary -A trust -U portfolio --no-locale -E UTF8 > .runtime/initdb.log
pg_ctl -D .runtime/primary -l .runtime/postgres.log -o '-p 55503 -h 127.0.0.1 -k /tmp' start
createdb -h 127.0.0.1 -p 55503 -U portfolio cedar
export CEDAR_DSN='host=127.0.0.1 port=55503 user=portfolio dbname=cedar'
export CEDAR_REDIS_URL='redis://127.0.0.1:56403/0'
export CEDAR_STANDBY_DSN='host=127.0.0.1 port=55504 user=portfolio dbname=cedar'
psql -X "$CEDAR_DSN" -v ON_ERROR_STOP=1 -f portfolio-1-database-design/schema.sql > portfolio-1-database-design/evidence/schema-build.txt
psql -X "$CEDAR_DSN" -v ON_ERROR_STOP=1 -f portfolio-1-database-design/seed.sql > portfolio-1-database-design/evidence/seed.txt
.venv/bin/python portfolio-2-query-optimisation/scripts/benchmark.py > portfolio-2-query-optimisation/benchmark-console.txt
.venv/bin/python portfolio-3-transactions-concurrency/scripts/test_transactions.py > portfolio-3-transactions-concurrency/test-console.txt
redis-server portfolio-4-nosql/redis.conf --dir "$PWD/.runtime" --daemonize yes --pidfile "$PWD/.runtime/redis.pid" --logfile "$PWD/.runtime/redis.log"
.venv/bin/python portfolio-4-nosql/scripts/test_nosql.py > portfolio-4-nosql/test-console.txt
bash portfolio-5-distributed-cloud/setup-standby.sh
.venv/bin/python portfolio-5-distributed-cloud/scripts/test_replication.py > portfolio-5-distributed-cloud/test-console.txt
psql -X "$CEDAR_DSN" -v ON_ERROR_STOP=1 -f portfolio-2-query-optimisation/queries.sql > portfolio-2-query-optimisation/evidence/all-query-results.txt
.venv/bin/python portfolio-2-query-optimisation/scripts/explain_queries.py > portfolio-2-query-optimisation/evidence/all-query-plans.txt
# The manual examples commit data, so they run on a throwaway copy of the finished lab database.
createdb -h 127.0.0.1 -p 55503 -U portfolio -T cedar cedar_examples
psql -X 'host=127.0.0.1 port=55503 user=portfolio dbname=cedar_examples' -v ON_ERROR_STOP=1 -f portfolio-3-transactions-concurrency/examples.sql > portfolio-3-transactions-concurrency/evidence/manual-sql-output.txt
printf 'All lab checks passed. Evidence has been regenerated. Services remain available for inspection.\n'

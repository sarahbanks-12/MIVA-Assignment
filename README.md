# MIT 8103 Advanced Database Systems Portfolio

## Case study: Cedar Bank

Cedar Bank is a simulated Nigerian fintech offering NGN wallets. The portfolio examines customer accounts, deposits, withdrawals, transfers, reversals and balance reconciliation. Database users include customers, support staff, operations staff and auditors. All customer data are synthetic.

## Repository structure

```text
MIVA-Assignment/
├── portfolio-1-database-design/
├── portfolio-2-query-optimisation/
├── portfolio-3-transactions-concurrency/
├── portfolio-4-nosql/
├── portfolio-5-distributed-cloud/
└── README.md
```

## Current status

This repository is being populated from an existing local portfolio. The initial commit establishes its structure. Implementation files and evidence will be added as the corresponding activities are reviewed; subsequent commits will record the review, corrections and improvements actually made.

The existing implementation uses PostgreSQL for the wallet ledger, Redis for auxiliary NoSQL examples, and a local PostgreSQL standby for replication. The 11 November 2026 review adds the database design and query-optimisation implementation with fresh local evidence. Portfolios 3–5 remain placeholders pending their scheduled review on 12 November.

## Portfolio activities

1. **Database design and modelling:** case study, ER model, relational schema, constraints and normalisation.
2. **Query processing and optimisation:** SQL queries, results, execution plans, indexing and measured performance.
3. **Transactions and concurrency:** commit, rollback, isolation, concurrent transfers and reconciliation.
4. **NoSQL and advanced data models:** Redis model, implementation, evidence and suitability.
5. **Distributed and cloud databases:** replication evidence and discussion of consistency, availability and sharding.

The final LMS documentation will summarise all five activities, include the repository link, a technical reflection, references and the required AI-use declaration.

## Run the currently published activities

Requirements: PostgreSQL 16 command-line tools on PATH, Python 3.9 or later, and an unused local port 55493. Use a new, disposable local cluster: the SQL creates a schema and a cluster-level application role. Do not run it in a shared or production database. The loopback-only lab uses trust authentication and synthetic data.

Run from the repository root. On Homebrew, first add `/opt/homebrew/opt/postgresql@16/bin` to PATH if necessary.

```sh
set -e
python3 -m venv .venv
.venv/bin/pip install -r portfolio-1-database-design/requirements.txt
mkdir -p .runtime
initdb -D .runtime/review-pg -U portfolio --auth=trust
pg_ctl -D .runtime/review-pg -l .runtime/postgres.log -o '-p 55493 -h 127.0.0.1 -k /tmp' start
createdb -h 127.0.0.1 -p 55493 -U portfolio cedar
export CEDAR_DSN='host=127.0.0.1 port=55493 user=portfolio dbname=cedar'
psql "$CEDAR_DSN" -v ON_ERROR_STOP=1 -f portfolio-1-database-design/schema.sql -f portfolio-1-database-design/seed.sql > portfolio-1-database-design/evidence/build.txt
.venv/bin/python portfolio-1-database-design/scripts/check_design.py
.venv/bin/python portfolio-2-query-optimisation/scripts/benchmark.py
.venv/bin/python portfolio-2-query-optimisation/scripts/explain_queries.py > portfolio-2-query-optimisation/evidence/all-query-plans.txt
psql "$CEDAR_DSN" -v ON_ERROR_STOP=1 -f portfolio-2-query-optimisation/queries.sql > portfolio-2-query-optimisation/evidence/all-query-results.txt
pg_ctl -D .runtime/review-pg stop
```

The cluster directory must not already exist for the initial setup. To reuse an existing lab, start its server and rerun only the checks and queries; do not reload the schema or seed. If a command fails, stop the server with the final command after inspecting the error. A new benchmark overwrites its evidence; update the written measurements when publishing new results.

## Review evidence and AI use

The 11 November review passed ten design checks on 5,000 customers, 5,001 accounts, 200,000 transfers and 400,000 postings. The benchmark checked identical query results and all fourteen measured plan shapes before and after indexing. All five supplied queries have fresh results and execution plans. Timings are local measurements, not production performance guarantees.

OpenAI Codex assisted with the original implementation and performed this review, execution and documentation update. Anthropic Claude (Claude Code) previously audited the existing local package. These are agent-performed checks; student-performed verification has not been confirmed. Source acknowledgements are retained in [References and provenance](portfolio-1-database-design/REFERENCES.md). The local implementation predates these GitHub review commits.

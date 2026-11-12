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

The 11 November review published database design and query optimisation. The 12 November review added transactions, Redis and physical PostgreSQL replication, and reran the integrated lab. All five activities are now included. These commits record review and publication of the pre-existing local implementation.

## Portfolio activities

1. **Database design and modelling:** case study, ER model, relational schema, constraints and normalisation.
2. **Query processing and optimisation:** SQL queries, results, execution plans, indexing and measured performance.
3. **Transactions and concurrency:** commit, rollback, isolation, concurrent transfers and reconciliation.
4. **NoSQL and advanced data models:** Redis model, implementation, evidence and suitability.
5. **Distributed and cloud databases:** replication evidence and discussion of consistency, availability and sharding.

The final LMS documentation will summarise all five activities, include the repository link, a technical reflection, references and the required AI-use declaration.

## Reproduce the complete lab

Requirements: PostgreSQL 16 command-line tools, Redis server/CLI, and Python 3.9 or later. Add PostgreSQL and Redis to PATH; on this Mac PostgreSQL is in `/opt/homebrew/opt/postgresql@16/bin` and Redis in `/opt/homebrew/bin`.

Run from the repository root in a fresh checkout:

```sh
python3 -m venv .venv
.venv/bin/pip install -r portfolio-1-database-design/requirements.txt
bash portfolio-1-database-design/scripts/run_lab.sh
.venv/bin/python portfolio-1-database-design/scripts/verify_portfolio.py
bash portfolio-1-database-design/scripts/stop_lab.sh
```

The script refuses to overwrite an existing primary or use occupied ports. It creates disposable, loopback-only PostgreSQL services on 55503/55504 and Redis on 56403, with synthetic data under ignored `.runtime/`. Trust authentication is for this local exercise only. Do not run the setup in a shared or production cluster. Services remain running for inspection until stopped; if any check fails, inspect its output and run the stop command. Use `start_lab.sh` to reopen an existing complete lab. Transaction fixture loading requires a fresh database, so do not rerun `run_lab.sh` on the same data directory.

The earlier ten-check design test expects a seed-only database. To reproduce it, insert its invocation immediately after the seed step in `run_lab.sh`, before transactions add fixtures. Its retained `design-checks.json` is dated 11 November. The full-lab evidence and final verification are dated 12 November. Generated measurements replace prior captures; the written analysis must be updated when publishing a rerun.

## Results and documentation

The integrated review passed 45 transaction checks, five Redis behaviour checks and the replication assertions. Final totals are 5,004 customers, 5,005 accounts, 200,333 transfers and 400,666 ledger entries, with no balance discrepancies or unbalanced transfers. All five supplied queries have recorded results and execution plans. The benchmark compares seven runs per configuration and checks result equality. These are local tests, not production guarantees or a cloud deployment.

See the [portfolio summary](portfolio-1-database-design/submission/summary.md), [verification evidence](portfolio-1-database-design/evidence/final-verification.json) and [references](portfolio-1-database-design/REFERENCES.md). The unpersonalised summary is included; the personalised LMS PDF remains local and was not rebuilt during this review. LMS submission has not been performed. The repository remains public at the user's request; the brief's private-repository requirement and assessor access still need to be resolved before submission.

## AI use

OpenAI Codex assisted with the original implementation and performed these reviews, test runs and documentation updates. Anthropic Claude (Claude Code) previously audited the local package. These are agent-performed checks; student-performed verification has not been confirmed. Required source acknowledgements are retained. The local implementation predates these GitHub review commits, and two days of review do not establish semester-long development.

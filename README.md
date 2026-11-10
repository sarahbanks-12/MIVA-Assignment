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

The existing implementation uses PostgreSQL for the wallet ledger, Redis for auxiliary NoSQL examples, and a local PostgreSQL standby for replication. These implementation files are not included in this initial repository setup.

## Portfolio activities

1. **Database design and modelling:** case study, ER model, relational schema, constraints and normalisation.
2. **Query processing and optimisation:** SQL queries, results, execution plans, indexing and measured performance.
3. **Transactions and concurrency:** commit, rollback, isolation, concurrent transfers and reconciliation.
4. **NoSQL and advanced data models:** Redis model, implementation, evidence and suitability.
5. **Distributed and cloud databases:** replication evidence and discussion of consistency, availability and sharding.

The final LMS documentation will summarise all five activities, include the repository link, a technical reflection, references and the required AI-use declaration.

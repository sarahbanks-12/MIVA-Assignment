# Portfolio 3 - Transactions and concurrency

## Why a transfer is one transaction

Moving NGN 250.00 from one wallet to another needs more than two unrelated UPDATE statements. The source debit, destination credit, transfer record and two postings must succeed together. `post_transfer` runs inside the caller's transaction; it does not commit on the caller's behalf. `examples.sql` gives explicit BEGIN, COMMIT and ROLLBACK examples. `../portfolio-3-transactions-concurrency/scripts/test_transactions.py` exercises independent PostgreSQL connections and records assertions in `evidence/tests.json`.

Atomicity is demonstrated by the rollback test: neither the balance changes nor the new transfer survives. Consistency is checked through positive amounts, account-type rules, nonnegative customer balances, foreign keys and balanced postings. Isolation is tested with concurrent sessions. Committed records remain visible to a fresh connection; PostgreSQL's WAL provides the durability mechanism, although this exercise does not claim to have run a power-loss test [6].

## The unsafe schedule and its consequence

A separate `isolation_demo` table starts at 100. A reads 100; B also reads 100. A subtracts 30 and writes 70, then commits. B subtracts 40 from its stale copy and writes 60, then commits. The final value is 60, although applying both deductions should give 30. The test deliberately reproduces this lost update and then drops the demonstration table. No wallet balance is corrupted to create the example.

## Protecting the actual balance

The transaction function locks both accounts using `SELECT ... FOR UPDATE`, always in ascending account-ID order. The available balance is read after those locks are obtained. In the controlled-spend test, A deducts 70,000 kobo from an account holding 100,000 and keeps the transaction open. B tries another 70,000 deduction. An observer queries `pg_blocking_pids` and confirms that B is waiting. When A commits, B sees the remaining 30,000 and fails. Only A's transfer is recorded.

Ordering account locks reduces deadlock risk for opposite-direction transfers. It does not justify assuming that every larger application transaction is deadlock-free: callers should keep transactions short, take other locks consistently and retry the whole transaction when PostgreSQL reports a deadlock or serialization failure.

The unique request key prevents the same request from being recorded twice. A transaction-scoped advisory lock serializes matching keys before checking for an existing transfer. Retrying exactly the same parameters returns the original ID. Reusing a key with different parameters raises an error. A second concurrency test verifies this waiting-and-reuse behaviour. Idempotency controls retries; it is not a substitute for balance locks.

## Isolation comparison

| Level | First read | Another connection commits 200 | Second read |
|---|---:|---|---:|
| READ COMMITTED | 100 | Yes | 200 |
| REPEATABLE READ | 100 | Yes | 100 |

READ COMMITTED can see a new committed value in a later statement. REPEATABLE READ retains the transaction's earlier snapshot. That stronger snapshot does not remove the need to handle conflicts and retries. Running the lost-update schedule above under REPEATABLE READ shows this directly: the second writer fails with SQLSTATE 40001, the first writer's value of 70 stands and the application must retry. The wallet implementation uses READ COMMITTED with explicit row locks [1].

## Reversal and auditability

The test transfers 25,000 kobo, then creates an equal and opposite reversal. Both the original and compensating entries remain visible. A repeated reversal is rejected; `reversal_of` also has a unique constraint to prevent competing reversal requests from both committing. The function rejects reversals with the wrong accounts, amount or original type. In a race between two reversal requests with different keys, the account locks make the second wait; it then finds the first reversal and is refused. A request that failed before commit has nothing to reverse.

The application role holds no INSERT, UPDATE, DELETE or TRUNCATE privilege on any bank table, and direct statements fail with SQLSTATE 42501. The deferred posting check rejects an owner-inserted transfer whose postings are missing, one-sided or of the wrong amount at commit. It checks transfer insertion, not every possible owner modification, so privileged administrative access must be controlled separately.

## Results and limits

The JSON log and console output report 45 checked outcomes. Rejection tests require the expected SQLSTATE and, for business-rule failures, the expected error message. The rollback test first reads the changed balances inside the transaction, so it cannot pass merely because the function did nothing. The withdrawal result is read back from the database rather than printed as an assumed value. Further checks cover a later statement failure rolling back an earlier transfer, zero/null amounts, an invalid operation, reversal of a reversal, reversals with the wrong amount or accounts, competing reversals, foreign keys, unique account numbers, the unique reversal reference, nonnegative balances and the single-clearing-account rule.

An opposite-direction test runs 320 transfers across eight sessions on the same two wallets and requires zero deadlocks. It supports the lock-ordering argument for this workload; no finite test can prove that deadlock is impossible. Final assertions require zero reconciliation differences, zero net ledger sum and zero negative customer balances. A separate check adds one kobo to a balance inside a rolled-back transaction and confirms that the reconciliation query reports that account, so an empty result is meaningful. Failed attempts are captured in the test evidence, not in committed financial history. A production service should separately record operational failures without undoing them in the failed financial transaction.

The lab does not implement customer authentication, per-customer SELECT policies, external settlement, chargeback workflows or high-volume contention testing. The application's broad read role is a coursework convenience, not a production privacy design.

[1] PostgreSQL Global Development Group. *Transaction Isolation*, PostgreSQL 16 documentation. https://www.postgresql.org/docs/16/transaction-iso.html

[6] PostgreSQL Global Development Group. *Write-Ahead Logging (WAL)*, PostgreSQL 16 documentation. https://www.postgresql.org/docs/16/wal-intro.html

## Reproduce this activity

The evidence above was regenerated on 12 November 2026. Follow the complete-lab commands in the root README; they create isolated services and run the activities in dependency order. Do not rerun the transaction fixture loader on an already populated lab.

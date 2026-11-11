# Portfolio 1 - Database design and modelling

## Case study: Cedar Bank

Cedar Bank is a simulated Nigerian fintech offering NGN wallets to retail customers. It is a teaching scenario, not a claim about an existing bank. Customers check balances and move money; support staff investigate complaints; operations staff reconcile postings; auditors inspect the transaction history. The database stores customer identifiers and contact details, accounts, committed money movements and the two ledger postings associated with each movement.

The core operations are deposits, withdrawals, internal transfers, compensating reversals, recent-transaction searches and balance reconciliation. All supplied names and addresses are generated fixtures. No BVN, card number, password or real bank account is used.

## Scope and business rules

A customer may hold several accounts; a customer account has one owner; the system clearing account has none. Joint accounts, interest, overdrafts, lending, fees, foreign exchange and external payment settlement are outside this exercise. Amounts are positive whole kobo stored as BIGINT. A customer balance cannot become negative. A single system clearing account represents the other side of deposits and withdrawals and may be negative; it is not a customer's wallet.

A transfer has distinct source and destination accounts. A deposit runs from clearing to a customer, a withdrawal from a customer to clearing, and an internal transfer between customers. A committed transfer has exactly two ledger entries, with opposite amounts. This is a balanced wallet subledger, not a full bank general ledger. The clearing balance is a control total, not proof of external settlement.

Only successful operations enter `transfers`. An operation that fails before commit leaves no transfer or ledger entry. Reversing a committed operation creates a new compensating transfer with a unique reference to the original. It does not delete history. A failed operation that has already rolled back must not be reversed, because no funds moved. If a recipient has spent the money, this simplified reversal is refused; a real bank would need an exception-resolution process.

## Model and relational schema

See `er-diagram.png` for the rendered diagram and `er-diagram.mmd` for its editable source.

| Relation | Primary key | Other keys and relationships |
|---|---|---|
| customers | customer_id | email UNIQUE; full_name required |
| accounts | account_id | account_number UNIQUE; customer_id -> customers, nullable only for clearing |
| transfers | transfer_id | request_key UNIQUE; source_account and destination_account -> accounts; reversal_of -> transfers, UNIQUE when present |
| ledger_entries | (transfer_id, account_id) | transfer_id -> transfers; account_id -> accounts |

`schema.sql` is the authoritative executable schema. It contains checks, foreign keys, a deferred posting constraint and the transaction function. The function checks operation type, available funds and reversal identity, then changes both balances and inserts both postings within the caller's transaction. `cedar_app` has read access and permission to call that function, but cannot directly alter balances, transfers or postings. The schema owner remains privileged: administrative tampering is outside that access-control boundary.

## Normalisation, from a flat record to 3NF

A starting spreadsheet might contain `(transfer_id, customer_name, customer_email, source_number, destination_number, amount, posting_1_account, posting_1_delta, posting_2_account, posting_2_delta)`. That repeats customer information and fixes the number of posting columns. A customer changing email would require edits to many rows; deleting their last transaction could remove the only contact record.

**First normal form:** separate repeating postings into rows and give each field one value. Each ledger row identifies one account and one signed amount.

**Second normal form:** the ledger key is `(transfer_id, account_id)`. The signed posting depends on both parts; transaction-level details such as request key and time belong in `transfers`, not in each posting row. Customer and account details are separated into their own relations.

**Third normal form:** the principal dependencies are `customer_id -> full_name, email, created_at`; `account_id -> customer_id, account_number, account_kind, currency, balance_kobo`; `transfer_id -> request_key, source_account, destination_account, amount_kobo, kind, reversal_of, created_at`; and `(transfer_id, account_id) -> delta_kobo`. Email and account number are alternate candidate keys in their respective tables. No customer name or email is copied into accounts or transfers, so the dependency through customer_id is removed.

Two attributes need a qualification. `account_kind` always agrees with whether `customer_id` is NULL, so strictly `customer_id -> account_kind` holds even though `customer_id` is not a key of `accounts`. It is kept as an explicit discriminator because it makes the deposit, withdrawal and transfer rules readable, and a CHECK constraint prevents the two columns from disagreeing. `currency` holds the single permitted value NGN in this scope and would need its own treatment if other currencies were added. Apart from these two documented choices, every non-key attribute depends on the whole key and only on the key.

There are two intentional cross-table redundancies. `accounts.balance_kobo` caches the sum of ledger postings for fast balance checks. The transfer amount also determines the two posting amounts. These do not create a non-key determinant inside those relations, but they do create consistency obligations across tables. The function maintains the cache, the deferred constraint verifies the two postings on each inserted transfer, and the reconciliation query checks every account. The ledger is the reconstruction source. Application users cannot edit it directly.

## Dataset and verification

`seed.sql` builds 5,000 customers, 5,001 accounts including clearing, 200,000 deposits and 400,000 postings. IDs, transfer times and amounts are deterministic; `customers.created_at` records the actual load time. Each customer starts with 40 deposits. This review uses the seed-only dataset. Transaction and replication fixtures are reserved for the next activity review.

The seed loads customers and accounts first, then bulk-loads the transfers, postings and corresponding balances in one transaction under the schema owner. It updates balances from the ledger and runs ANALYZE. This privileged loading path is separate from the application's function-only write path. Build output is in `evidence/build.txt`. On 11 November 2026, `scripts/check_design.py` passed ten design checks, including exact row counts, key and balance constraints, deferred posting validation, application write permissions and reconciliation. The reconciliation check also detected an injected one-kobo mismatch, which was rolled back. See `evidence/design-checks.json`. Run instructions are in the root README. These checks do not replace the forthcoming transaction and concurrency tests.

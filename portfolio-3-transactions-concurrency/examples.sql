-- Run on a disposable copy of the seeded database; run_lab.sh creates cedar_examples for this.
SET search_path=bank,public;
BEGIN;
SET LOCAL ROLE cedar_app;
SELECT post_transfer('manual-transfer',2,3,10000);
COMMIT;
BEGIN;
SET LOCAL ROLE cedar_app;
SELECT post_transfer('manual-rollback',2,3,20000);
ROLLBACK;
-- Expect zero rows: a rolled-back attempt is not committed financial history.
SELECT * FROM transfers WHERE request_key='manual-rollback';
-- Reverse a committed operation using a new compensating entry.
BEGIN;
SET LOCAL ROLE cedar_app;
SELECT post_transfer('manual-reversal',3,2,10000,'reversal',
 (SELECT transfer_id FROM transfers WHERE request_key='manual-transfer'));
COMMIT;
-- Expect the original and its reversal, both preserved, and no rolled-back row.
SELECT request_key,kind,amount_kobo,reversal_of IS NOT NULL AS is_reversal
 FROM transfers WHERE request_key LIKE 'manual-%' ORDER BY transfer_id;
-- Expect zero rows: the balance cache still agrees with the ledger.
SELECT a.account_id,a.balance_kobo,coalesce(sum(l.delta_kobo),0) AS ledger_balance
 FROM accounts a LEFT JOIN ledger_entries l USING(account_id)
 GROUP BY a.account_id HAVING a.balance_kobo<>coalesce(sum(l.delta_kobo),0);

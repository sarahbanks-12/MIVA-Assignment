SET search_path=bank,public;
-- Q1: most recent incoming transactions: fixed account and stable tie-break.
SELECT transfer_id,amount_kobo,kind,created_at FROM transfers
 WHERE destination_account=42 ORDER BY created_at DESC,transfer_id DESC LIMIT 20;
-- Q2: account totals per customer, including customers without accounts.
SELECT c.customer_id,c.full_name,coalesce(sum(a.balance_kobo),0) AS total_kobo
 FROM customers c LEFT JOIN accounts a USING(customer_id)
 GROUP BY c.customer_id,c.full_name ORDER BY total_kobo DESC,c.customer_id LIMIT 10;
-- Q3: daily deposit volume (fixed UTC grouping avoids session timezone drift).
SELECT (created_at AT TIME ZONE 'UTC')::date AS day,count(*) AS deposits,sum(amount_kobo) AS amount_kobo
 FROM transfers WHERE kind='deposit' GROUP BY 1 ORDER BY 1;
-- Q4: reconciliation, expected to return zero discrepancies.
SELECT a.account_id,a.balance_kobo,coalesce(sum(l.delta_kobo),0) AS ledger_balance
 FROM accounts a LEFT JOIN ledger_entries l USING(account_id)
 GROUP BY a.account_id HAVING a.balance_kobo<>coalesce(sum(l.delta_kobo),0);
-- Q5: audit trail linking a compensating transfer to the original.
SELECT t.transfer_id,t.kind,t.amount_kobo,r.transfer_id AS reversed_by
 FROM transfers t LEFT JOIN transfers r ON r.reversal_of=t.transfer_id
 WHERE t.request_key LIKE 'test-%' ORDER BY t.transfer_id;

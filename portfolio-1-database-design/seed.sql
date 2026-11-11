SET search_path=bank,public;
-- All records are synthetic. Repeatable generation, no personal banking data.
INSERT INTO customers(customer_id,full_name,email)
 SELECT g,'Demo Customer '||g,'customer'||g||'@example.test' FROM generate_series(1,5000) g;
INSERT INTO accounts(account_id,customer_id,account_number,account_kind)
 VALUES(1,NULL,'0000000001','clearing');
INSERT INTO accounts(account_id,customer_id,account_number,account_kind)
 SELECT g+1,g,lpad((g+1)::text,10,'0'),'customer' FROM generate_series(1,5000) g;
BEGIN;
INSERT INTO transfers(transfer_id,request_key,source_account,destination_account,amount_kobo,kind,created_at)
 SELECT g,'seed-'||g,1,2+((g-1)%5000),10000+(g%100)*100,'deposit',
 '2026-09-01 00:00:00+00'::timestamptz + g*interval '20 seconds'
 FROM generate_series(1,200000) g;
INSERT INTO ledger_entries SELECT transfer_id,source_account,-amount_kobo FROM transfers
 UNION ALL SELECT transfer_id,destination_account,amount_kobo FROM transfers;
UPDATE accounts a SET balance_kobo=s.total FROM
 (SELECT account_id,sum(delta_kobo)::bigint total FROM ledger_entries GROUP BY account_id) s
 WHERE a.account_id=s.account_id;
COMMIT;
SELECT setval(pg_get_serial_sequence('bank.customers','customer_id'),5000);
SELECT setval(pg_get_serial_sequence('bank.accounts','account_id'),5001);
SELECT setval(pg_get_serial_sequence('bank.transfers','transfer_id'),200000);
ANALYZE;

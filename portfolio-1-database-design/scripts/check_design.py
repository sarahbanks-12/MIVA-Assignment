"""Validate design constraints on the seed-only database; all probes roll back."""
import json
from datetime import datetime, timezone
from common import connect, save

c = connect()
checks = []

def expect_error(name, sql, state):
    try:
        c.execute(sql)
        c.commit()  # Exercise deferred posting checks, too.
    except Exception as exc:
        c.rollback()
        assert getattr(exc, 'sqlstate', None) == state, (name, str(exc))
        checks.append(name)
    else:
        raise AssertionError(name + ': invalid data accepted')

counts = dict(c.execute("SELECT 'customers', count(*) FROM customers UNION ALL SELECT 'accounts', count(*) FROM accounts UNION ALL SELECT 'transfers', count(*) FROM transfers UNION ALL SELECT 'ledger_entries', count(*) FROM ledger_entries").fetchall())
assert counts == dict(customers=5000, accounts=5001, transfers=200000, ledger_entries=400000), counts
checks.append('deterministic seed row counts')
c.commit()
expect_error('duplicate email rejected', "INSERT INTO customers(full_name,email) VALUES ('Probe','customer1@example.test')", '23505')
expect_error('unknown customer rejected', "INSERT INTO accounts(customer_id,account_number,account_kind) VALUES (999999,'9999999999','customer')", '23503')
expect_error('negative customer balance rejected', "UPDATE accounts SET balance_kobo=-1 WHERE account_id=42", '23514')
expect_error('second clearing account rejected', "INSERT INTO accounts(account_number,account_kind) VALUES ('9999999999','clearing')", '23505')
expect_error('zero transfer amount rejected', "INSERT INTO transfers(request_key,source_account,destination_account,amount_kobo,kind) VALUES ('design-zero',1,42,0,'deposit')", '23514')
expect_error('missing postings rejected at commit', "INSERT INTO transfers(request_key,source_account,destination_account,amount_kobo,kind) VALUES ('design-incomplete',1,42,1,'deposit')", 'P0001')
c.execute('SET LOCAL ROLE cedar_app')
expect_error('application cannot edit balances directly', 'UPDATE accounts SET balance_kobo=balance_kobo+1 WHERE account_id=42', '42501')
rows = c.execute('SELECT a.account_id FROM accounts a LEFT JOIN ledger_entries l USING(account_id) GROUP BY a.account_id HAVING a.balance_kobo<>coalesce(sum(l.delta_kobo),0)').fetchall()
assert not rows
assert c.execute('SELECT sum(delta_kobo) FROM ledger_entries').fetchone()[0] == 0
checks.append('every account reconciles and ledger nets to zero')
c.execute('UPDATE accounts SET balance_kobo=balance_kobo+1 WHERE account_id=42')
rows = c.execute('SELECT a.account_id FROM accounts a LEFT JOIN ledger_entries l USING(account_id) GROUP BY a.account_id HAVING a.balance_kobo<>coalesce(sum(l.delta_kobo),0)').fetchall()
assert rows == [(42,)], rows
c.rollback()
checks.append('reconciliation detects injected one-kobo discrepancy; rolled back')
result = {'reviewed_at_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'seed-only schema and constraints; probes rolled back', 'counts': counts, 'passed': len(checks), 'checks': checks}
save('portfolio-1-database-design/evidence/design-checks.json', result)
print(json.dumps(result, indent=2))
c.close()

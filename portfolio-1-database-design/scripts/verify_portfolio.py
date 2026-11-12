"""Verify captured lab evidence against the running database after run_lab.sh."""
import datetime,hashlib,json,statistics
from common import ROOT,connect,save,plan_nodes,check_plan_shape

EXPECTED_TRANSACTION_CHECKS=45
def read(path):return json.loads((ROOT/path).read_text())
b=read('portfolio-2-query-optimisation/evidence/benchmark.json')
t=read('portfolio-3-transactions-concurrency/evidence/tests.json')
n=read('portfolio-4-nosql/evidence/results.json')
r=read('portfolio-5-distributed-cloud/evidence/replication.json')
# record() only runs after a test's assertions pass, so the count and unique names are what matter.
assert len(t)==EXPECTED_TRANSACTION_CHECKS and len({x['test'] for x in t})==EXPECTED_TRANSACTION_CHECKS
assert all(n['checks'].values()) and 0<n['fixed_window_after_ms']<=n['fixed_window_before_ms']<4500
assert n['unique_counter_results']==list(range(1,21))
for phase in ('before','after'):
 plans=read(f'portfolio-2-query-optimisation/evidence/{phase}-plans.json')
 for plan in plans:check_plan_shape(phase,plan)
 times=[p['Execution Time'] for p in plans]
 assert len(times)==7 and times==b[phase]['execution_ms']
 assert statistics.median(times)==b[phase]['median_ms']
 assert plans[-1]['Plan']['Shared Hit Blocks']==b[phase]['root_shared_hit_blocks']
 assert plans[-1]['Plan']['Shared Read Blocks']==b[phase]['root_shared_read_blocks']
assert b['after']['median_ms']<b['before']['median_ms'] and b['after']['root_shared_hit_blocks']<b['before']['root_shared_hit_blocks']
assert b['rows']==200000 and b['result_equivalence']
assert len(read('portfolio-2-query-optimisation/evidence/q1-results.json'))==20
# Every submitted query needs a plan, and the broad queries must really be broad, as the analysis says.
all_plans={p['query']:p['plan'] for p in read('portfolio-2-query-optimisation/evidence/all-query-plans.json')}
assert list(all_plans)==['Q1','Q2','Q3','Q4','Q5']
def seq_scans(query):return {x['Relation Name'] for x in plan_nodes(all_plans[query]['Plan']) if x['Node Type']=='Seq Scan'}
assert {'customers','accounts'}<=seq_scans('Q2') and 'transfers' in seq_scans('Q3') and {'accounts','ledger_entries'}<=seq_scans('Q4')
assert not seq_scans('Q1')
manual=(ROOT/'portfolio-3-transactions-concurrency/evidence/manual-sql-output.txt').read_text()
assert 'manual-transfer' in manual and 'manual-reversal' in manual and 'manual-rollback ' not in manual
assert manual.count('(0 rows)')==2 and '(2 rows)' in manual
assert r['standby_write_rejected']['sqlstate']=='25006'
assert r['standby_marker_postings']==[[1,-12345],[42,12345]]
assert any(x[0]=='streaming' and x[1]=='async' for x in r['primary_replication_rows'])
with connect(True) as c:
 counts={table:c.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('customers','accounts','transfers','ledger_entries')}
 differences=c.execute('SELECT count(*) FROM (SELECT a.account_id FROM accounts a LEFT JOIN ledger_entries l USING(account_id) GROUP BY a.account_id HAVING a.balance_kobo<>coalesce(sum(l.delta_kobo),0)) x').fetchone()[0]
 unbalanced=c.execute('SELECT count(*) FROM (SELECT transfer_id FROM ledger_entries GROUP BY transfer_id HAVING count(*)<>2 OR sum(delta_kobo)<>0) x').fetchone()[0]
 assert differences==0 and unbalanced==0
 assert counts['transfers']==r['primary_transfer_count']==r['standby_transfer_count']
 assert counts['ledger_entries']==2*counts['transfers']
 assert c.execute("SELECT count(*) FROM transfers WHERE request_key IN ('test-rollback','test-later-error','test-race-b')").fetchone()[0]==0
report={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'verification':'Captured plans checked against aggregates and expected plan shapes; current database reconciled. Written summary reviewed separately.',
 'transaction_checks_passed':len(t),'nosql_behaviours_passed':len(n['checks']),
 'replication':'marker and its two postings replayed; streaming async status and read-only rejection verified',
 'manual_sql_examples':'Run on cedar_examples copy: committed transfer and reversal preserved, rolled-back request absent, reconciliation returned no differences.',
 'query_plans_captured':list(all_plans),
 'final_database_counts':counts,'final_balance_discrepancies':differences,'unbalanced_transfers':unbalanced,
 'pdf':'Personalised LMS PDF is not part of this repository or this verification.',
 'publication':'Repository: https://github.com/sarahbanks-12/MIVA-Assignment; assessor access not verified','lms':'Not submitted','student_review':'Pending',
 'semester_long_progressive_history':'Not established; do not backdate commits'}
save('portfolio-1-database-design/evidence/final-verification.json',report)
print(json.dumps(report,indent=2))

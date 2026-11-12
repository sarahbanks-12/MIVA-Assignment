from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "portfolio-1-database-design/scripts"))
import threading,time,json
from common import *
log=[]
def record(name,**data):
 log.append({'test':name,'status':'PASS',**data});print(name, data)
def app():
 c=connect();c.execute('SET ROLE cedar_app');c.commit();return c
def post(c,key,s,d,amount,kind='transfer',rev=None):
 return c.execute('SELECT post_transfer(%s,%s,%s,%s,%s,%s)',(key,s,d,amount,kind,rev)).fetchone()[0]
def balance(c,a):return c.execute('SELECT balance_kobo FROM accounts WHERE account_id=%s',(a,)).fetchone()[0]
def rejects(name,fn,expected="P0001",message=None):
 c=app()
 try:
  fn(c);c.commit()
 except psycopg.Error as e:
  c.rollback()
  assert e.sqlstate==expected,(name,e.sqlstate,str(e))
  if message is not None: assert message in str(e),(name,str(e))
  record(name,sqlstate=e.sqlstate,error=str(e).splitlines()[0])
 else:raise AssertionError(name+' unexpectedly succeeded')
 finally:c.close()
def wait_until_blocked(pid,observer):
 deadline=time.monotonic()+5
 while time.monotonic()<deadline:
  if observer.execute('SELECT cardinality(pg_blocking_pids(%s))>0',(pid,)).fetchone()[0]:return True
 return False
RECONCILE='SELECT a.account_id FROM accounts a LEFT JOIN ledger_entries l USING(account_id) GROUP BY a.account_id HAVING a.balance_kobo<>coalesce(sum(l.delta_kobo),0)'
# Rerun after rebuilding the disposable database, not against a live bank.
with connect() as c:
 for i in range(6001,6005):
  c.execute('INSERT INTO customers(customer_id,full_name,email) VALUES(%s,%s,%s)',(i,'Transaction Fixture '+str(i),f'fixture{i}@example.test'))
  c.execute("INSERT INTO accounts(account_id,customer_id,account_number,account_kind) VALUES(%s,%s,%s,'customer')",(i,i,str(i).zfill(10)))
with connect() as c:
 c.execute("SELECT setval(pg_get_serial_sequence('bank.customers','customer_id'),6004)")
 c.execute("SELECT setval(pg_get_serial_sequence('bank.accounts','account_id'),6004)")
with app() as c:
 post(c,'test-fund-1',1,6001,100000,'deposit');post(c,'test-fund-3',1,6003,100000,'deposit')
with app() as c: tid=post(c,'test-commit',6001,6002,25000)
with app() as c:
 assert (balance(c,6001),balance(c,6002))==(75000,25000)
 record('commit',source_kobo=75000,destination_kobo=25000,transfer_id=tid)
with app() as c:
 before=(balance(c,6001),balance(c,6002))
 assert post(c,'test-commit',6001,6002,25000)==tid
 # A retry must not move money a second time or add a second transfer row.
 assert (balance(c,6001),balance(c,6002))==before
 assert c.execute("SELECT count(*) FROM transfers WHERE request_key='test-commit'").fetchone()[0]==1
 record('idempotent retry',same_transfer_id=tid,balances_unchanged=True)
rejects('idempotency payload conflict',lambda c:post(c,'test-commit',6001,6002,26000),message='Idempotency key reused')
c=app();post(c,'test-rollback',6001,6002,10000)
# Prove the change really existed inside the transaction before ROLLBACK removes it.
during=(balance(c,6001),balance(c,6002));assert during==(65000,35000)
c.rollback();c.close()
with app() as c:
 assert (balance(c,6001),balance(c,6002))==(75000,25000) and c.execute("SELECT count(*) FROM transfers WHERE request_key='test-rollback'").fetchone()[0]==0
 record('explicit rollback',source_kobo=75000,inside_transaction_source_kobo=during[0],transaction_rows=0)
rejects('insufficient funds',lambda c:post(c,'test-overdraw',6001,6002,99999999),message='Insufficient funds')
rejects('negative amount',lambda c:post(c,'test-negative',6001,6002,-100),message='Invalid request')
rejects('self transfer',lambda c:post(c,'test-self',6001,6001,100),message='Invalid request')
rejects('missing account',lambda c:post(c,'test-missing',6001,999999,100),message='Unknown account')
rejects('wrong operation type',lambda c:post(c,'test-wrong-kind',6001,6002,100,'deposit'),message='Account kinds do not match')
rejects('application cannot alter balances',lambda c:c.execute('UPDATE accounts SET balance_kobo=0 WHERE account_id=6001'),expected='42501')
rejects('application cannot delete ledger',lambda c:c.execute('DELETE FROM ledger_entries WHERE transfer_id=%s',(tid,)),expected='42501')
with app() as c:rev=post(c,'test-reverse',6002,6001,25000,'reversal',tid)
with app() as c:
 assert (balance(c,6001),balance(c,6002))==(100000,0)
 assert c.execute('SELECT count(*) FROM transfers WHERE transfer_id IN (%s,%s)',(tid,rev)).fetchone()[0]==2
 record('compensating reversal preserves original',original=tid,reversal=rev)
rejects('duplicate reversal',lambda c:post(c,'test-reverse-again',6002,6001,25000,'reversal',tid),message='Already reversed')
rejects('invalid reversal reference',lambda c:post(c,'test-bad-reversal',6001,6002,100,'reversal',99999999),message='Invalid reversal')
with app() as c:
 c.execute('SET search_path=public')
 c.execute("SELECT bank.post_transfer('test-public-path',6001,6002,100)")
record('deferred check with public search path',committed=True)
with app() as c:post(c,'test-withdraw',6001,1,10000,'withdrawal')
with app() as c:
 actual=balance(c,6001);assert actual==89900
 record('withdrawal committed',source_kobo=actual)
# Competing withdrawals: hold A's row lock while B tries to spend the same balance.
a=app();post(a,'test-race-a',6003,6004,70000)
started=threading.Event();outcome={};pid={}
def competing():
 b=app();pid['value']=b.info.backend_pid;started.set()
 try:post(b,'test-race-b',6003,6004,70000);b.commit();outcome['result']='committed'
 except psycopg.Error as e:b.rollback();outcome.update(result='rejected',error=str(e).splitlines()[0],sqlstate=e.sqlstate)
 finally:b.close()
t=threading.Thread(target=competing);t.start();assert started.wait(5)
observer=connect(True);deadline=time.monotonic()+5;blocked=False
while time.monotonic()<deadline:
 if observer.execute('SELECT cardinality(pg_blocking_pids(%s))>0',(pid['value'],)).fetchone()[0]:blocked=True;break
assert blocked,'B never observed waiting on lock'
a.commit();a.close();t.join(5);assert not t.is_alive() and outcome['result']=='rejected'
assert outcome['sqlstate']=='P0001' and outcome['error']=='Insufficient funds'
assert balance(observer,6003)==30000 and balance(observer,6004)==70000
record('concurrent spend controlled',observed_blocking=True,first='committed',second=outcome,remaining_kobo=30000)
observer.close()
# Same-key race: the second caller returns the existing ID after waiting.
a=app();same_id=post(a,'test-same-key-race',6001,6002,1000)
ready=threading.Event();retry_result={}
def retry():
 b=app();retry_result['pid']=b.info.backend_pid;ready.set()
 try:retry_result['id']=post(b,'test-same-key-race',6001,6002,1000);b.commit()
 finally:b.close()
t=threading.Thread(target=retry);t.start();assert ready.wait(5)
with connect(True) as observer:
 deadline=time.monotonic()+5;blocked=False
 while time.monotonic()<deadline:
  if observer.execute('SELECT cardinality(pg_blocking_pids(%s))>0',(retry_result['pid'],)).fetchone()[0]:blocked=True;break
 assert blocked
 a.commit();a.close();t.join(5);assert not t.is_alive() and retry_result['id']==same_id
record('concurrent idempotent retry',observed_blocking=True,same_transfer_id=same_id)
# Isolation experiment on a separate disposable table, never on real account rows.
with connect(True) as c:
 c.execute('CREATE TABLE bank.isolation_demo(id int PRIMARY KEY,value int NOT NULL)')
 c.execute('INSERT INTO isolation_demo VALUES(1,100)')
for level,expected in [('READ COMMITTED',200),('REPEATABLE READ',100)]:
 with connect(True) as b:b.execute('UPDATE isolation_demo SET value=100')
 a=connect();a.execute('SET TRANSACTION ISOLATION LEVEL '+level)
 first=a.execute('SELECT value FROM isolation_demo').fetchone()[0]
 with connect(True) as b:b.execute('UPDATE isolation_demo SET value=200')
 second=a.execute('SELECT value FROM isolation_demo').fetchone()[0]
 assert (first,second)==(100,expected);a.rollback();a.close()
 record('isolation '+level,first_read=first,second_read=second)
# Deliberately unsafe read/compute/write schedule reproduces a lost update.
with connect(True) as c:c.execute('UPDATE isolation_demo SET value=100')
a=connect();b=connect();av=a.execute('SELECT value FROM isolation_demo').fetchone()[0];bv=b.execute('SELECT value FROM isolation_demo').fetchone()[0]
a.execute('UPDATE isolation_demo SET value=%s',(av-30,));a.commit()
b.execute('UPDATE isolation_demo SET value=%s',(bv-40,));b.commit();a.close();b.close()
with connect(True) as c:
 actual=c.execute('SELECT value FROM isolation_demo').fetchone()[0];assert actual==60
 record('unsafe lost update reproduced',expected_with_both_debits=30,actual=actual)
 c.execute('UPDATE isolation_demo SET value=100')
# The identical schedule under REPEATABLE READ: the second writer must fail and retry.
a=connect();b=connect()
for s in (a,b):s.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
av=a.execute('SELECT value FROM isolation_demo').fetchone()[0];bv=b.execute('SELECT value FROM isolation_demo').fetchone()[0]
a.execute('UPDATE isolation_demo SET value=%s',(av-30,));a.commit()
try:
 b.execute('UPDATE isolation_demo SET value=%s',(bv-40,));b.commit()
 raise AssertionError('Second REPEATABLE READ writer unexpectedly committed')
except psycopg.Error as e:
 b.rollback();assert e.sqlstate=='40001',e.sqlstate;conflict=e.sqlstate
a.close();b.close()
with connect(True) as c:
 actual=c.execute('SELECT value FROM isolation_demo').fetchone()[0];assert actual==70
 record('repeatable read rejects the lost update',second_writer_sqlstate=conflict,committed_value=actual)
 c.execute('DROP TABLE isolation_demo')
# A missing posting is rejected by the deferred constraint even for the owner.
c=connect()
try:
 c.execute("INSERT INTO transfers(request_key,source_account,destination_account,amount_kobo,kind) VALUES('test-unbalanced',6001,6002,100,'transfer')")
 c.commit();raise AssertionError('Unbalanced transfer committed')
except psycopg.Error as e:
 c.rollback();assert e.sqlstate=='P0001' and 'two balanced postings' in str(e)
 record('deferred balanced-posting constraint',error=str(e).splitlines()[0])
finally:c.close()
rejects('zero amount',lambda c:post(c,'test-zero',6001,6002,0),message='Invalid request')
rejects('null amount',lambda c:post(c,'test-null',6001,6002,None),message='Invalid request')
rejects('unknown operation type',lambda c:post(c,'test-kind',6001,6002,100,'unknown'),expected='23514')
rejects('reversal of a reversal',lambda c:post(c,'test-nested-reversal',6001,6002,25000,'reversal',rev),message='Invalid reversal')
# Atomic rollback after an error occurring AFTER a valid function call.
c=app();before=(balance(c,6001),balance(c,6002))
try:
 post(c,'test-later-error',6001,6002,1000)
 c.execute('SELECT 1/0')
except psycopg.Error as e:
 assert e.sqlstate=='22012';c.rollback()
else:raise AssertionError('Expected transaction failure')
assert (balance(c,6001),balance(c,6002))==before
assert c.execute("SELECT count(*) FROM transfers WHERE request_key='test-later-error'").fetchone()[0]==0
c.close();record('later transaction error rolls back all postings',balances_unchanged=True,transfer_rows=0)
# Reversal identity: each request targets a live original, so only the identity check can reject it.
with app() as c:original=post(c,'test-identity-original',6001,6002,500)
rejects('reversal with wrong amount',lambda c:post(c,'test-reverse-amount',6002,6001,499,'reversal',original),message='Invalid reversal')
rejects('reversal with wrong accounts',lambda c:post(c,'test-reverse-accounts',6001,6002,500,'reversal',original),message='Invalid reversal')
# Two requests with different keys race to reverse one original: exactly one may win.
with app() as c:contested=post(c,'test-race-original',6001,6002,500)
gate=threading.Barrier(2);race=[]
def reverse(key):
 b=app()
 try:gate.wait(5);post(b,key,6002,6001,500,'reversal',contested);b.commit();race.append('committed')
 except psycopg.Error as e:b.rollback();race.append(e.sqlstate+':'+str(e).splitlines()[0])
 finally:b.close()
workers=[threading.Thread(target=reverse,args=(k,)) for k in ('test-race-reverse-a','test-race-reverse-b')]
for t in workers:t.start()
for t in workers:t.join(10)
assert sorted(race)==['P0001:Already reversed','committed'],race
with app() as c:
 assert c.execute('SELECT count(*) FROM transfers WHERE reversal_of=%s',(contested,)).fetchone()[0]==1
record('competing reversals commit once',original=contested,outcomes=sorted(race))
# If the first caller rolls back, a waiting retry must proceed and record the transfer once.
a=app();abandoned=post(a,'test-same-key-rollback',6001,6002,300)
ready=threading.Event();waiter={}
def retry_after_rollback():
 b=app();waiter['pid']=b.info.backend_pid;ready.set()
 try:waiter['id']=post(b,'test-same-key-rollback',6001,6002,300);b.commit()
 finally:b.close()
t=threading.Thread(target=retry_after_rollback);t.start();assert ready.wait(5)
with connect(True) as observer:assert wait_until_blocked(waiter['pid'],observer)
a.rollback();a.close();t.join(5);assert not t.is_alive() and waiter['id']!=abandoned
with app() as c:
 assert c.execute("SELECT count(*) FROM transfers WHERE request_key='test-same-key-rollback'").fetchone()[0]==1
record('waiting retry proceeds after first caller rolls back',rolled_back_id=abandoned,committed_id=waiter['id'])
# Opposite-direction traffic on the same two wallets: ordered locks must prevent deadlock.
with app() as c:start=(balance(c,6003),balance(c,6004))
failures=[]
def opposite(source,destination,worker,attempts=40):
 b=app()
 for i in range(attempts):
  if failures:break # Stop at the first failure so a deadlock is reported at once.
  try:post(b,f'test-opposite-{worker}-{i}',source,destination,1);b.commit()
  except psycopg.Error as e:b.rollback();failures.append(e.sqlstate)
 b.close()
workers=[threading.Thread(target=opposite,args=((6003,6004,w) if w%2==0 else (6004,6003,w))) for w in range(8)]
for t in workers:t.start()
for t in workers:t.join(60)
assert not any(t.is_alive() for t in workers) and failures==[],failures[:5]
with app() as c:
 assert (balance(c,6003),balance(c,6004))==start
 posted=c.execute("SELECT count(*) FROM transfers WHERE request_key LIKE 'test-opposite-%'").fetchone()[0];assert posted==320
record('opposite-direction transfers do not deadlock',workers=8,transfers=posted,failures=0,balances_unchanged=True)
# The application role may read and call post_transfer, and nothing else.
rejects('application cannot insert transfers',lambda c:c.execute("INSERT INTO transfers(request_key,source_account,destination_account,amount_kobo,kind) VALUES('test-direct',6001,6002,1,'transfer')"),expected='42501')
with connect(True) as c:
 can=lambda table,priv:c.execute('SELECT has_table_privilege(%s,%s,%s)',('cedar_app','bank.'+table,priv)).fetchone()[0]
 tables=('customers','accounts','transfers','ledger_entries')
 writes=[(t,p) for t in tables for p in ('INSERT','UPDATE','DELETE','TRUNCATE') if can(t,p)]
 signature='bank.post_transfer(text,bigint,bigint,bigint,text,bigint)'
 execute=lambda role:c.execute('SELECT has_function_privilege(%s,%s,%s)',(role,signature,'EXECUTE')).fetchone()[0]
 assert writes==[] and all(can(t,'SELECT') for t in tables) and execute('cedar_app') and not execute('public')
 record('application role is function-only for writes',write_privileges_found=len(writes),app_can_execute=True,public_can_execute=False)
# Table-level constraints: use owner access in a rolled-back test transaction.
def owner_reject(name,sql,expected,message=None):
 c=connect()
 try:c.execute(sql);c.commit()
 except psycopg.Error as e:
  c.rollback();assert e.sqlstate==expected,(name,e.sqlstate)
  if message is not None:assert message in str(e),(name,str(e))
  record(name,sqlstate=e.sqlstate,error=str(e).splitlines()[0])
 else:raise AssertionError(name+' unexpectedly succeeded')
 finally:c.close()
# The deferred constraint must inspect the postings, not merely notice that some exist.
def bad_postings(name,transfer,postings):
 owner_reject(name,f"INSERT INTO transfers(transfer_id,request_key,source_account,destination_account,amount_kobo,kind) VALUES({transfer},'test-posting-{transfer}',6001,6002,100,'transfer');INSERT INTO ledger_entries VALUES {postings}",'P0001','two balanced postings')
bad_postings('deferred constraint rejects one posting',900001,'(900001,6001,-100)')
bad_postings('deferred constraint rejects two credits',900002,'(900002,6001,100),(900002,6002,100)')
bad_postings('deferred constraint rejects wrong amounts',900003,'(900003,6001,-50),(900003,6002,50)')
owner_reject('reversal_of is unique',f"INSERT INTO transfers(request_key,source_account,destination_account,amount_kobo,kind,reversal_of) VALUES('test-second-reversal',6002,6001,25000,'reversal',{tid})",'23505','transfers_reversal_of_key')
owner_reject('account owner foreign key',"INSERT INTO accounts(customer_id,account_number,account_kind) VALUES(999999,'9999999999','customer')",'23503')
owner_reject('unique account number',"INSERT INTO accounts(customer_id,account_number,account_kind) VALUES(6001,'0000006001','customer')",'23505')
owner_reject('nonnegative customer balance',"UPDATE accounts SET balance_kobo=-1 WHERE account_id=6001",'23514')
owner_reject('only one clearing account',"INSERT INTO accounts(customer_id,account_number,account_kind) VALUES(NULL,'9999999998','clearing')",'23505')
# A reconciliation that can only ever return zero rows proves nothing: inject a 1-kobo error first.
c=connect()
c.execute('UPDATE accounts SET balance_kobo=balance_kobo+1 WHERE account_id=6001')
flagged=c.execute(RECONCILE).fetchall();c.rollback()
clean=c.execute(RECONCILE).fetchall();c.rollback();c.close()
assert flagged==[(6001,)] and clean==[],(flagged,clean)
record('reconciliation detects an injected 1-kobo error',flagged_account=6001,differences_after_rollback=0)
with connect(True) as c:
 discrepancies=c.execute(RECONCILE).fetchall()
 total=c.execute('SELECT sum(delta_kobo) FROM ledger_entries').fetchone()[0]
 negative=c.execute("SELECT count(*) FROM accounts WHERE account_kind='customer' AND balance_kobo<0").fetchone()[0]
 assert not discrepancies and total==0 and negative==0
 record('final ledger invariants',balance_discrepancies=0,global_net_kobo=int(total),negative_customer_balances=negative)
save('portfolio-3-transactions-concurrency/evidence/tests.json',log)

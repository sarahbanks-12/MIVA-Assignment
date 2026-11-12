from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "portfolio-1-database-design/scripts"))
import time,json,os
import psycopg
from common import *
p=connect(True)
s=psycopg.connect(os.getenv('CEDAR_STANDBY_DSN','host=127.0.0.1 port=55504 user=portfolio dbname=cedar'),autocommit=True)
s.execute('SET search_path=bank,public')
assert s.execute('SELECT pg_is_in_recovery()').fetchone()[0]
# A unique committed transfer is the replication marker, not just server status.
marker='replication-marker-'+str(time.time_ns())
tid=p.execute("SELECT post_transfer(%s,1,42,12345,'deposit')",(marker,)).fetchone()[0]
lsn=p.execute('SELECT pg_current_wal_lsn()').fetchone()[0]
start=time.monotonic();deadline=start+10;seen=None
while time.monotonic()<deadline:
 seen=s.execute('SELECT transfer_id,amount_kobo FROM transfers WHERE request_key=%s',(marker,)).fetchone()
 if seen:break
 time.sleep(.02)
assert seen==(tid,12345),'Replica did not replay marker within 10 seconds'
observed_elapsed=round(time.monotonic()-start,4)
postings=s.execute('SELECT account_id,delta_kobo FROM ledger_entries WHERE transfer_id=%s ORDER BY account_id',(tid,)).fetchall()
assert postings==[(1,-12345),(42,12345)]
write_error=None
try:s.execute("INSERT INTO customers(full_name,email) VALUES('Blocked','blocked@example.test')")
except psycopg.Error as e:write_error={'sqlstate':e.sqlstate,'error':str(e).splitlines()[0]}
assert write_error and write_error['sqlstate']=='25006'
rows=p.execute('SELECT state,sync_state,sent_lsn::text,write_lsn::text,flush_lsn::text,replay_lsn::text FROM pg_stat_replication').fetchall()
assert rows and any(row[0]=='streaming' and row[1]=='async' for row in rows)
report={'topology':'Two PostgreSQL instances on one host; physical streaming replication; asynchronous',
 'primary_port':55503,'standby_port':55504,'standby_in_recovery':True,
 'marker':marker,'transfer_id':tid,'amount_kobo':12345,'primary_wal_lsn':str(lsn),
 'observed_within_seconds':observed_elapsed,'standby_marker_postings':postings,'primary_replication_rows':rows,
 'standby_write_rejected':write_error,'primary_transfer_count':p.execute('SELECT count(*) FROM transfers').fetchone()[0],
 'standby_transfer_count':s.execute('SELECT count(*) FROM transfers').fetchone()[0],
 'limitations':'Not cloud deployment, not separate failure domains, no failover or disaster recovery test; measured observation interval is not a general lag guarantee.'}
assert report['primary_transfer_count']==report['standby_transfer_count']
save('portfolio-5-distributed-cloud/evidence/replication.json',report)
print(json.dumps(report,indent=2));p.close();s.close()

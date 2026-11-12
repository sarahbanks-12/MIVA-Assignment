from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "portfolio-1-database-design/scripts"))
from concurrent.futures import ThreadPoolExecutor
import os,time,json
import redis
from common import ROOT,save
r=redis.Redis.from_url(os.getenv('CEDAR_REDIS_URL','redis://127.0.0.1:56403/0'),decode_responses=True)
# A reserved teaching prefix allows safe reruns without FLUSHDB.
keys=list(r.scan_iter('cedar:portfolio:*'))
if keys:r.delete(*keys)
profile='cedar:portfolio:customer:42:preferences'
r.hset(profile,mapping={'customer_id':'42','channel':'email','language':'en','daily_digest':'false'})
assert r.hget(profile,'channel')=='email'
r.hset(profile,'channel','push')
assert r.hget(profile,'channel')=='push'
# Hash fields can evolve without an ALTER TABLE; applications still validate values.
r.hset(profile,'quiet_hours','22:00-06:00')
script=r.register_script((ROOT/'portfolio-4-nosql/velocity.lua').read_text())
key='cedar:portfolio:customer:42:attempts'
with ThreadPoolExecutor(max_workers=8) as pool:
 results=list(pool.map(lambda _:script(keys=[key],args=[60]),range(20)))
assert sorted(int(x[0]) for x in results)==list(range(1,21))
assert r.get(key)=='20' and 0<r.ttl(key)<=60
risk='cedar:portfolio:risk-review'
r.zadd(risk,{'transfer-demo-1':70,'transfer-demo-2':95,'transfer-demo-3':20})
ranked=r.zrevrange(risk,0,1,withscores=True)
assert ranked==[('transfer-demo-2',95.0),('transfer-demo-1',70.0)]
# Exact expiry checked against the real server, not a mock.
fixed='cedar:portfolio:window-check'
assert script(keys=[fixed],args=[5])[0]==1
time.sleep(1.1)
remaining_before=r.pttl(fixed)
assert 0<remaining_before<4500
assert script(keys=[fixed],args=[5])[0]==2
remaining_after=r.pttl(fixed)
assert 0<remaining_after<=remaining_before,'Later increment extended the window'
expiry='cedar:portfolio:expiry-check'
assert script(keys=[expiry],args=[1])[0]==1
time.sleep(1.1);assert r.get(expiry) is None
r.hdel(profile,'quiet_hours');assert not r.hexists(profile,'quiet_hours')
report={'server_version':r.info('server')['redis_version'],'model':'Redis key-value store with hashes, sorted sets and an atomic Lua counter',
 'preferences':r.hgetall(profile),'concurrent_counter':r.get(key),'ttl_seconds':r.ttl(key),
 'fixed_window_before_ms':remaining_before,'fixed_window_after_ms':remaining_after,
 'unique_counter_results':sorted(int(x[0]) for x in results),'top_risks':ranked,
 'checks':{'hash_create_read_update_delete':True,'20_concurrent_increments':True,'fixed_window_ttl':True,'expiry_observed':True,'risk_ranking':True},
 'persistence':r.config_get('appendonly','appendfsync'),
 'scope':'No customer PII or authoritative balances stored; demo risk scores are synthetic, not a fraud model.'}
save('portfolio-4-nosql/evidence/results.json',report);print(json.dumps(report,indent=2))

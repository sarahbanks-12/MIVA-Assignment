from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "portfolio-1-database-design/scripts"))
import statistics, platform, json
from common import *
c=connect(True)
q='SELECT transfer_id,amount_kobo,kind,created_at FROM transfers WHERE destination_account=42 ORDER BY created_at DESC,transfer_id DESC LIMIT 20'
results={'platform':platform.platform(),'postgres':c.execute('SELECT version()').fetchone()[0],
 'rows':c.execute('SELECT count(*) FROM transfers').fetchone()[0],
 'method':'One warm-up and seven measured EXPLAIN ANALYZE runs per configuration; same session and query; warm-cache local timings, not production capacity.'}
c.execute('DROP INDEX IF EXISTS transfers_destination_recent')
expected=c.execute(q).fetchall()
for label in ['before','after']:
 if label=='after': c.execute((ROOT/'portfolio-2-query-optimisation/index.sql').read_text())
 c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q).fetchone()
 plans=[c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+q).fetchone()[0][0] for _ in range(7)]
 for p in plans:check_plan_shape(label,p)
 times=[p['Execution Time'] for p in plans]
 results[label]={'execution_ms':times,'median_ms':statistics.median(times),
 'min_ms':min(times),'max_ms':max(times),'root_shared_hit_blocks':plans[-1]['Plan'].get('Shared Hit Blocks'),
 'root_shared_read_blocks':plans[-1]['Plan'].get('Shared Read Blocks')}
 save(f'portfolio-2-query-optimisation/evidence/{label}-plans.json',plans)
 plan='\n'.join(r[0] for r in c.execute('EXPLAIN (ANALYZE,BUFFERS) '+q))
 (ROOT/f'portfolio-2-query-optimisation/evidence/{label}-plan.txt').write_text(plan+'\n')
 assert c.execute(q).fetchall()==expected
assert results['after']['median_ms']<results['before']['median_ms'] and results['after']['root_shared_hit_blocks']<results['before']['root_shared_hit_blocks'],'Index did not reduce time and buffer work'
results['index_bytes']=c.execute("SELECT pg_relation_size('transfers_destination_recent')").fetchone()[0]
results['result_equivalence']=True
save('portfolio-2-query-optimisation/evidence/benchmark.json',results)
save('portfolio-2-query-optimisation/evidence/q1-results.json',expected)
print(json.dumps(results,indent=2))

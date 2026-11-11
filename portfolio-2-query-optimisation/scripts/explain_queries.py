from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "portfolio-1-database-design/scripts"))
"""Capture an execution plan for every statement in queries.sql, using the file's exact text."""
import re
from common import ROOT,connect,save
source=(ROOT/'portfolio-2-query-optimisation/queries.sql').read_text()
# Each query is preceded by a "-- Qn: description" comment.
pattern=re.compile(r'--\s*(Q\d+):\s*(.*?)\n(SELECT.*?);',re.S)
queries=[(m[1],m[2].strip(),m[3]) for m in pattern.finditer(source)]
assert [q[0] for q in queries]==['Q1','Q2','Q3','Q4','Q5'],queries
report=[]
with connect(True) as c:
 for label,description,sql in queries:
  plan=c.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+sql).fetchone()[0][0]
  text='\n'.join(r[0] for r in c.execute('EXPLAIN (ANALYZE,BUFFERS) '+sql))
  report.append({'query':label,'description':description,'plan':plan})
  print(f'-- {label}: {description}\n{text}\n')
save('portfolio-2-query-optimisation/evidence/all-query-plans.json',report)

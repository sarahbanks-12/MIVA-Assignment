import os, json
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[2]
DSN=os.getenv('CEDAR_DSN','host=127.0.0.1 port=55483 user=portfolio dbname=cedar')
def connect(autocommit=False):
    c=psycopg.connect(DSN,autocommit=autocommit)
    c.execute('SET search_path=bank,public')
    if not autocommit: c.commit()
    return c
INDEX_NAME='transfers_destination_recent'
def plan_nodes(node):
    return [node]+[n for child in node.get('Plans',[]) for n in plan_nodes(child)]
def check_plan_shape(label,plan):
    """Fail unless a captured plan shows what the written analysis says it shows."""
    nodes=plan_nodes(plan['Plan']);types=[n['Node Type'] for n in nodes]
    uses_index=any(n['Node Type']=='Index Scan' and n.get('Index Name')==INDEX_NAME and 'destination_account' in n.get('Index Cond','') for n in nodes)
    if label=='before':
        assert 'Seq Scan' in types and 'Sort' in types and not uses_index,('baseline plan is not a scan and sort',types)
    else:
        assert uses_index and 'Sort' not in types,('indexed plan does not read the index in order',types)
def save(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,default=str)+'\n')

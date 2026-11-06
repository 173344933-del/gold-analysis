"""Exit 1 on inadequate data, independently of static-file verification."""
import argparse
import json
from pathlib import Path
from radar.readiness import assess

def check(directory, expected_sessions=None):
    root=Path(directory)/'data'
    snapshot=json.loads((root/'snapshot.json').read_text())
    ledger=json.loads((root/'score-inputs.json').read_text())
    markets=json.loads((root/'market-audit.json').read_text())
    result=assess(snapshot,ledger,markets,expected_sessions)
    (root/'readiness.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result['status']=='core_data_ready'

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',nargs='?',default='dist')
    parser.add_argument('--expected-session',action='append',default=[],metavar='REGION=YYYY-MM-DD')
    args=parser.parse_args()
    expected=dict(v.split('=',1) for v in args.expected_session)
    raise SystemExit(0 if check(args.directory,expected) else 1)

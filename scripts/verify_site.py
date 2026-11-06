import json
import sys
from pathlib import Path

def verify(directory):
 root=Path(directory)
 html=(root/'index.html').read_text()
 assert 'data-mode="static"' in html and './static-api.js' in html
 assert 'href="/style.css"' not in html and 'src="/app.js"' not in html
 for f in ['app.js','style.css','static-api.js','data/snapshot.json','data/build.json','data/history-000001.SH.json','data/score-inputs.json','data/market-audit.json','data/readiness.json']:
  assert (root/f).is_file(),f
 s=json.loads((root/'data/snapshot.json').read_text())
 assert not s['notes'] and not s['decisions'] and not s['scenarios'] and not s['watchlist']
 assert not any(r['source'].startswith('import:') for r in s['evidence'])
 h=json.loads((root/'data/history-000001.SH.json').read_text())
 assert len(h['events'])>=20
 assert h['meta']['first']<'2000-01-01'
 assert h['meta']['count']>5000
 assert any(e['study'].get('available') for e in h['events'])
 print('PASS: static asset paths, public-data isolation, 20+ events, actual 1990s history and valid event studies')
if __name__=='__main__':verify(sys.argv[1] if len(sys.argv)>1 else 'dist')

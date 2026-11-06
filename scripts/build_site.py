"""Produce a self-contained GitHub Pages site without publishing private research."""
import json
import hashlib
import os
import shutil
from pathlib import Path
from radar import store
from radar.catalog import SOURCES
from radar.ingest import run_source, refresh
from radar.server import snapshot, market_data
from radar.history import manifest, overview
from radar.readiness import assess

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'dist'

def market_filename(symbol):
 return 'market-'+hashlib.sha256(symbol.encode('utf-8')).hexdigest()[:24]+'.json'

def build():
 if OUT.is_symlink():raise ValueError('Build output must not be a symlink')
 if OUT.exists():shutil.rmtree(OUT)
 OUT.mkdir(exist_ok=True)
 for name in ['index.html','style.css','app.js','static-api.js','favicon.svg']:
  shutil.copy2(ROOT/'web'/name,OUT/name)
 html=(OUT/'index.html').read_text().replace('<html lang="zh-CN">','<html lang="zh-CN" data-mode="static">').replace('href="/"','href="./"').replace('href="/style.css"','href="./style.css"').replace('src="/app.js"','src="./static-api.js" defer></script><script src="./app.js"')
 (OUT/'index.html').write_text(html)
 (OUT/'.nojekyll').touch()
 data=OUT/'data';data.mkdir(exist_ok=True)
 # Always build from a separate database. Never export researcher imports,
 # watchlists, notes, subjective scenarios, credentials or decisions.
 original=store.DB_PATH
 store.DB_PATH=ROOT/'.radar/build.db'
 store.init()
 for source in SOURCES:
  if source['kind']=='bundled':run_source(source)
 if os.environ.get('RADAR_REFRESH_PUBLIC')=='1':refresh()
 s=snapshot()
 s['watchlist']=[];s['notes']={};s['decisions']=[];s['scenarios']={}
 s['evidence']=[r for r in s['evidence'] if not r['source'].startswith('import:')]
 with store.db() as c:
  all_evidence=[dict(r) for r in c.execute('SELECT * FROM evidence ORDER BY published DESC,id')]
  allowed={source['id'] for source in SOURCES}
  if any(r['source'] not in allowed for r in all_evidence):raise ValueError('public_cache_contains_unapproved_source')
  input_ids={eid for t in s['themes'] for eid in t['audit']['input_ids']}
  ledger=[r for r in all_evidence if r['id'] in input_ids]
  market_audit=[]
  for row in c.execute('SELECT source,symbol,max(date) last_date FROM observations GROUP BY source,symbol').fetchall():
   r=dict(row)
   r['latest_metrics']={v['metric']:v['value'] for v in c.execute('SELECT metric,value FROM observations WHERE source=? AND symbol=? AND date=?',(r['source'],r['symbol'],r['last_date']))}
   market_audit.append(r)
 s['data_readiness']=assess(s,ledger,market_audit)
 (data/'score-inputs.json').write_text(json.dumps(ledger,ensure_ascii=False,separators=(',',':')))
 (data/'market-audit.json').write_text(json.dumps(market_audit,ensure_ascii=False,separators=(',',':')))
 (data/'readiness.json').write_text(json.dumps(s['data_readiness'],ensure_ascii=False,indent=2))
 for row in s['evidence']:row['summary']=row['summary'][:280]
 s['deployment_mode']='public-static-browser-local'
 (data/'snapshot.json').write_text(json.dumps(s,ensure_ascii=False,separators=(',',':')))
 with store.db() as c:
  symbols=[dict(r) for r in c.execute('SELECT symbol,source,count(*) records,min(date) first_date,max(date) last_date,group_concat(DISTINCT metric) metrics FROM observations GROUP BY symbol,source')]
  holdings=[dict(r) for r in c.execute('SELECT * FROM holdings ORDER BY filed DESC,reported_value DESC LIMIT 200')]
 (data/'symbols.json').write_text(json.dumps(symbols,ensure_ascii=False))
 (data/'holdings.json').write_text(json.dumps({'rows':holdings,'note':'13F延迟披露，非完整仓位；原文value未归一化历史口径。'},ensure_ascii=False))
 for row in symbols:
  (data/market_filename(row['symbol'])).write_text(json.dumps(market_data(row['symbol']),ensure_ascii=False,separators=(',',':')))
 for meta in manifest()['series']:
  (data/('history-'+meta['symbol']+'.json')).write_text(json.dumps(overview(meta['symbol']),ensure_ascii=False,separators=(',',':')))
 (data/'build.json').write_text(json.dumps({'as_of':s['as_of'],'revision':os.environ.get('GITHUB_SHA','local'),'evidence':s['evidence_total'],'historical_series':len(manifest()['series']),'public_deployment':'limited-core-research' if s['data_readiness']['status']=='core_data_ready' else 'data-insufficient', 'data_readiness':s['data_readiness']['status'],'private_research_exported':False},ensure_ascii=False))
 store.DB_PATH=original
 print('Built',OUT,'files',len(list(OUT.rglob('*'))),'bytes',sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()))
if __name__=='__main__':
 try:
  build()
 except Exception as error:
  # Public annotations give actionable failures without exposing environments,
  # credential files, HTTP headers or private research data.
  message=(type(error).__name__+': '+str(error)).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
  print('::error title=Public snapshot build failed::'+message,flush=True)
  raise

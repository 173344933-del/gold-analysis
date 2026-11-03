import json
import os
import time
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

def verify(url):
 url=url.rstrip('/')+'/'
 result={'url':url,'checked':datetime.now(timezone.utc).isoformat(),'status':'failed'}
 try:
  last=None
  for attempt in range(12):
   try:
    with urllib.request.urlopen(url,timeout=20) as r:
     html=r.read().decode();assert r.status==200
    assert 'data-mode="static"' in html and 'static-api.js' in html
    with urllib.request.urlopen(url+'data/build.json',timeout=20) as r:build=json.load(r)
    assert build['private_research_exported'] is False
    expected=os.environ.get('GITHUB_SHA')
    if expected:assert build['revision']==expected,'Public site is not the current commit'
    with urllib.request.urlopen(url+'data/history-000001.SH.json',timeout=20) as r:history=json.load(r)
    assert len(history['events'])>=20 and history['meta']['count']>5000
    result.update(status='passed',build=build,historical_series=len(history['manifest']['series']),event_count=len(history['events']))
    break
   except Exception as e:last=type(e).__name__;time.sleep(min(5,attempt+1))
  else:raise RuntimeError('Public verification failed: '+str(last))
 finally:
  path=Path('.radar/deployment-verification.json');path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False))
 return result
if __name__=='__main__':verify(os.environ['RADAR_PUBLIC_URL'])

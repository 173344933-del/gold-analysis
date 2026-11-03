"""Optional real Chromium regression. Uses an isolated database; never seeds live data."""
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent

def run():
 with tempfile.TemporaryDirectory(prefix='radar-browser-') as directory:
  with socket.socket() as sock:
   sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  base=f'http://127.0.0.1:{port}'
  process=subprocess.Popen(['python3','-m','radar.server','--port',str(port)],cwd=ROOT,env={**os.environ,'RADAR_DB':directory+'/browser.db'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for attempt in range(50):
    try:
     urllib.request.urlopen(base+'/api/health',timeout=1);break
    except OSError:time.sleep(.1)
   else:raise AssertionError('Server did not start')
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    page.goto(base,wait_until='networkidle')
    assert page.locator('.theme-card').count()==6
    assert page.locator('.heat-value.missing').count()==5
    for view in ['radar','markets','watchlist','evidence','sources','method','overview']:
     page.locator('[data-view="'+view+'"]').click()
     page.wait_for_timeout(100)
     assert page.locator('h1').inner_text()
    # All fixture evidence is isolated and clearly synthetic; never shown in live app.
    now=datetime.now(timezone.utc).isoformat()
    records=[{'title':'TEST FIXTURE Artificial intelligence '+str(i),'url':'https://example.org/test-only/'+str(i),'published':now,'source':'test-'+str(i%2),'theme':'ai'} for i in range(4)]
    page.locator('[data-view="evidence"]').click()
    page.locator('[data-action="import"]').first.click()
    page.locator('#import-text').fill(json.dumps(records))
    page.locator('#submit-import').click()
    page.wait_for_selector('.evidence-item')
    assert page.locator('.evidence-item').count()==4
    # Annotation is explicit and immediately changes the descriptive consensus.
    for i in range(3):
     page.locator('.evidence-item').nth(i).locator('[data-stance="support"]').click()
     page.wait_for_timeout(150)
    page.locator('[data-view="radar"]').click()
    page.locator('[data-market="CN"]').click()
    page.locator('#theme-search').fill('AI')
    assert page.locator('tbody tr').count()==1
    page.locator('tbody tr').click()
    page.wait_for_selector('#research-note')
    assert page.locator('.detail-metric strong').nth(0).inner_text().strip().startswith(('3','4','5','6','7','8','9','1'))
    assert page.locator('.detail-metric strong').nth(1).inner_text().startswith('100')
    page.locator('#research-note').fill('TEST ONLY: verify revenue and capex before changing the thesis.')
    page.locator('[data-action="save-note"]').click()
    page.wait_for_timeout(150)
    # Saving a watch must preserve an unsaved note draft in the dialog.
    page.locator('#research-note').fill('TEST ONLY: unsaved draft')
    page.locator('#detail-dialog [data-watch]').click()
    page.wait_for_timeout(150)
    assert page.locator('#research-note').input_value()=='TEST ONLY: unsaved draft'
    for key,value in {'price':100,'bear':70,'base':110,'bull':150,'p_bear':25,'p_base':50,'p_bull':25}.items():
     page.locator('#scenario-'+key).fill(str(value))
    page.locator('[data-action="save-scenario"]').click()
    page.wait_for_selector('.scenario-result')
    assert '10%' in page.locator('.scenario-result').inner_text()
    page.locator('#decision-rationale').fill('TEST ONLY: verify the primary cash-flow evidence.')
    page.locator('[data-action="save-decision"]').click()
    page.wait_for_selector('.decision-entry')
    assert 'TEST ONLY' in page.locator('.decision-entry').inner_text()
    with page.expect_download() as download:
     page.locator('#detail-dialog a[href^="/api/memo"]').click()
    text=Path(download.value.path()).read_text()
    assert 'TEST ONLY' in text and 'expected_return' in text
    page.locator('[data-action="close-detail"]').click()
    page.reload(wait_until='networkidle')
    page.locator('[data-view="watchlist"]').click()
    assert page.locator('.theme-card').count()==1
    for view in ['overview','radar','markets','watchlist','evidence','sources','method']:
     page.set_viewport_size({'width':390,'height':844})
     page.locator('[data-view="'+view+'"]').click()
     page.wait_for_timeout(100)
     assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),view
    assert not errors,errors
    browser.close()
   print('PASS: 7 views, empty state, import, manual consensus, market/search filters, notes, watchlist, scenario, judgment log, memo download, persistence, mobile overflow, zero console errors. Isolated database removed.')
  finally:
   process.terminate();process.wait(timeout=5)

if __name__=='__main__':run()

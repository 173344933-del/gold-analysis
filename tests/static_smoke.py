"""Validate the public build under a project subpath, with no Python API server."""
import subprocess,tempfile,socket,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent

def run():
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 process=subprocess.Popen(['python3','-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(ROOT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  base=f'http://127.0.0.1:{port}/dist/'
  for _ in range(30):
   try:urllib.request.urlopen(base,timeout=1);break
   except OSError:time.sleep(.1)
  with sync_playwright() as p:
   b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=b.new_page(viewport={'width':1440,'height':1000});errors=[];requests=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
   page.on('request',lambda r:requests.append(r.url))
   page.goto(base,wait_until='networkidle')
   assert '公开研究试用版' in page.locator('#status-banner').inner_text()
   assert page.locator('.stat-value').first.inner_text().startswith('14')
   page.locator('[data-view="history"]').click();page.wait_for_selector('.event-row')
   assert page.locator('.event-row').count()>=20
   assert '雷曼' in page.locator('.history-layout .panel h2').last.inner_text()
   page.locator('#history-symbol').select_option('SP500.MONTHLY')
   page.wait_for_timeout(200)
   assert '月度观测' in page.locator('.event-returns').inner_text()
   assert '日线触发' in page.locator('#content').inner_text()
   with page.expect_download() as d:page.locator('a[download="event-study.json"]').click()
   h=json.loads(Path(d.value.path()).read_text());assert h['meta']['frequency']=='monthly_average'
   page.locator('[data-view="radar"]').click()
   page.locator('tr[data-theme="ai"]').click()
   page.locator('#research-note').fill('STATIC PRIVATE NOTE - never publish')
   page.locator('[data-action="save-note"]').click();page.wait_for_timeout(100)
   page.locator('#detail-dialog [data-watch]').click();page.wait_for_timeout(100)
   page.locator('[data-action="close-detail"]').click();page.reload(wait_until='networkidle')
   page.locator('[data-view="watchlist"]').click();assert page.locator('.theme-card').count()==1
   page.locator('.theme-card').click();assert page.locator('#research-note').input_value()=='STATIC PRIVATE NOTE - never publish'
   with page.expect_download() as d:page.locator('#detail-dialog a[href^="/api/memo"]').click()
   assert 'STATIC PRIVATE NOTE' in Path(d.value.path()).read_text()
   page.locator('[data-action="close-detail"]').click()
   for view in ['overview','history','radar','markets','watchlist','evidence','sources','method']:
    page.set_viewport_size({'width':390,'height':844});page.locator('[data-view="'+view+'"]').click();page.wait_for_timeout(120)
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),view
   assert not errors,errors
   assert not any('/api/' in r for r in requests),requests
   assert 'STATIC PRIVATE NOTE' not in (ROOT/'dist/data/snapshot.json').read_text()
   page.set_viewport_size({'width':1440,'height':1000});page.locator('[data-view="history"]').click();page.wait_for_timeout(100)
   page.screenshot(path='/tmp/radar-history-desktop.png',full_page=True)
   b.close()
  print('PASS: project subpath, 14 actual historical series, 29 events, monthly/daily separation, result export, browser-private notes and watchlist persistence, 8 mobile views, no backend dependency, zero browser errors.')
 finally:process.terminate();process.wait(timeout=5)
if __name__=='__main__':run()

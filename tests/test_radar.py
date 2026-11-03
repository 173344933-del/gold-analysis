import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from radar import store, ingest, server
from radar.catalog import THEMES, SOURCES
from radar.scoring import compute

NOW=datetime.now(timezone.utc)
def evidence(i,source='fed',stance='unknown',days=1,cluster=None):
 return dict(id=str(i),source=source,title='AI research '+str(i),url='https://example.org/'+str(i),published=(NOW-timedelta(days=days)).isoformat(),summary='',theme='ai',stance=stance,cluster=cluster or str(i),retrieved=NOW.isoformat())

class ScoringTests(unittest.TestCase):
 def score(self,rows):return compute(THEMES[0],rows,NOW)
 def test_missing_is_not_zero(self):
  s=self.score([]);self.assertIsNone(s['heat']);self.assertIsNone(s['consensus']);self.assertEqual(s['confidence'],0)
 def test_one_source_is_insufficient(self):
  self.assertIsNone(self.score([evidence(i) for i in range(20)])['heat'])
 def test_unknown_stance_is_not_positive_consensus(self):
  s=self.score([evidence(i,'fed' if i%2 else 'bls') for i in range(10)])
  self.assertGreater(s['heat'],0);self.assertLessEqual(s['heat'],100);self.assertIsNone(s['consensus']);self.assertIsNone(s['velocity'])
 def test_syndicated_titles_not_counted_twice(self):
  s=self.score([evidence(i,'fed' if i%2 else 'bls',cluster='same') for i in range(10)])
  self.assertEqual(s['evidence_count'],1);self.assertIsNone(s['heat'])
 def test_consensus_can_be_negative(self):
  s=self.score([evidence(i,'fed' if i%2 else 'bls','challenge') for i in range(5)])
  self.assertEqual(s['consensus'],100);self.assertEqual(s['stance_counts']['challenge'],5)
 def test_labeled_sources_need_independence(self):
  rows=[evidence(i,'fed','support') for i in range(5)]+[evidence(9,'bls')]
  self.assertIsNone(self.score(rows)['consensus'])
 def test_unknown_reprint_is_not_independent_labeled_source(self):
  rows=[evidence(i,'fed','support') for i in range(5)]+[evidence(9,'bls',cluster='1')]
  self.assertIsNone(self.score(rows)['consensus'])
 def test_future_and_old_records_excluded(self):
  s=self.score([evidence(1,days=-1),evidence(2,days=30)])
  self.assertEqual(s['evidence_count'],0)
 def test_conflicting_cluster_excluded_from_consensus(self):
  rows=[evidence(1,'fed','support',cluster='a'),evidence(2,'bls','challenge',cluster='a'),evidence(3,'fed','support')]
  self.assertIsNone(self.score(rows)['consensus'])

class StorageCase(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=store.DB_PATH;store.DB_PATH=Path(self.temp.name)/'test.db';store.init()
 def tearDown(self):store.DB_PATH=self.old;self.temp.cleanup()
 def source(self,sid):return next(s for s in SOURCES if s['id']==sid)

class DatabaseTests(StorageCase):
 def test_rss_preserves_provenance_and_is_repeatable(self):
  xml=f'<rss><channel><item><title>Artificial intelligence research</title><link>https://example.org/ai</link><pubDate>{NOW.isoformat()}</pubDate><description>New AI report</description></item><item><title>gold</title><link>https://example.org/gold</link></item></channel></rss>'
  self.assertEqual(ingest.rss(self.source('fed'),xml),1)
  self.assertEqual(ingest.rss(self.source('fed'),xml),0)
  with store.db() as c:
   r=c.execute('SELECT * FROM evidence').fetchone();self.assertEqual(r['source'],'fed');self.assertEqual(r['stance'],'unknown')
 def test_atom_parses_link_attributes(self):
  xml=f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Artificial intelligence model</title><link href="https://example.org/paper"/><published>{NOW.isoformat()}</published><summary>AI</summary></entry></feed>'
  self.assertEqual(ingest.rss(self.source('arxiv'),xml),1)
 def test_market_csv_ingests_ohlcv_not_fund_flow(self):
  with patch('radar.ingest.fetch',return_value='Date,Open,High,Low,Close,Volume\n2020-01-02,10,12,9,11,1000\n'):
   result=ingest.run_source(self.source('stooq'))
  self.assertEqual(result['status'],'ok');self.assertEqual(result['count'],15)
  with store.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM evidence').fetchone()[0],0)
 def test_worldbank_null_values_preserved_as_missing(self):
  data=[{},[{'countryiso3code':'USA','date':'2020','value':-2.2},{'countryiso3code':'CHN','date':'2021','value':None}]]
  with patch('radar.ingest.fetch',return_value=json.dumps(data)):
   result=ingest.run_source(self.source('worldbank'))
  self.assertEqual(result['count'],2)
 def test_github_is_adoption_not_news_or_funds(self):
  with patch('radar.ingest.fetch',return_value=json.dumps({'items':[{'full_name':'org/ai','stargazers_count':42,'html_url':'https://github.com/org/ai'}]})):
   self.assertEqual(ingest.run_source(self.source('github'))['count'],1)
  with store.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM evidence').fetchone()[0],0)
 def test_failure_preserves_archived_data(self):
  ingest.save_evidence('fed','Artificial intelligence report','https://example.org/a',NOW.isoformat())
  with patch('radar.ingest.fetch',side_effect=urllib.error.URLError('Tunnel connection failed: 403 Forbidden')):
   result=ingest.run_source(self.source('fed'))
  self.assertEqual(result['status'],'error');self.assertIn('403',result['message'])
  with store.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM evidence').fetchone()[0],1)
 def test_sec_13f_retains_option_type_and_filing_date(self):
  submissions={'filings':{'recent':{'form':['13F-HR'],'accessionNumber':['0001-26-001'],'filingDate':['2026-08-14'],'reportDate':['2026-06-30'],'primaryDocument':['primary_doc.xml']}}}
  directory={'directory':{'item':[{'name':'primary_doc.xml'},{'name':'holdings.xml'}]}}
  xml='<informationTable xmlns="urn:sec"><infoTable><nameOfIssuer>Example</nameOfIssuer><cusip>123</cusip><value>300</value><shrsOrPrnAmt><sshPrnamt>10</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt><putCall>CALL</putCall></infoTable></informationTable>'
  with patch('radar.ingest.fetch',side_effect=[json.dumps(submissions),json.dumps(directory),xml]),patch('radar.ingest.time.sleep'):
   self.assertEqual(ingest.run_source(self.source('funds'))['count'],1)
  with store.db() as c:
   r=c.execute('SELECT * FROM holdings').fetchone();self.assertEqual(r['put_call'],'CALL');self.assertEqual(r['period'],'2026-06-30');self.assertEqual(r['filed'],'2026-08-14')

class APITests(StorageCase):
 def setUp(self):
  super().setUp();self.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.base=f'http://127.0.0.1:{self.http.server_port}'
 def tearDown(self):self.http.shutdown();self.http.server_close();super().tearDown()
 def request(self,path,body=None,headers=None):
  data=json.dumps(body).encode() if body is not None else None
  req=urllib.request.Request(self.base+path,data=data,headers=headers or ({'Content-Type':'application/json'} if data else {}))
  try:
   with urllib.request.urlopen(req) as r:return r.status,r.read().decode()
  except urllib.error.HTTPError as e:return e.code,e.read().decode()
 def test_api_empty_state_and_health(self):
  status,text=self.request('/api/snapshot');self.assertEqual(status,200);s=json.loads(text);self.assertTrue(all(t['heat'] is None for t in s['themes']));self.assertEqual(self.request('/api/health')[0],200)
 def test_import_validation_is_atomic(self):
  rows=[{'title':'AI report','url':'https://example.org/r','published':NOW.isoformat(),'source':'research','theme':'ai'},{'title':'bad'}]
  self.assertEqual(self.request('/api/import',{'records':rows})[0],400)
  self.assertEqual(json.loads(self.request('/api/snapshot')[1])['evidence_total'],0)
 def test_import_annotation_watch_notes_export(self):
  row={'title':'Artificial intelligence research','url':'https://example.org/report','published':NOW.isoformat(),'source':'external','theme':'ai'}
  self.assertEqual(self.request('/api/import',{'records':[row]})[0],200)
  s=json.loads(self.request('/api/snapshot')[1]);eid=s['evidence'][0]['id']
  self.assertEqual(self.request('/api/annotate',{'id':eid,'stance':'challenge'})[0],200)
  self.assertEqual(self.request('/api/watchlist',{'theme':'ai','active':True})[0],200)
  self.request('/api/notes',{'theme':'ai','body':'资本回报需要核验'})
  self.assertIn('资本回报需要核验',self.request('/api/memo?theme=ai')[1])
  self.assertIn('challenge',self.request('/api/export?format=csv')[1])
  store.init();self.assertIn('ai',json.loads(self.request('/api/snapshot')[1])['watchlist'])
 def test_cross_origin_write_blocked(self):
  self.assertEqual(self.request('/api/watchlist',{'theme':'ai','active':True},{'Content-Type':'application/json','Origin':'https://evil.example'})[0],403)
 def test_scenario_validation_and_math(self):
  model={'theme':'ai','price':100,'bear':70,'base':110,'bull':150,'p_bear':25,'p_base':50,'p_bull':25}
  status,text=self.request('/api/scenario',model);self.assertEqual(status,200);self.assertEqual(json.loads(text)['expected_return'],10)
  model['p_base']=80;self.assertEqual(self.request('/api/scenario',model)[0],400)
  model['p_base']=50;model['price']=0;self.assertEqual(self.request('/api/scenario',model)[0],400)
 def test_decision_log_attaches_existing_evidence(self):
  ingest.save_evidence('fed','Artificial intelligence report','https://example.org/a',NOW.isoformat())
  self.assertEqual(self.request('/api/decision',{'theme':'ai','disposition':'补充核验','rationale':'还需要核验现金流变化'})[0],200)
  s=json.loads(self.request('/api/snapshot')[1]);self.assertEqual(len(json.loads(s['decisions'][0]['evidence_ids'])),1)
 def test_malicious_url_rejected(self):
  row={'title':'AI','url':'javascript:alert(1)','published':NOW.isoformat(),'source':'user'}
  self.assertEqual(self.request('/api/import',{'records':[row]})[0],400)
 def test_json_array_request_rejected(self):self.assertEqual(self.request('/api/notes',[])[0],400)
 def test_csv_formula_injection_neutralized(self):
  ingest.save_evidence('fed','=HYPERLINK("evil") Artificial intelligence','https://example.org/a',NOW.isoformat())
  self.assertIn("'=HYPERLINK",self.request('/api/export?format=csv')[1])

if __name__=='__main__':unittest.main()

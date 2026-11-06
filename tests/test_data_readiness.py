"""Synthetic unit fixtures only; never written into a production build."""
import copy
import http.client
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from radar import store, ingest, official_pages
from radar.catalog import THEMES, SOURCES
from radar.evidence_rules import matched_terms
from radar.scoring import rank, compute, CATALOG
from radar.readiness import assess, LIVE

NOW=datetime(2026,11,6,2,12,59,tzinfo=timezone.utc)
def row(tid,i,sid):
    return dict(id=tid+str(i),theme=tid,source=sid,title=tid+str(i),summary='',
                url='https://fixture.invalid/'+tid+str(i),published=(NOW-timedelta(days=1)).isoformat(),
                retrieved=(NOW-timedelta(hours=1)).isoformat(),cluster=tid+str(i),stance='unknown')

def ready_fixture():
    rows=[]
    for tid,sids in [('ai',['nvidia_news','azure_blog']),('china',['pbc','nbs']),('power',['nea','eia'])]:
        rows += [row(tid,i,sids[i%2]) for i in range(3)]
    sources=[dict(s,run=dict(status='ok',checked=(NOW-timedelta(hours=1)).isoformat())) for s in SOURCES]
    snapshot=dict(as_of=NOW.isoformat(),themes=rank(rows,NOW),sources=sources)
    markets=[dict(symbol=symbol,source=sid,last_date='2026-11-05',latest_metrics=dict(open=10,high=11,low=9,close=10,volume=0)) for symbol,sid in LIVE.items()]
    return snapshot,rows,markets

class ReadinessTests(unittest.TestCase):
    def test_sufficient_core_and_zero_observed_volume(self):
        self.assertEqual(assess(*ready_fixture())['status'],'core_data_ready')
    def test_missing_is_not_observed_zero(self):
        s,rows,m=ready_fixture();m[0]['latest_metrics']['volume']=None
        self.assertEqual(assess(s,rows,m)['status'],'blocked')
    def test_no_evidence_never_passes_on_history_count(self):
        s,rows,m=ready_fixture();s['themes']=rank([],NOW);s['observations']=138178
        r=assess(s,[],m)
        self.assertFalse(r['core_narratives_ready']);self.assertIsNone(r['core']['ai']['heat'])
    def test_one_failed_core_source_degrades_cached_heat(self):
        s,rows,m=ready_fixture()
        next(x for x in s['sources'] if x['id']=='pbc')['run']['status']='error'
        self.assertIsNotNone(s['themes'][0]['heat'])
        self.assertFalse(assess(s,rows,m)['core']['china']['ready'])
    def test_fake_heat_is_detected_by_replay(self):
        s,rows,m=ready_fixture();s['themes'][0]['heat']=99
        self.assertTrue(assess(s,rows,m)['integrity_failures'])
    def test_missing_score_input_is_detected(self):
        s,rows,m=ready_fixture()
        self.assertTrue(assess(s,rows[1:],m)['integrity_failures'])
    def test_old_market_data_is_not_live(self):
        s,rows,m=ready_fixture();m[0]['last_date']='2025-08-06'
        self.assertFalse(assess(s,rows,m)['live_eod_samples_ready'])
    def test_verified_last_session_can_be_required(self):
        self.assertEqual(assess(*ready_fixture(),expected_sessions={'US':'2026-11-04'})['status'],'blocked')
    def test_zero_price_is_invalid(self):
        s,rows,m=ready_fixture();m[0]['latest_metrics']['close']=0
        self.assertFalse(assess(s,rows,m)['live_eod_samples_ready'])
    def test_one_publisher_multiple_feeds_is_not_breadth(self):
        rows=[row('ai',i,'nvidia_news' if i%2 else 'nvidia_alias') for i in range(5)]
        with patch.dict(CATALOG,{'nvidia_alias':dict(publisher_group='nvidia',heat_eligible=True)}):
            r=compute(THEMES[0],rows,NOW)
        self.assertEqual(r['source_count'],1);self.assertIsNone(r['heat'])
    def test_reprints_cannot_supply_second_publisher(self):
        rows=[row('ai',i,'nvidia_news') for i in range(3)]
        duplicate=dict(rows[0],id='copy',source='azure_blog',published=(NOW-timedelta(hours=1)).isoformat())
        r=compute(THEMES[0],rows+[duplicate],NOW)
        self.assertEqual(r['source_count'],1);self.assertIsNone(r['heat'])
    def test_naive_date_is_not_assigned_host_timezone(self):
        rows=[dict(row('ai',i,'nvidia_news'),published='2026-11-05T12:00:00') for i in range(3)]
        self.assertEqual(compute(THEMES[0],rows,NOW)['evidence_count'],0)

    def test_day_precision_boundary_does_not_invent_publication_hour(self):
        r=dict(row('china',1,'nbs'),published='2026-10-30')
        score=compute(next(t for t in THEMES if t['id']=='china'),[r],NOW)
        self.assertEqual(score['evidence_count'],0)
        r['published']='2026-11-05'
        self.assertEqual(compute(next(t for t in THEMES if t['id']=='china'),[r],NOW)['evidence_count'],1)

    def test_insufficient_baseline_velocity_is_missing(self):
        rows=[row('ai',i,'fed' if i%2 else 'bls') for i in range(5)]
        rows.append(dict(row('ai',9,'fed'),published=(NOW-timedelta(days=8)).isoformat()))
        self.assertIsNone(compute(THEMES[0],rows,NOW)['velocity'])
    def test_equal_supported_samples_have_true_zero_velocity(self):
        rows=[row('ai',i,'fed' if i%2 else 'bls') for i in range(5)]
        rows += [dict(row('ai',10+i,'fed' if i%2 else 'bls'),published=(NOW-timedelta(days=8)).isoformat()) for i in range(5)]
        self.assertEqual(compute(THEMES[0],rows,NOW)['velocity'],0)
    def test_supported_decline_is_negative_not_false_zero(self):
        rows=[row('ai',i,'fed' if i%2 else 'bls') for i in range(3)]
        rows += [dict(row('ai',10+i,'fed' if i%2 else 'bls'),published=(NOW-timedelta(days=8)).isoformat()) for i in range(5)]
        self.assertEqual(compute(THEMES[0],rows,NOW)['velocity'],-40)

class RelevanceTests(unittest.TestCase):
    def theme(self,tid):return next(t for t in THEMES if t['id']==tid)
    def test_gold_answer_is_not_gold_market(self):
        self.assertFalse(matched_terms(self.theme('gold'),'Search agents','without a generative judge or gold answer'))
        self.assertTrue(matched_terms(self.theme('gold'),'Central bank gold purchases rise'))
    def test_ai_research_alone_is_not_compute_capex(self):
        self.assertFalse(matched_terms(self.theme('ai'),'Artificial intelligence agents in chemical laboratories'))
        self.assertTrue(matched_terms(self.theme('ai'),'GPU data center deployment'))
    def test_credit_terms_without_china_string_are_found(self):
        self.assertTrue(matched_terms(self.theme('china'),'9月社会融资规模存量统计'))
        self.assertTrue(matched_terms(self.theme('china'),'全国规模以上工业企业利润'))

class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.old=store.DB_PATH;store.DB_PATH=Path(self.temp.name)/'test.db';store.init()
    def tearDown(self):store.DB_PATH=self.old;self.temp.cleanup()
    def source(self,sid):return next(s for s in SOURCES if s['id']==sid)
    def count(self):
        with store.db() as c:return c.execute('SELECT count(*) FROM observations').fetchone()[0]
    def test_partial_market_failure_does_not_abort_other_symbols(self):
        with patch('radar.ingest.fetch',side_effect=['No data','Date,Open,High,Low,Close,Volume\n2026-11-04,10,11,9,10,0\n','Date,Open,High,Low,Close,Volume\n2026-11-04,10,11,9,10,5\n']):
            r=ingest.run_source(self.source('stooq'))
        self.assertEqual(r['status'],'partial');self.assertEqual(r['count'],10)
        self.assertEqual(r['details']['symbols'][0]['count'],0)
        with store.db() as c:self.assertEqual(c.execute("SELECT value FROM observations WHERE symbol='GLD.US' AND metric='volume'").fetchone()[0],0)
    def test_market_missing_values_do_not_become_zero(self):
        with patch('radar.ingest.fetch',return_value='Date,Open,High,Low,Close,Volume\n2026-11-04,10,11,9,10,\n'):
            r=ingest.run_source(self.source('stooq'))
        self.assertEqual(r['status'],'error');self.assertEqual(self.count(),0)
    def test_market_nan_and_bad_ohlc_are_rejected(self):
        for close in ['nan','200']:
            with patch('radar.ingest.fetch',return_value=f'Date,Open,High,Low,Close,Volume\n2026-11-04,10,11,9,{close},10\n'):
                self.assertEqual(ingest.run_source(self.source('stooq'))['status'],'error')
        self.assertEqual(self.count(),0)
    def test_eastmoney_wrong_symbol_is_rejected(self):
        text=json.dumps({'data':{'code':'000001','klines':['2026-11-04,10,10,11,9,0,0']}})
        with patch('radar.ingest.fetch',return_value=text):self.assertEqual(ingest.run_source(self.source('eastmoney'))['status'],'error')
        self.assertEqual(self.count(),0)
    def test_completed_bar_only_and_index_units(self):
        from radar.markets import collect
        text=json.dumps({'data':{'code':'000300','klines':['2026-11-05,10,10,11,9,0,0','2026-11-06,10,10,11,9,0,0']}})
        r=collect(self.source('eastmoney'),lambda url:text,ingest.save_observations,NOW)
        self.assertEqual(r[0]['last_date'],'2026-11-05')
        with store.db() as c:self.assertEqual(c.execute("SELECT unit FROM observations WHERE symbol='000300.SH' AND metric='close'").fetchone()[0],'index_points')
    def test_empty_no_match_and_dedup_are_different(self):
        with patch('radar.ingest.fetch',return_value='<rss><channel/></rss>'):
            self.assertEqual(ingest.run_source(self.source('fed'))['status'],'empty')
        date='2026-11-04T12:00:00+00:00'
        xml=f'<rss><channel><item><title>Unrelated fixture</title><link>https://fixture.invalid/x</link><pubDate>{date}</pubDate></item></channel></rss>'
        with patch('radar.ingest.fetch',return_value=xml):self.assertEqual(ingest.run_source(self.source('fed'))['status'],'no_match')
        xml=xml.replace('Unrelated fixture','GPU data center')
        with patch('radar.ingest.fetch',return_value=xml):
            self.assertGreater(ingest.run_source(self.source('fed'))['count'],0)
            r=ingest.run_source(self.source('fed'));self.assertEqual(r['count'],0);self.assertEqual(r['status'],'ok')
    def test_html_response_is_not_empty_success(self):
        with patch('radar.ingest.fetch',return_value='<html><body>unavailable</body></html>'):
            self.assertEqual(ingest.run_source(self.source('fed'))['status'],'error')
    def test_atom_updated_only_is_not_new_evidence(self):
        xml='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>GPU data center</title><link href="https://fixture.invalid/x"/><updated>2026-11-04T12:00:00+00:00</updated></entry></feed>'
        stats={};self.assertEqual(ingest.rss(self.source('arxiv'),xml,stats),0);self.assertEqual(stats['rejected_date'],1)
    def test_official_metadata_and_origin_required(self):
        source=self.source('nbs');url='https://www.stats.gov.cn/sj/zxfb/202610/t20261031_1965718.html'
        index=f'<a href="{url}">fixture</a>'
        html='<meta name="ArticleTitle" content="社会融资与信用"><meta name="PubDate" content="2026-10-31 09:30"><meta name="ContentSource" content="国家统计局">'
        stats={};self.assertGreater(official_pages.collect(source,index,lambda url:html,ingest.save_evidence,stats),0)
        with store.db() as c:self.assertEqual(c.execute('SELECT published FROM evidence').fetchone()[0],'2026-10-31T01:30:00+00:00')
        stats={};self.assertEqual(official_pages.collect(source,index,lambda url:html.replace('国家统计局','外部媒体'),ingest.save_evidence,stats),0)
        self.assertEqual(stats['rejected_metadata'],1)
    def test_official_date_only_is_preserved_without_fake_clock(self):
        source=self.source('nbs');index='<a href="202610/t20261031_1965718.html">fixture</a>'
        html='<meta name="ArticleTitle" content="社会融资"><meta name="PubDate" content="2026-10-31"><meta name="ContentSource" content="国家统计局">'
        stats={};self.assertGreater(official_pages.collect(source,index,lambda url:html,ingest.save_evidence,stats),0)
        self.assertEqual(stats['day_precision'],1)
        with store.db() as c:self.assertEqual(c.execute('SELECT published FROM evidence').fetchone()[0],'2026-10-31')
    def test_403_is_not_retried_or_bypassed(self):
        error=urllib.error.HTTPError('https://fixture.invalid',403,'Forbidden',{},None)
        with patch('urllib.request.urlopen',side_effect=error) as f:
            with self.assertRaises(urllib.error.HTTPError):ingest.fetch('https://fixture.invalid')
        self.assertEqual(f.call_count,1)
    def test_remote_disconnect_is_bounded(self):
        with patch('urllib.request.urlopen',side_effect=http.client.RemoteDisconnected()) as f,patch('radar.ingest.time.sleep'):
            with self.assertRaises(http.client.RemoteDisconnected):ingest.fetch('https://fixture.invalid')
        self.assertEqual(f.call_count,2)

if __name__=='__main__':unittest.main()

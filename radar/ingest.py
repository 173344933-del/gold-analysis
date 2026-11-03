"""Bounded public connectors, TLS verification intact, no synthetic fallback."""
import csv
import hashlib
import io
import json
import os
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from .catalog import SOURCES, THEMES
from .store import db

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def clean(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', str(value or ''))).strip()

def normalized_title(title):
    return re.sub(r'[^\w\u4e00-\u9fff]', '', title.casefold())

def fetch(url):
    contact=os.environ.get('RADAR_SEC_CONTACT','').strip()
    agent='NarrativeRadar/1.0 public-research-tool'+(' '+contact if contact else '')
    req=urllib.request.Request(url, headers={'User-Agent':agent,'Accept':'application/json, application/xml, text/xml, text/csv, */*'})
    with urllib.request.urlopen(req,timeout=18) as response:
        data=response.read(8_000_001)
        if len(data)>8_000_000:
            raise ValueError('响应超过8MB限制；需要分页')
        return data.decode('utf-8-sig')

def canonical_date(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,AttributeError):
        try: d=parsedate_to_datetime(value)
        except (ValueError,TypeError): return None
    if not d.tzinfo: d=d.replace(tzinfo=timezone.utc)
    if d > datetime.now(timezone.utc): return None
    return d.astimezone(timezone.utc).isoformat()

def save_evidence(source,title,url,published,summary='',stance='unknown',theme=None):
    published=canonical_date(published)
    if not published or not title or not url.startswith(('https://','http://')): return 0
    if stance not in ('support','challenge','unknown'): raise ValueError('stance必须为support/challenge/unknown')
    title=clean(title)[:1000]; summary=clean(summary)[:4000]
    matching=[t['id'] for t in THEMES if any(k in (title+' '+summary).casefold() for k in t['terms'])]
    if theme:
        if theme not in {t['id'] for t in THEMES}: raise ValueError('未知主题')
        matching=[theme]
    cluster=hashlib.sha256(normalized_title(title).encode()).hexdigest()[:24]
    count=0
    with db() as c:
        for tid in matching:
            key=hashlib.sha256((url+'|'+tid).encode()).hexdigest()
            count+=c.execute('INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?)',
                (key,source,title,url,published,summary,tid,stance,cluster,utcnow())).rowcount
    return count

def save_observations(source, rows):
    with db() as c:
        c.executemany('INSERT OR REPLACE INTO observations VALUES (?,?,?,?,?,?,?,?)',
            [(source,*r,utcnow()) for r in rows])
    return len(rows)

def rss(source,text):
    root=ET.fromstring(text)
    count=0
    for item in list(root.findall('.//item'))+list(root.findall('.//{http://www.w3.org/2005/Atom}entry')):
        def val(name):
            return item.findtext(name) or item.findtext('{http://www.w3.org/2005/Atom}'+name) or ''
        link=val('link')
        if not link:
            links=item.findall('{http://www.w3.org/2005/Atom}link')
            link=next((x.get('href','') for x in links if x.get('rel','alternate')=='alternate'),'')
        count+=save_evidence(source['id'],val('title'),link,val('pubDate') or val('published') or val('updated'),val('description') or val('summary'))
    return count

def run_source(source):
    sid=source['id']; count=0
    try:
        if source['kind']=='reference': return dict(source=sid,status='reference',count=0)
        if source['kind']=='bundled':
            from .history import manifest,series
            for meta in manifest()['series']:
                if meta['source']!=sid:continue
                _,bars=series(meta['symbol'])
                metric='monthly_average' if meta['frequency']=='monthly_average' else 'close'
                records=[]
                for bar in bars:
                    records.append((meta['symbol'],bar['date'],metric,bar['close'],meta['unit'],source['url']))
                    if bar['volume'] is not None:records.append((meta['symbol'],bar['date'],'volume',bar['volume'],'upstream_units',source['url']))
                count+=save_observations(sid,records)
            with db() as c:
                bounds=c.execute('SELECT min(date),max(date) FROM observations WHERE source=?',(sid,)).fetchone()
                c.execute('INSERT OR REPLACE INTO source_runs VALUES (?,?,?,?,?,?,?)',(sid,'ok',count,'本地固定提交历史文件校验通过；不是实时数据连接',utcnow(),bounds[0],bounds[1]))
            return dict(source=sid,status='ok',count=count)
        text=fetch(source['url'])
        if source['kind'] in ('rss','atom'): count=rss(source,text)
        elif source['kind']=='github':
            for r in json.loads(text).get('items',[]):
                # Repository edits are not independent news or investment decisions.
                count+=save_observations(sid,[(r['full_name'],utcnow()[:10],'stars',r['stargazers_count'],'stars',r['html_url'])])
        elif source['kind']=='worldbank':
            for metric,code in [('gdp_growth','NY.GDP.MKTP.KD.ZG'),('inflation','FP.CPI.TOTL.ZG')]:
                url=source['url'].replace('NY.GDP.MKTP.KD.ZG',code)
                data=json.loads(text if metric=='gdp_growth' else fetch(url))
                if len(data)<2 or not isinstance(data[1],list): raise ValueError('World Bank响应无数据列表')
                count+=save_observations(sid,[(r['countryiso3code'],r['date']+'-12-31',metric,r['value'],'%',url) for r in data[1] if r['value'] is not None])
        elif source['kind']=='stooq':
            for symbol in ['spy.us','gld.us','nvda.us']:
                url=source['url'].replace('spy.us',symbol)
                data=list(csv.DictReader(io.StringIO(text if symbol=='spy.us' else fetch(url))))
                if not data or 'Close' not in data[0]: raise ValueError('未返回有效OHLCV；供应商可能限制访问')
                rows=[]
                for r in data:
                    if r['Date']>utcnow()[:10]: continue
                    for metric in ['Open','High','Low','Close','Volume']:
                        if r.get(metric): rows.append((symbol.upper(),r['Date'],metric.lower(),float(r[metric]),'shares' if metric=='Volume' else 'USD',url))
                count+=save_observations(sid,rows)
        elif source['kind']=='eastmoney':
            for symbol,secid in [('000300.SH','1.000300'),('600547.SH','1.600547')]:
                url=source['url'].replace('1.000300',secid)
                data=json.loads(text if secid=='1.000300' else fetch(url)).get('data')
                if not data or not data.get('klines'): raise ValueError('未返回K线数据')
                rows=[]
                for line in data['klines']:
                    parts=line.split(',')
                    for i,metric,unit in [(1,'open','CNY'),(2,'close','CNY'),(3,'high','CNY'),(4,'low','CNY'),(5,'volume','lots'),(6,'turnover','CNY')]:
                        rows.append((symbol,parts[0],metric,float(parts[i]),unit,url))
                count+=save_observations(sid,rows)
        elif source['kind']=='sec13f':
            recent=json.loads(text)['filings']['recent']
            idx=next((i for i,f in enumerate(recent['form']) if f=='13F-HR'),None)
            if idx is None: raise ValueError('近期列表中无13F-HR')
            accession=recent['accessionNumber'][idx].replace('-','')
            filed=recent['filingDate'][idx]
            period=recent['reportDate'][idx]
            base=f'https://www.sec.gov/Archives/edgar/data/1067983/{accession}/'
            time.sleep(.2)
            directory=json.loads(fetch(base+'index.json'))['directory']['item']
            # Never guess an XML filename or interpret the cover page as holdings.
            candidates=[r['name'] for r in directory if r['name'].lower().endswith('.xml') and r['name']!=recent['primaryDocument'][idx] and '/' not in r['name']]
            records=[]
            for name in candidates[:6]:
                time.sleep(.2)
                root=ET.fromstring(fetch(base+name))
                for item in root.iter():
                    if item.tag.split('}')[-1]!='infoTable': continue
                    def field(key):
                        return next((e.text for e in item.iter() if e.tag.split('}')[-1]==key),'')
                    key=hashlib.sha256((accession+ET.tostring(item,encoding='unicode')).encode()).hexdigest()
                    records.append((key,'Berkshire Hathaway',period,filed,clean(field('nameOfIssuer')),field('cusip'),float(field('sshPrnamt')),field('sshPrnamtType'),field('putCall'),float(field('value')),base+name,utcnow()))
                if records: break
            if not records: raise ValueError('未找到可解析的13F信息表')
            with db() as c: c.executemany('INSERT OR REPLACE INTO holdings VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',records)
            count=len(records)
        with db() as c:
            bounds=c.execute('SELECT min(date),max(date) FROM observations WHERE source=?',(sid,)).fetchone()
            if not bounds[0]: bounds=c.execute('SELECT min(published),max(published) FROM evidence WHERE source=?',(sid,)).fetchone()
            c.execute('INSERT OR REPLACE INTO source_runs VALUES (?,?,?,?,?,?,?)',(sid,'ok',count,'请求成功；数量为本次写入，历史范围见实际记录',utcnow(),bounds[0],bounds[1]))
        return dict(source=sid,status='ok',count=count)
    except Exception as e:
        # Do not log response bodies or proxy/credential URLs.
        if isinstance(e,urllib.error.HTTPError): message=f'HTTP {e.code}：需检查供应商授权、频率或网络策略'
        elif isinstance(e,urllib.error.URLError):
            message='代理拒绝目标域名（HTTP 403）：请在环境设置中保存网络白名单变更' if '403' in str(e.reason) else '连接失败：请检查代理、TLS证书或供应商状态；未生成替代数据'
        else: message=f'{type(e).__name__}：响应解析失败或格式变化'
        with db() as c:
            c.execute('INSERT OR REPLACE INTO source_runs VALUES (?,?,?,?,?,?,?)',(sid,'error',count,message,utcnow(),None,None))
        return dict(source=sid,status='error',count=count,message=message)

def refresh():
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(run_source,[s for s in SOURCES if s['kind']!='reference']))

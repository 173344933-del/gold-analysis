"""Local research service. Python standard library only. Run: python3 -m radar.server."""
import argparse
import csv
import io
import json
import mimetypes
import math
import threading
import uuid
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .catalog import SOURCES, THEMES
from .ingest import refresh, save_evidence, utcnow
from .scoring import rank, VERSION
from .store import db, init

ROOT=Path(__file__).resolve().parent.parent
LOCK=threading.Lock()

def snapshot():
    from .history import manifest, EVENTS
    with db() as c:
        rows=[dict(r) for r in c.execute('SELECT * FROM evidence ORDER BY published DESC')]
        runs={r['source']:dict(r) for r in c.execute('SELECT * FROM source_runs')}
        watches=[r[0] for r in c.execute('SELECT theme FROM watchlist')]
        counts={r['source']:dict(r) for r in c.execute('SELECT source,count(*) records,min(date) first_date,max(date) last_date FROM observations GROUP BY source')}
        notes={r['theme']:dict(r) for r in c.execute('SELECT * FROM notes')}
        decisions=[dict(r) for r in c.execute('SELECT * FROM decisions ORDER BY created DESC LIMIT 100')]
        scenarios={r['theme']:json.loads(r['model']) for r in c.execute('SELECT * FROM scenarios')}
        job=c.execute('SELECT * FROM jobs ORDER BY started DESC LIMIT 1').fetchone()
    sources=[]
    for source in SOURCES:
        s=dict(source)
        s['run']=runs.get(s['id'],dict(status='reference' if s['kind']=='reference' else 'unverified',count=0))
        s['observations']=counts.get(s['id'])
        s['stored_evidence']=sum(r['source']==s['id'] for r in rows)
        sources.append(s)
    return dict(as_of=utcnow(),themes=rank(rows),sources=sources,watchlist=watches,notes=notes,
        evidence=rows[:500],evidence_total=len(rows),observations=sum(r['records'] for r in counts.values()),
        job=dict(job) if job else None,methodology_version=VERSION,decisions=decisions,scenarios=scenarios,
        history_summary=dict(series=len(manifest()['series']),events=len(EVENTS),first=min(r['first'] for r in manifest()['series'])),
        limitations=['热度是已采集样本的关注强度，不是收益预测或全市场新闻覆盖率。',
          '来源广度按发布平台计数，不保证原始信源独立；去重仅识别标准化同标题。',
          '共识需要人工标注支持／反证；报道提及不自动等于支持。',
          '年度宏观值以观察期标识，未保留全部初值与发布日期，不可用于无前视偏差回测。',
          '成交量、成交额、GitHub stars均不等同资金净流入；没有真实交易执行或机构内部决策数据。'])

def scenario_result(data):
    keys=['price','bear','base','bull','p_bear','p_base','p_bull']
    if any(isinstance(data.get(k),bool) or not isinstance(data.get(k),(float,int)) or not math.isfinite(data[k]) for k in keys):
        raise ValueError('请完整填写有限数值')
    if data['price']<=0 or min(data[k] for k in ['bear','base','bull'])<0: raise ValueError('参考价格须大于0，目标价格不能为负')
    if not data['bear']<=data['base']<=data['bull']: raise ValueError('目标价须满足：熊市 ≤ 基准 ≤ 牛市')
    if min(data[k] for k in ['p_bear','p_base','p_bull'])<0 or abs(sum(data[k] for k in ['p_bear','p_base','p_bull'])-100)>.001: raise ValueError('情景概率须非负且合计100%')
    expected=sum(data[k]*data['p_'+k]/100 for k in ['bear','base','bull'])
    return {**{k:data[k] for k in keys},'expected_price':round(expected,4),
      'expected_return':round((expected/data['price']-1)*100,2),
      'bear_return':round((data['bear']/data['price']-1)*100,2),
      'bull_return':round((data['bull']/data['price']-1)*100,2),
      'assumption':'所有输入均为研究员主观假设，非一致预期；未计交易成本、分红与时间价值', 'updated':utcnow()}

def market_data(symbol):
    with db() as c:
        rows=[dict(r) for r in c.execute('SELECT * FROM observations WHERE symbol=? ORDER BY date,metric',(symbol,))]
    return dict(symbol=symbol,rows=rows)

def memo(tid):
    s=snapshot(); t=next(t for t in s['themes'] if t['id']==tid)
    evidence=[r for r in s['evidence'] if r['theme']==tid][:20]
    display=lambda v:'证据不足' if v is None else str(v)
    return '\n'.join([f"# {t['name']} · 研究备忘录",f"\n生成时间：{s['as_of']} | 方法 v{VERSION}",
       f"\n热度：{display(t['heat'])}/100 · 共识：{display(t['consensus'])}/100 · 证据置信度：{t['confidence']}/100",
       f"\n## 核心问题\n{t['thesis']}",f"\n## 观察标的（研究映射，非推荐）\n{', '.join(t['tickers'])}",
       f"\n## 证实条件\n{t['confirm']}",f"\n## 失效条件\n{t['invalidate']}",
       '\n## 证据账本（自动分类需人工复核）',
       *[f"- {r['published'][:10]} [{r['title']}]({r['url']}) · {r['source']} · {r['stance']}" for r in evidence],
       '\n## 研究员笔记\n'+s['notes'].get(tid,{}).get('body','尚未填写。'),
       '\n## 主观情景模型\n'+json.dumps(s['scenarios'].get(tid,{}),ensure_ascii=False,indent=2),
       '\n## 判断日志（最近100条工作区记录中的本主题记录）',
       *[f"- {d['created']} · {d['disposition']} · {d['rationale']} · 关联证据ID：{d['evidence_ids']}" for d in s['decisions'] if d['theme']==tid],
       '\n## 数据限制',*['- '+v for v in s['limitations']]])

class Handler(BaseHTTPRequestHandler):
    server_version='NarrativeRadar/1.0'
    def reply(self,data,status=200,content_type='application/json; charset=utf-8',filename=None):
        body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if content_type.startswith('application/json') else data.encode() if isinstance(data,str) else data
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path; q=parse_qs(parsed.query)
        if path=='/api/health': return self.reply(dict(status='ok',time=utcnow(),version=VERSION))
        if path=='/api/snapshot': return self.reply(snapshot())
        if path=='/api/market': return self.reply(market_data(q.get('symbol',['SPY.US'])[0]))
        if path=='/api/history':
            from .history import overview
            return self.reply(overview(q.get('symbol',['000001.SH'])[0]))
        if path=='/api/observed-symbols':
            with db() as c: symbols=[dict(r) for r in c.execute('SELECT symbol,source,count(*) records,min(date) first_date,max(date) last_date,group_concat(DISTINCT metric) metrics FROM observations GROUP BY symbol,source')]
            return self.reply(symbols)
        if path=='/api/holdings':
            with db() as c: rows=[dict(r) for r in c.execute('SELECT * FROM holdings ORDER BY filed DESC,reported_value DESC LIMIT 200')]
            return self.reply(dict(rows=rows,note='13F仅含披露范围内持仓；不是完整组合或当日仓位。value按原文数值展示，未统一历史美元/千美元口径，不用于跨期金额比较。PUT/CALL与股数类型单独保留。'))
        if path=='/api/export':
            fmt=q.get('format',['json'])[0]
            if fmt=='csv':
                with db() as c: rows=[dict(r) for r in c.execute('SELECT * FROM evidence ORDER BY published DESC')]
                out=io.StringIO(); fields=['id','source','theme','title','url','published','summary','stance','cluster','retrieved']
                writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader()
                # Prevent spreadsheet formula injection in analyst exports.
                for row in rows: writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()})
                return self.reply('\ufeff'+out.getvalue(),content_type='text/csv; charset=utf-8',filename='evidence.csv')
            return self.reply(snapshot(),filename='narrative-radar.json')
        if path=='/api/memo':
            tid=q.get('theme',[''])[0]
            if tid not in {t['id'] for t in THEMES}: return self.reply({'error':'未知主题'},404)
            return self.reply(memo(tid),content_type='text/markdown; charset=utf-8',filename=f'{tid}-memo.md')
        files={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/favicon.svg':'favicon.svg'}
        if path=='/favicon.ico': return self.reply(b'',204,'image/x-icon')
        if path in files:
            file=ROOT/'web'/files[path]
            return self.reply(file.read_bytes(),content_type=mimetypes.guess_type(str(file))[0]+'; charset=utf-8')
        return self.reply({'error':'not found'},404)

    def do_POST(self):
        origin=self.headers.get('Origin')
        if origin and urlparse(origin).netloc!=self.headers.get('Host'):
            return self.reply({'error':'跨来源写入被拒绝'},403)
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            return self.reply({'error':'只接受application/json'},415)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<0 or size>2_000_000: return self.reply({'error':'请求过大'},413)
            data=json.loads(self.rfile.read(size) or b'{}')
            if not isinstance(data,dict): raise ValueError('请求必须为JSON对象')
            path=urlparse(self.path).path
            if path=='/api/refresh':
                if not LOCK.acquire(blocking=False): return self.reply({'error':'已有采集任务正在运行'},409)
                jid=uuid.uuid4().hex
                with db() as c: c.execute('INSERT INTO jobs VALUES (?,?,?,?,?)',(jid,'running',utcnow(),None,None))
                def job():
                    try:
                        result=refresh()
                        with db() as c: c.execute('UPDATE jobs SET status=?,ended=?,result=? WHERE id=?',('completed',utcnow(),json.dumps(result),jid))
                    except Exception:
                        with db() as c: c.execute('UPDATE jobs SET status=?,ended=? WHERE id=?',('failed',utcnow(),jid))
                    finally: LOCK.release()
                threading.Thread(target=job,daemon=True).start()
                return self.reply({'id':jid,'status':'running'},202)
            if path in ('/api/watchlist','/api/notes'):
                tid=data.get('theme')
                if tid not in {t['id'] for t in THEMES}: raise ValueError('未知主题')
                with db() as c:
                    if path=='/api/watchlist':
                        if data.get('active'): c.execute('INSERT OR IGNORE INTO watchlist VALUES (?,?)',(tid,utcnow()))
                        else: c.execute('DELETE FROM watchlist WHERE theme=?',(tid,))
                    else:
                        body=data.get('body','')
                        if not isinstance(body,str) or len(body)>20000: raise ValueError('笔记上限20000字符')
                        c.execute('INSERT OR REPLACE INTO notes VALUES (?,?,?)',(tid,body,utcnow()))
                return self.reply({'status':'saved'})
            if path=='/api/annotate':
                stance=data.get('stance')
                if stance not in ('support','challenge','unknown'): raise ValueError('无效立场')
                with db() as c:
                    changed=c.execute('UPDATE evidence SET stance=? WHERE id=?',(stance,data.get('id'))).rowcount
                return self.reply({'status':'saved'} if changed else {'error':'证据不存在'},200 if changed else 404)
            if path in ('/api/decision','/api/scenario'):
                tid=data.get('theme')
                if tid not in {t['id'] for t in THEMES}: raise ValueError('未知主题')
                if path=='/api/scenario':
                    model=scenario_result(data)
                    with db() as c: c.execute('INSERT OR REPLACE INTO scenarios VALUES (?,?,?)',(tid,json.dumps(model),utcnow()))
                    return self.reply(model)
                disposition=data.get('disposition')
                if disposition not in ['观察','补充核验','进入估值','暂缓','假设失效']: raise ValueError('无效研究状态')
                rationale=data.get('rationale','')
                if not isinstance(rationale,str) or not 5<=len(rationale)<=5000: raise ValueError('请填写5–5000字的判断依据')
                with db() as c:
                    ids=[r[0] for r in c.execute('SELECT id FROM evidence WHERE theme=? ORDER BY published DESC LIMIT 50',(tid,))]
                    c.execute('INSERT INTO decisions VALUES (?,?,?,?,?,?)',(uuid.uuid4().hex,tid,disposition,rationale,json.dumps(ids),utcnow()))
                return self.reply({'status':'saved','evidence_links':len(ids)})
            if path=='/api/import':
                rows=data.get('records')
                if not isinstance(rows,list) or not 1<=len(rows)<=1000: raise ValueError('请提供1–1000条records')
                # Validate all records before writing any of them.
                from .ingest import canonical_date
                for r in rows:
                    if not isinstance(r,dict) or not all(isinstance(r.get(k),str) and r[k].strip() for k in ['title','url','published','source']): raise ValueError('每条记录需要title,url,published,source')
                    if not canonical_date(r['published']): raise ValueError('日期无效或位于未来')
                    if not r['url'].startswith(('https://','http://')): raise ValueError('来源URL仅支持http/https')
                    if r.get('theme') not in [None]+[t['id'] for t in THEMES]: raise ValueError('未知主题')
                    if r.get('stance','unknown') not in ('support','challenge','unknown'): raise ValueError('立场无效')
                count=sum(save_evidence('import:'+r['source'][:100],r['title'],r['url'],r['published'],r.get('summary',''),r.get('stance','unknown'),r.get('theme')) for r in rows)
                return self.reply({'status':'saved','inserted':count,'message':'导入内容为用户提供，权威度按未核验来源处理；自动分类需复核'})
            return self.reply({'error':'not found'},404)
        except (ValueError,TypeError,KeyError) as e:
            return self.reply({'error':str(e)[:200]},400)
        except Exception:
            return self.reply({'error':'操作失败，请检查服务器日志与数据库状态'},500)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8088)
    args=parser.parse_args(); init()
    from .ingest import run_source
    for source in SOURCES:
        if source['kind']=='bundled': run_source(source)
    print(f'Narrative Radar running on {args.host}:{args.port}',flush=True)
    ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()

if __name__=='__main__': main()

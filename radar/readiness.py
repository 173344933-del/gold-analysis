"""Recompute from a complete public score ledger; structural success is separate."""
from datetime import timedelta
import math
from urllib.parse import urlsplit
from .scoring import rank, parse_date, evidence_interval
from .catalog import SOURCES

CORE = ('ai','china','power')
LIVE = {'SPY.US':'stooq','GLD.US':'stooq','NVDA.US':'stooq',
        '000300.SH':'eastmoney','600547.SH':'eastmoney'}

def assess(snapshot, ledger, markets, expected_sessions=None):
    now = parse_date(snapshot['as_of'])
    if now is None: raise ValueError('invalid_as_of')
    failures = []
    ids = [r.get('id') for r in ledger]
    if len(ids)!=len(set(ids)): failures.append('duplicate_ledger_ids')
    for row in ledger:
        if (not all(row.get(k) for k in ('id','source','title','url','published','cluster','retrieved','theme'))
                or urlsplit(row['url']).scheme not in ('https','http')
                or evidence_interval(row) is None
                or evidence_interval(row)[1]>now
                or parse_date(row['retrieved']) is None
                or parse_date(row['retrieved'])>now):
            failures.append('invalid_provenance:'+str(row.get('id')))
    actual = {t['id']:t for t in rank(ledger,now)}
    exported = {t['id']:t for t in snapshot['themes']}
    runs = {s['id']:s.get('run',{}) for s in snapshot['sources']}
    catalog = {s['id']:s for s in SOURCES}
    for tid,score in actual.items():
        claimed=exported.get(tid,{})
        for field in ('heat','consensus','confidence','evidence_count','source_count','components','formula_version','audit'):
            if claimed.get(field)!=score[field]: failures.append('score_replay_mismatch:'+tid+':'+field)
    core = {}
    for tid in CORE:
        score = actual[tid]; claimed = exported.get(tid,{})
        for field in ('heat','evidence_count','source_count','components','formula_version'):
            if claimed.get(field)!=score[field]: failures.append('score_replay_mismatch:'+tid+':'+field)
        healthy_publishers = set()
        for row in ledger:
            if row['id'] not in score['audit']['current_ids']: continue
            run = runs.get(row['source'],{})
            checked = parse_date(run.get('checked'))
            if run.get('status')=='ok' and checked and now-timedelta(hours=36)<=checked<=now:
                healthy_publishers.add(catalog.get(row['source'],{}).get('publisher_group',row['source']))
        reasons = list(score['reason_codes'])
        if len(healthy_publishers)<2: reasons.append('insufficient_fresh_healthy_publishers')
        core[tid] = dict(ready=not reasons, reasons=reasons, clusters=score['evidence_count'],
                         publishers=score['source_count'],heat=score['heat'])
    market_checks = {}
    for symbol,sid in LIVE.items():
        data = next((r for r in markets if r['symbol']==symbol and r['source']==sid),None)
        run = runs.get(sid,{})
        reasons = []
        if run.get('status')!='ok': reasons.append('source_failure')
        checked=parse_date(run.get('checked'))
        if not checked or not now-timedelta(hours=36)<=checked<=now: reasons.append('stale_source_check')
        if data is None:
            reasons.append('missing_market_data')
        else:
            # A four-calendar-day stale guard is not an exchange calendar.
            end = parse_date(data['last_date']+'T00:00:00+00:00')
            if end is None or end>now or (now.date()-end.date()).days>4: reasons.append('stale_or_invalid_market_date')
            expected = (expected_sessions or {}).get('US' if symbol.endswith('.US') else 'CN')
            if expected and data['last_date']!=expected: reasons.append('unexpected_last_session')
            if not {'open','high','low','close','volume'}.issubset(data['latest_metrics']): reasons.append('missing_market_fields')
            for metric,value in data['latest_metrics'].items():
                if (not isinstance(value,(float,int)) or isinstance(value,bool) or not math.isfinite(value)
                        or (value<=0 if metric in ('open','high','low','close') else value<0)):
                    reasons.append('invalid_market_value:'+metric)
        market_checks[symbol] = dict(ready=not reasons,reasons=reasons,last_date=data['last_date'] if data else None)
    narrative_ready = all(r['ready'] for r in core.values())
    market_ready = all(r['ready'] for r in market_checks.values())
    return dict(status='core_data_ready' if narrative_ready and market_ready and not failures else 'blocked',
                core_narratives_ready=narrative_ready,live_eod_samples_ready=market_ready,
                scored_themes=sum(t['heat'] is not None for t in actual.values()),total_themes=len(actual),
                core=core,markets=market_checks,integrity_failures=sorted(set(failures)),
                scope='三个核心主题与五个日线样本；通过不代表全市场覆盖、经济周期评分或投资预测有效',
                market_freshness_policy='最多4个日历日；可用expected_sessions指定已核实的最近交易日')

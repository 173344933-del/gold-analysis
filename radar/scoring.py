"""Versioned, reproducible descriptive metrics, not predictive trading signals."""
import math
import re
from zoneinfo import ZoneInfo
from collections import Counter
from datetime import datetime, timezone, timedelta
from .catalog import SOURCES, THEMES

VERSION = '1.1.0'
CATALOG = {s['id']:s for s in SOURCES}
from .evidence_rules import publisher, matched_terms
AUTHORITY = {s['id']: s['authority'] for s in SOURCES}

def parse_date(value):
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError, AttributeError):
        return None

def evidence_interval(row):
    value=row['published']
    if isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        zone=CATALOG.get(row['source'],{}).get('publication_timezone')
        if not zone:return None
        try: start=datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(zone)).astimezone(timezone.utc)
        except ValueError:return None
        return start,start+timedelta(days=1)
    d=parse_date(value)
    return (d,d) if d else None

def compute(theme, rows, now=None):
    now = now or datetime.now(timezone.utc)
    # One item per cross-source title cluster; distinct sources retained for breadth.
    recent = [r for r in rows if CATALOG.get(r['source'],{}).get('heat_eligible',True) and (bounds := evidence_interval(r)) and now-timedelta(days=14) <= bounds[0] and bounds[1] <= now]
    current = [r for r in recent if evidence_interval(r)[0] >= now-timedelta(days=7)]
    previous = [r for r in recent if evidence_interval(r)[1] < now-timedelta(days=7)]
    clusters = {r['cluster'] for r in current}
    prev_clusters = {r['cluster'] for r in previous}
    # Same-title reprints contribute only one publisher and one freshness weight.
    representatives = {}
    for r in sorted(current,key=lambda r:(r['published'],publisher(r['source'],CATALOG),r['id'])):
        representatives.setdefault(r['cluster'],r)
    sources = {publisher(r['source'],CATALOG) for r in representatives.values()}
    n = len(clusters)
    quality = sum(max(AUTHORITY.get(r['source'],.4) for r in representatives.values() if publisher(r['source'],CATALOG)==s) for s in sources)/max(1,len(sources))
    breadth = min(1, len(sources)/5)
    activity = min(1, math.log1p(n)/math.log(51))
    freshness = sum(math.exp(-(now-evidence_interval(r)[0]).total_seconds()/86400/3) for r in representatives.values())/len(representatives) if representatives else None
    eligible = n >= 3 and len(sources) >= 2
    previous_representatives={}
    for r in sorted(previous,key=lambda r:(r['published'],publisher(r['source'],CATALOG),r['id'])):
        previous_representatives.setdefault(r['cluster'],r)
    previous_publishers={publisher(r['source'],CATALOG) for r in previous_representatives.values()}
    baseline_eligible=len(prev_clusters)>=3 and len(previous_publishers)>=2
    velocity=min(1,max(-1,(n-len(prev_clusters))/max(5,len(prev_clusters)))) if eligible and baseline_eligible else None
    # Avoid fabricating a baseline where prior coverage is missing.
    heat = round(100*(.55*activity+.25*breadth+.20*freshness)) if eligible else None
    stance_by_cluster = {}
    for r in current:
        if r['stance'] in ('support','challenge'):
            stance_by_cluster.setdefault(r['cluster'],set()).add(r['stance'])
    labeled = [next(iter(v)) for v in stance_by_cluster.values() if len(v)==1]
    counts = Counter(labeled)
    labeled_sources = {publisher(r['source'],CATALOG) for r in current if r['stance'] in ('support','challenge') and r['cluster'] in stance_by_cluster and len(stance_by_cluster[r['cluster']])==1}
    consensus = round(100*max(counts.values())/len(labeled)) if len(labeled)>=3 and len(labeled_sources)>=2 else None
    confidence = round(100*quality*breadth*min(1,n/15)) if current else 0
    latest = max((r['published'] for r in current), default=None)
    reasons=[]
    if not n: reasons.append('no_recent_evidence')
    if n<3: reasons.append('insufficient_evidence_clusters')
    if len(sources)<2: reasons.append('insufficient_publishers')
    audit=dict(as_of=now.isoformat(),window_start=(now-timedelta(days=7)).isoformat(),
               baseline_start=(now-timedelta(days=14)).isoformat(),min_clusters=3,min_publishers=2,baseline_eligible=baseline_eligible,
               weights=dict(activity=.55,breadth=.25,freshness=.20),
               date_policy='day-only: whole local day inside window; freshness uses interval start',
               publisher_groups=sorted(sources),input_ids=sorted(r['id'] for r in recent),
               current_ids=sorted(r['id'] for r in current),
               representative_ids=sorted(r['id'] for r in representatives.values()))
    return dict(**theme, heat=heat, heat_status='available' if eligible else 'insufficient_evidence',
                reason_codes=reasons, audit=audit, consensus=consensus, confidence=confidence,
                evidence_count=n, source_count=len(sources), latest=latest,
                velocity=round(velocity*100) if velocity is not None else None,
                stance_counts=dict(counts), labeled_count=len(labeled),
                stage='证据不足' if heat is None else ('高关注' if heat>=70 else '扩散中' if heat>=40 else '低关注'),
                components=dict(activity=round(activity*100),breadth=round(breadth*100),freshness=round(freshness*100) if freshness is not None else None),
                formula_version=VERSION)

def rank(rows, now=None):
    return sorted([compute(t,[r for r in rows if r['theme']==t['id']],now) for t in THEMES],
                  key=lambda t:(t['heat'] is not None,t['heat'] or 0,t['evidence_count']),reverse=True)

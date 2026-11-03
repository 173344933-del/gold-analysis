"""Versioned, reproducible descriptive metrics, not predictive trading signals."""
import math
from collections import Counter
from datetime import datetime, timezone, timedelta
from .catalog import SOURCES, THEMES

VERSION = '1.0.0'
AUTHORITY = {s['id']: s['authority'] for s in SOURCES}

def parse_date(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None

def compute(theme, rows, now=None):
    now = now or datetime.now(timezone.utc)
    # One item per cross-source title cluster; distinct sources retained for breadth.
    recent = [r for r in rows if (d := parse_date(r['published'])) and now-timedelta(days=14) <= d <= now]
    current = [r for r in recent if parse_date(r['published']) >= now-timedelta(days=7)]
    previous = [r for r in recent if parse_date(r['published']) < now-timedelta(days=7)]
    clusters = {r['cluster'] for r in current}
    prev_clusters = {r['cluster'] for r in previous}
    sources = {r['source'] for r in current}
    n = len(clusters)
    quality = sum(AUTHORITY.get(s, .4) for s in sources)/max(1,len(sources))
    breadth = min(1, len(sources)/5)
    activity = min(1, math.log1p(n)/math.log(51))
    velocity = min(1, max(0, (n-len(prev_clusters))/max(5,len(prev_clusters)))) if prev_clusters else None
    freshness = sum(math.exp(-(now-parse_date(r['published'])).total_seconds()/86400/3) for r in current)/max(1,len(current))
    eligible = n >= 3 and len(sources) >= 2
    # Avoid fabricating a baseline where prior coverage is missing.
    heat = round(100*(.55*activity+.25*breadth+.20*freshness)) if eligible else None
    stance_by_cluster = {}
    for r in current:
        if r['stance'] in ('support','challenge'):
            stance_by_cluster.setdefault(r['cluster'],set()).add(r['stance'])
    labeled = [next(iter(v)) for v in stance_by_cluster.values() if len(v)==1]
    counts = Counter(labeled)
    labeled_sources = {r['source'] for r in current if r['stance'] in ('support','challenge') and r['cluster'] in stance_by_cluster and len(stance_by_cluster[r['cluster']])==1}
    consensus = round(100*max(counts.values())/len(labeled)) if len(labeled)>=3 and len(labeled_sources)>=2 else None
    confidence = round(100*quality*breadth*min(1,n/15)) if current else 0
    latest = max((r['published'] for r in current), default=None)
    return dict(**theme, heat=heat, consensus=consensus, confidence=confidence,
                evidence_count=n, source_count=len(sources), latest=latest,
                velocity=round(velocity*100) if velocity is not None else None,
                stance_counts=dict(counts), labeled_count=len(labeled),
                stage='证据不足' if heat is None else ('高关注' if heat>=70 else '扩散中' if heat>=40 else '低关注'),
                components=dict(activity=round(activity*100),breadth=round(breadth*100),freshness=round(freshness*100)),
                formula_version=VERSION)

def rank(rows, now=None):
    return sorted([compute(t,[r for r in rows if r['theme']==t['id']],now) for t in THEMES],
                  key=lambda t:(t['heat'] is not None,t['heat'] or 0,t['evidence_count']),reverse=True)

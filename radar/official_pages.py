"""Bounded official index adapter. Unknown origin or publication time is rejected."""
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []; self.meta = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'meta':
            self.meta[(attrs.get('name') or attrs.get('property') or '').casefold()] = attrs.get('content', '')

def collect(source, text, fetch, save, stats):
    page = Page(text)
    urls = []
    for href in page.links:
        url = urljoin(source['url'], href).split('#')[0]
        if (urlsplit(url).hostname in source['article_hosts']
                and re.search(source['article_pattern'], urlsplit(url).path)
                and url not in urls):
            urls.append(url)
    if not urls:
        raise ValueError('official_index_no_article_links')
    urls.sort(key=lambda u:max(re.findall(r'20\d{6}',u) or ['']),reverse=True)
    stats['seen'] = len(urls)
    inserted = 0
    # Metadata, never the URL date or retrieval time, determines publication.
    for url in urls[:source.get('max_articles', 20)]:
        try:
            meta = Page(fetch(url)).meta
            title = meta.get('articletitle', '')
            raw = meta.get('pubdate', '') or meta.get('publishdate', '')
            origin = meta.get('contentsource', '') or meta.get('source', '')
            if not title or not raw or not any(s in origin for s in source['origin_names']):
                stats['rejected_metadata'] = stats.get('rejected_metadata', 0) + 1
                continue
            # These two Chinese official sources publish metadata in local time.
            raw = raw.replace('/', '-')
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):
                # Preserve a date as a date; the scorer handles its whole-day interval.
                published=raw
                stats['day_precision']=stats.get('day_precision',0)+1
            elif re.fullmatch(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?',raw):
                published=datetime.fromisoformat(raw).replace(tzinfo=timezone(timedelta(hours=8))).isoformat()
            else:
                stats['rejected_date'] = stats.get('rejected_date', 0) + 1
                continue
            stats['dated'] = stats.get('dated', 0) + 1
            inserted += save(source['id'], title, url, published, '')
        except Exception as error:
            # Do not publish response bodies, credentials, or private URLs.
            stats.setdefault('article_errors', []).append(type(error).__name__)
    return inserted

"""Per-symbol EOD ingestion. No alternate provider or invented bar on failure."""
import csv
import io
import json
import math
from datetime import datetime, timezone, timedelta, date
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from zoneinfo import ZoneInfo

class MarketFormatError(ValueError):
    pass

def number(value, positive=False):
    if value is None or str(value).strip() in ('', '-', 'null', 'None', 'N/D'):
        raise MarketFormatError('missing_numeric_field')
    value = float(value)
    if not math.isfinite(value) or (value <= 0 if positive else value < 0):
        raise MarketFormatError('invalid_numeric_field')
    return value

def validate(day, prices, volume, cutoff):
    date.fromisoformat(day)
    if day > cutoff:
        return False  # Current incomplete session and future observations excluded.
    if not (prices['low'] <= min(prices['open'], prices['close'])
            <= max(prices['open'], prices['close']) <= prices['high']):
        raise MarketFormatError('inconsistent_ohlc')
    return True

def collect(source, fetch, save, now=None):
    now = now or datetime.now(timezone.utc)
    us = source['kind'] == 'stooq'
    targets = [('SPY.US', 'spy.us'), ('GLD.US', 'gld.us'), ('NVDA.US', 'nvda.us')] if us else [('000300.SH', '1.000300'), ('600547.SH', '1.600547')]
    local = now.astimezone(ZoneInfo('America/New_York' if us else 'Asia/Shanghai'))
    cutoff = (local.date() if local.hour >= (17 if us else 16) else local.date()-timedelta(days=1)).isoformat()
    end = now.strftime('%Y%m%d'); begin = (now-timedelta(days=45)).strftime('%Y%m%d')
    output = []
    for symbol, upstream in targets:
        parts = urlsplit(source['url']); query = dict(parse_qsl(parts.query))
        query.update({'s':upstream, 'd1':begin, 'd2':end} if us else {'secid':upstream, 'beg':begin, 'end':end, 'lmt':'120'})
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))
        try:
            text = fetch(url)
            records = []
            if us:
                reader = csv.DictReader(io.StringIO(text))
                if not set(['Date','Open','High','Low','Close','Volume']).issubset(reader.fieldnames or []):
                    raise MarketFormatError('stooq_non_ohlcv_response')
                bars = list(reader)
            else:
                data = json.loads(text).get('data')
                if not isinstance(data, dict) or not isinstance(data.get('klines'), list):
                    raise MarketFormatError('eastmoney_no_klines')
                expected = upstream.split('.')[1]
                if data.get('code') != expected:
                    raise MarketFormatError('symbol_mismatch')
                bars = []
                for line in data['klines']:
                    fields = line.split(',')
                    if len(fields) < 7:
                        raise MarketFormatError('short_kline')
                    bars.append(dict(Date=fields[0], Open=fields[1], Close=fields[2], High=fields[3], Low=fields[4], Volume=fields[5], Turnover=fields[6]))
            for bar in bars:
                day = bar['Date']
                prices = {k.lower():number(bar[k], positive=True) for k in ['Open','High','Low','Close']}
                volume = number(bar.get('Volume'))  # An observed zero remains zero.
                if not validate(day, prices, volume, cutoff):
                    continue
                price_unit = 'USD' if us else ('index_points' if symbol=='000300.SH' else 'CNY')
                for metric, value in prices.items():
                    records.append((symbol,day,metric,value,price_unit,url))
                records.append((symbol,day,'volume',volume,'shares' if us else 'lots',url))
                if not us:
                    records.append((symbol,day,'turnover',number(bar.get('Turnover')),'CNY',url))
            if not records:
                raise MarketFormatError('no_completed_bars')
            count = save(source['id'], records)  # Atomic per symbol after full validation.
            output.append(dict(symbol=symbol,status='ok',count=count,last_date=max(r[1] for r in records),url=url))
        except Exception as error:
            code = str(error) if isinstance(error, MarketFormatError) else type(error).__name__
            output.append(dict(symbol=symbol,status='error',count=0,code=code,url=url))
    return output

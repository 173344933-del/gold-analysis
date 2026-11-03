"""Descriptive event studies. Outcomes are not causal effects or trading backtests."""
import csv
import hashlib
import json
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path
from statistics import mean

DATA=Path(__file__).resolve().parent.parent/'data/history'

# Editorial event anchors, never generated from price extrema. Official reference
# URLs are provided for review; original documents have not all been retrieved.
EVENTS=[
 ('asian97','1997-07-02','亚洲金融危机：泰铢浮动','GLOBAL','信用冲击','break','https://www.imf.org/external/np/exr/facts/asia.htm','汇率与外债错配显性化；比较不同市场，而非预设同向反应。'),
 ('ltcm98','1998-09-23','LTCM 救助与去杠杆','US','流动性','break','https://www.federalreservehistory.org/essays/ltcm-near-failure','杠杆策略相关性在压力中上升，流动性成为约束。'),
 ('dotcom','2000-03-10','互联网泡沫：纳指周期峰值','US','技术周期','hindsight','https://www.federalreservehistory.org/essays/dot-com-bubble','事后峰值标签；不能作为当时可交易的先验信号。'),
 ('sept11','2001-09-11','9·11 事件与交易中断','US','外生冲击','break','https://www.federalreservehistory.org/essays/september-11','市场停市与风险溢价变化；本样本不识别日内冲击。'),
 ('rmb05','2005-07-21','人民币汇率形成机制改革','CN','政策','trigger','https://www.pbc.gov.cn/','汇率制度变化可能改变出口、金融与资产重估预期。'),
 ('stamp07','2007-05-30','A股证券交易印花税上调','CN','监管','break','https://www.chinatax.gov.cn/','交易成本与政策预期改变；需要检查短期冲击是否持续。'),
 ('china07peak','2007-10-16','A股2007周期峰值','CN','市场周期','hindsight','https://www.sse.com.cn/market/price/trends/','事后周期标签，仅用于回看回撤结构，不进入前瞻触发检验。'),
 ('lehman','2008-09-15','雷曼申请破产保护','GLOBAL','信用冲击','break','https://www.federalreservehistory.org/essays/lehman-brothers-failure','信用风险与被动去杠杆共振；单一事件不能解释整个危机。'),
 ('stimulus08','2008-11-09','中国扩大内需政策公布','CN','财政政策','trigger','https://www.gov.cn/','政策承诺先于实体兑现；比较后续现金流与信用变化。'),
 ('us09trough','2009-03-09','美股金融危机周期低点','US','市场周期','hindsight','https://fred.stlouisfed.org/series/SP500','事后谷值，不是当时可识别的“精准抄底”信号。'),
 ('futures10','2010-04-16','沪深300股指期货启动','CN','市场结构','trigger','https://www.cffex.com.cn/','对冲工具改变市场结构；不能仅由指数收益推断政策因果。'),
 ('cash13','2013-06-20','中国银行间流动性紧张','CN','流动性','break','https://www.pbc.gov.cn/','资金价格压力可通过信用与估值渠道传导。'),
 ('rate14','2014-11-21','中国央行宣布降息','CN','货币政策','trigger','https://www.pbc.gov.cn/','观察宽松预期、风险偏好与盈利改善是否同步。'),
 ('china15peak','2015-06-12','A股杠杆牛市周期峰值','CN','市场周期','hindsight','https://www.sse.com.cn/market/price/trends/','事后标签；通过随后回撤研究杠杆反馈，不宣称峰值可预测。'),
 ('rmb15','2015-08-11','人民币中间价报价机制调整','CN','汇率政策','trigger','https://www.pbc.gov.cn/','汇率、资本流动预期与权益估值可能重新定价。'),
 ('circuit16','2016-01-04','A股熔断机制首次触发','CN','市场结构','break','https://www.csrc.gov.cn/','市场机制与流动性相互作用；不能把相关性直接解释为因果。'),
 ('tariff18','2018-03-22','美国宣布301贸易行动','GLOBAL','贸易政策','break','https://ustr.gov/issue-areas/enforcement/section-301-investigations','贸易摩擦预期影响供应链、盈利与风险溢价。'),
 ('wuhan20','2020-01-23','武汉暂停离汉通道','CN','公共卫生','break','https://www.gov.cn/','外生冲击与春节休市重叠，应按实际交易日对齐。'),
 ('pandemic20','2020-03-11','WHO 将COVID-19定性为大流行','GLOBAL','公共卫生','break','https://www.who.int/director-general/speeches/detail/who-director-general-s-opening-remarks-at-the-media-briefing-on-covid-19---11-march-2020','疫情、经济封锁与流动性共同变化，事件窗口高度重叠。'),
 ('fed20','2020-03-23','美联储扩大资产购买支持','US','货币政策','trigger','https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323a.htm','流动性尾部风险下降不等于盈利风险消失。'),
 ('ant20','2020-11-03','蚂蚁集团上市暂缓','CN','监管','break','https://www.sse.com.cn/','商业模式、监管边界与平台估值逻辑需要重新核验。'),
 ('tutoring21','2021-07-24','中国“双减”政策公布','CN','监管','break','https://www.gov.cn/zhengce/2021-07/24/content_5627132.htm','政策可改变行业利润池；宽基指数不能代表教培个股冲击。'),
 ('ukraine22','2022-02-24','俄乌冲突升级','GLOBAL','地缘冲击','break','https://www.un.org/','能源、通胀与风险溢价渠道交织，需分行业验证。'),
 ('fedhike22','2022-03-16','美联储启动本轮加息','US','货币政策','break','https://www.federalreserve.gov/newsevents/pressreleases/monetary20220316a.htm','贴现率重估与盈利预期变化需要分开解释。'),
 ('chatgpt','2022-11-30','ChatGPT 公开发布','GLOBAL','技术创新','trigger','https://openai.com/index/chatgpt/','从技术可用性到付费采用，再到资本开支与盈利兑现。'),
 ('chinaopen22','2022-12-07','中国疫情防控“新十条”公布','CN','政策','trigger','https://www.gov.cn/xinwen/2022-12/07/content_5730443.htm','重启预期与居民需求兑现的时间可能不一致。'),
 ('svb23','2023-03-10','硅谷银行被接管','US','信用冲击','break','https://www.fdic.gov/news/press-releases/2023/pr23016.html','久期损失、存款集中度与挤兑速度暴露脆弱性。'),
 ('nvidia23','2023-05-24','NVIDIA 财报与AI需求指引','US','盈利兑现','trigger','https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2024','把叙事从演示迁移到收入与订单；本基准不是NVDA个股。'),
 ('china24','2024-09-24','中国金融政策组合公布','CN','货币政策','trigger','https://www.pbc.gov.cn/','区分风险偏好重估与后续盈利、现金流修复。'),
]

@lru_cache(maxsize=1)
def manifest():
    return json.loads((DATA/'manifest.json').read_text())

@lru_cache(maxsize=100)
def series(symbol):
    meta=next((s for s in manifest()['series'] if s['symbol']==symbol),None)
    if not meta:return None,[]
    path=DATA/meta['file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('历史序列校验失败')
    with path.open() as f:
        rows=[{'date':r['date'],'close':float(r['close']),'volume':float(r['volume']) if r.get('volume') else None} for r in csv.DictReader(f)]
    return meta,rows

def drawdown(values):
    if not values:return None
    peak=values[0];worst=0
    for v in values:
        peak=max(peak,v);worst=min(worst,v/peak-1)
    return round(worst*100,2)

def study(symbol,date):
    meta,rows=series(symbol)
    if not rows:return {'available':False,'reason':'未接入该序列'}
    dates=[r['date'] for r in rows]
    monthly=meta['frequency']=='monthly_average'
    before_coverage=date[:7]<dates[0][:7] if monthly else date<dates[0]
    if before_coverage or date>=dates[-1]:return {'available':False,'reason':'事件超出实际数据覆盖范围'}
    # Monthly means cannot establish daily event reactions. Start at the first
    # completed month after the event month; never label it event-day return.
    i=next((i for i,r in enumerate(rows) if r['date'][:7]>date[:7]),len(rows)) if meta['frequency']=='monthly_average' else bisect_right(dates,date)
    if i>=len(rows):return {'available':False,'reason':'缺少事件后有效观测'}
    monthly=meta['frequency']=='monthly_average';horizons=[1,3,6,12] if monthly else [1,5,20,60,120,252]
    out={str(h):round((rows[i+h]['close']/rows[i]['close']-1)*100,2) if i+h<len(rows) else None for h in horizons}
    window=12 if monthly else 120
    completed=i+window<len(rows)
    values=[r['close'] for r in rows[i:min(len(rows),i+window+1)]]
    unadjusted='未复权' in meta['adjustment']
    suspicious=lambda xs:any(abs(b/a-1)>.35 for a,b in zip(xs,xs[1:]))
    corporate_warning=unadjusted and suspicious(values)
    if unadjusted:
        for h in horizons:
            if suspicious([r['close'] for r in rows[i:min(len(rows),i+h+1)]]):out[str(h)]=None
    return {'available':True,'symbol':symbol,'entry_date':rows[i]['date'],'entry_price':rows[i]['close'],
       'unit':'月度观测' if monthly else '交易日','returns':out,'drawdown':drawdown(values) if completed and not corporate_warning else None,
       'drawdown_window':window,'window_complete':completed,'last_observation':dates[-1],
       'baseline':'事件后第一个完整月的月均价' if monthly else '事件日期之后的首个可用交易日收盘',
       'path':[{'date':r['date'],'value':round((r['close']/rows[i]['close']-1)*100,4)} for r in rows[max(0,i-(6 if monthly else 20)):min(len(rows),i+window+1)]],
       'coverage_note':meta['adjustment'],'corporate_action_warning':corporate_warning}

@lru_cache(maxsize=100)
def signals(symbol):
    meta,rows=series(symbol)
    if not rows or meta['frequency']!='daily':return []
    output=[];last={'breakout':-100,'breakdown':-100}
    for i in range(60,len(rows)):
        prior=[r['close'] for r in rows[i-60:i]];price=rows[i]['close'];ma20=mean(prior[-20:]);ma60=mean(prior)
        if '未复权' in meta['adjustment'] and any(abs(b/a-1)>.35 for a,b in zip(prior,prior[1:]+[price])):continue
        for kind,condition in [('breakout',price>max(prior)*1.005 and ma20>ma60),('breakdown',price<ma60*.97 and price/max(prior)<.8)]:
            if condition and i-last[kind]>=60:
                output.append(dict(date=rows[i]['date'],kind=kind,price=price,rule='此前60日新高+0.5%且MA20>MA60' if kind=='breakout' else '低于此前MA60的97%且较此前60日高点回撤>20%',
                    forward_20=round((rows[i+20]['close']/price-1)*100,2) if i+20<len(rows) else None))
                last[kind]=i
    return output

def overview(symbol=None):
    symbol=symbol or '000001.SH';meta,_=series(symbol)
    events=[]
    for eid,date,title,country,category,phase,url,note in EVENTS:
        events.append(dict(id=eid,date=date,title=title,country=country,category=category,phase=phase,url=url,note=note,
          verification='编辑整理；参考链接原文尚未全部自动核验',study=study(symbol,date)))
    return dict(manifest=manifest(),symbol=symbol,meta=meta,events=events,signals=signals(symbol),
      limitations=['事件样本为人工选取，存在选择偏差与事件窗口重叠；未声称穷尽历史事件。',
        '事后峰谷标签仅作回顾，不进入可交易触发点或成功率计算。',
        '日线与月均值不可混合比较；月均值不能识别事件日冲击。',
        '指数价格收益不是含分红总回报，也不是个股收益；相关性不证明叙事因果。',
        '价格突破/失效为过去数据定义的技术状态，不等于叙事开启/破裂；后续20日收益单独用于事后描述。',
        '未取得连续20–30年新闻全文、当时一致预期和资金流，无法重建同期叙事热度。'])

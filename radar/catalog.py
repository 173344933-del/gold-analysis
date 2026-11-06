"""Explicit source coverage; availability is observed, never assumed."""
THEMES = [
    dict(id='ai', name='AI 算力与基础设施', en='AI INFRASTRUCTURE', sector='科技', markets=['US','CN'], tickers=['NVDA','MSFT','AMD','688256.SH'], terms=['artificial intelligence','data center','datacenter','semiconductor','nvidia','人工智能','算力','芯片','大模型'], thesis='资本开支能否转化为持续现金流，而非库存与折旧压力？', confirm='云厂商资本开支、推理需求与自由现金流同步改善。', invalidate='资本开支增长而利用率、毛利率和订单转化持续下滑。'),
    dict(id='rates', name='利率拐点与流动性', en='RATES & LIQUIDITY', sector='宏观', markets=['US','CN'], tickers=['TLT','SPY','510300.SS'], terms=['interest rate','federal funds','monetary policy','fomc','inflation','利率','降息','流动性','通胀'], thesis='通胀回落是否足以抵消增长与期限溢价风险？', confirm='实际利率回落且盈利预期未同步恶化。', invalidate='通胀再加速，或降息源于信用与盈利快速收缩。'),
    dict(id='gold', name='黄金与储备多元化', en='GOLD & RESERVES', sector='大宗', markets=['US','CN'], tickers=['GLD','GOLD','600547.SH'], terms=['gold','bullion','central bank reserves','黄金','购金','贵金属'], thesis='央行储备需求能否持续抵消实际利率与美元压力？', confirm='官方储备与ETF持仓增长，价格获得成交量确认。', invalidate='实际利率上行且央行、ETF需求同时转弱。'),
    dict(id='china', name='中国政策与内需修复', en='CHINA REFLATION', sector='宏观', markets=['CN','US'], tickers=['510300.SS','MCHI','BABA'], terms=['china','chinese','stimulus','中国','财政','消费','内需','房地产'], thesis='政策承诺何时转化为居民需求与企业盈利？', confirm='信用、消费、盈利修正和成交活跃度共同改善。', invalidate='政策预期升温但需求与现金流迟迟不兑现。'),
    dict(id='energy', name='能源安全与供给约束', en='ENERGY SECURITY', sector='大宗', markets=['US','CN'], tickers=['XLE','XOM','601857.SH'], terms=['oil','energy','opec','natural gas','crude','石油','能源','天然气'], thesis='供给纪律与地缘冲击能否传导到可持续自由现金流？', confirm='库存下降、期限结构趋紧且资本纪律维持。', invalidate='需求回落与新增供给释放共同压低价格。'),
    dict(id='robotics', name='机器人与具身智能', en='EMBODIED INTELLIGENCE', sector='科技', markets=['US','CN'], tickers=['TSLA','300124.SZ','002050.SZ'], terms=['robot','robotics','humanoid','机器人','具身智能','自动驾驶'], thesis='技术演示能否跨越量产成本与商业交付门槛？', confirm='付费订单、交付数量与单机经济性可被核实。', invalidate='反复推迟量产，收入主要来自概念或关联交易。'),
    dict(id='power', name='电网与电力资本开支', en='POWER & GRID', sector='工业', markets=['US','CN'], tickers=['VRT','ETN','600406.SH'], terms=['electricity','power grid','nuclear','电网','电力','核电','储能'], thesis='负荷增长与电网改造能否转化为设备与运营回报？', confirm='订单、监管回报与现金回款同步兑现。', invalidate='电力需求预测下修或项目回报被成本吞噬。'),
    dict(id='biotech', name='创新药与医疗技术', en='BIOTECH INNOVATION', sector='医疗', markets=['US','CN'], tickers=['XBI','LLY','600276.SH'], terms=['biotech','clinical','fda','drug','创新药','临床','医药','生物科技'], thesis='临床价值、支付意愿与商业化效率能否同时成立？', confirm='关键终点获验证，获批与净收入转化可追踪。', invalidate='临床失败、支付限制或现金消耗超过融资能力。'),
    dict(id='crypto', name='数字资产与市场结构', en='DIGITAL ASSETS', sector='金融', markets=['US'], tickers=['COIN','IBIT'], terms=['bitcoin','crypto','stablecoin','tokenization','比特币','稳定币','数字资产'], thesis='制度接纳是否转化为持续资金需求与可分配收入？', confirm='披露持仓、交易收入与合规进展共同改善。', invalidate='杠杆挤兑、监管收紧或业务收入无法覆盖成本。'),
    dict(id='trade', name='贸易重构与供应链', en='TRADE REALIGNMENT', sector='宏观', markets=['CN','US'], tickers=['ITA','CAT','601138.SH'], terms=['tariff','trade','supply chain','export','关税','贸易','出口','供应链'], thesis='供应链迁移带来新增价值还是重复资本开支？', confirm='订单迁移、产能利用率与回报率获得财报确认。', invalidate='关税成本侵蚀需求或新增产能长期闲置。'),
]

SOURCES = [
 dict(id='nvidia_news', name='NVIDIA Newsroom', category='公司原文', kind='rss', url='https://nvidianews.nvidia.com/releases.xml', authority=.8, coverage='芯片与算力供应商公告；厂商自述，非独立验证', history='滚动RSS，需持续保存', region='GLOBAL', publisher_group='nvidia', primary_hosts=['nvidianews.nvidia.com']),
 dict(id='azure_blog', name='Microsoft Azure Blog', category='公司原文', kind='rss', url='https://azure.microsoft.com/en-us/blog/feed/', authority=.8, coverage='云计算运营商原文；仅算力相关内容计入AI主题', history='滚动RSS，需持续保存', region='GLOBAL', publisher_group='microsoft', primary_hosts=['azure.microsoft.com']),
 dict(id='pbc', name='中国人民银行 · 新闻RSS', category='官方政策', kind='rss', url='https://www.pbc.gov.cn/goutongjiaoliu/113456/2986536/index.html', authority=1.0, coverage='政策与金融工作原文；不等于月度信用指标齐备', history='滚动RSS，需持续保存', region='CN', publisher_group='pbc', primary_hosts=['www.pbc.gov.cn','pbc.gov.cn']),
 dict(id='nbs', name='国家统计局 · 数据发布', category='官方宏观', kind='official_index', url='https://www.stats.gov.cn/sj/zxfb/', authority=1.0, coverage='只采集本机构有明确发布时间的原文标题；不自动提取指标数值', history='有界列表和文章元数据适配器', region='CN', publisher_group='nbs', article_hosts=['www.stats.gov.cn'], article_pattern=r'/sj/zxfb/\d{6}/t\d+_\d+\.html$', origin_names=['国家统计局'], publication_timezone='Asia/Shanghai'),
 dict(id='nea', name='国家能源局 · 公告与动态', category='官方产业', kind='official_index', url='https://www.nea.gov.cn/', authority=1.0, coverage='只采集本机构有明确发布时间的原文；拒绝外部媒体转载', history='有界列表和文章元数据适配器', region='CN', publisher_group='nea', article_hosts=['www.nea.gov.cn'], article_pattern=r'/\d{8}/[0-9a-f]{32}/c\.html$', origin_names=['国家能源局'], publication_timezone='Asia/Shanghai'),
 dict(id='eia', name='EIA · Today in Energy', category='官方产业', kind='rss', url='https://www.eia.gov/rss/todayinenergy.xml', authority=1.0, coverage='美国能源官方分析；仅电力相关内容计入power主题', history='滚动RSS，需持续保存', region='US', publisher_group='us_doe', primary_hosts=['www.eia.gov','eia.gov']),
 dict(id='wisdom_archive', name='中国历史指数 / 个股公开归档', category='历史行情', kind='bundled', url='https://github.com/qiutian02/WisdomGathering-Stock-Data/tree/dfb469b9fdba8b3bd2bad7af4e68091a88aefa9f', authority=.6, coverage='本地校验的真实长期子集；确切标的与日期见历史事件研究', history='1995起的代表性序列，部分指数或个股上市较晚；不是全市场', region='CN'),
 dict(id='shiller_dataset', name='Shiller / FRED 月度公开整理集', category='历史行情', kind='bundled', url='https://github.com/datasets/s-and-p-500/tree/87a2284276f79d75041c71c8f6d9f2aa1c965e84', authority=.7, coverage='1995以来标普500月均值，非月末收盘与个股行情', history='固定提交；2023-07起由上游仓库用FRED价格续接；零占位财务字段未导入', region='US'),
 dict(id='fed', name='Federal Reserve', category='官方政策', kind='rss', url='https://www.federalreserve.gov/feeds/press_all.xml', authority=1.0, coverage='RSS 近期公告；不代表完整历史', history='政策档案需按年补充', region='US'),
 dict(id='bls', name='美国劳工统计局 BLS', category='官方宏观', kind='rss', url='https://www.bls.gov/feed/bls_latest.rss', authority=1.0, coverage='RSS 最新统计公告', history='统计序列可超过20年；新闻非全量', region='US'),
 dict(id='ecb', name='欧洲央行 ECB', category='官方政策', kind='rss', url='https://www.ecb.europa.eu/rss/press.html', authority=1.0, coverage='近期政策公告', history='档案起点1998；本连接器仅RSS', region='GLOBAL'),
 dict(id='sec', name='SEC 监管公告', category='监管披露', kind='rss', url='https://www.sec.gov/news/pressreleases.rss', authority=1.0, coverage='近期监管新闻；非全部EDGAR申报', history='EDGAR电子档案1994起；尚未批量回填', region='US'),
 dict(id='arxiv', name='arXiv · AI research', category='科研前沿', kind='atom', url='https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=30', authority=.7, coverage='最新30篇AI预印本；未经同行评议', history='arXiv 1991起；本连接器仅近期样本', region='GLOBAL'),
 dict(id='hn', name='Hacker News · technology', category='开发者讨论', kind='rss', url='https://hnrss.org/frontpage', authority=.45, coverage='社区讨论；不是权威事实源', history='2007起；当前RSS仅近期', region='GLOBAL'),
 dict(id='github', name='GitHub · AI repositories', category='开源采用', kind='github', url='https://api.github.com/search/repositories?q=topic:artificial-intelligence&sort=updated&per_page=20', authority=.65, coverage='最近更新仓库；stars为存量而非资金流', history='2008起；本连接器非历史stars序列', region='GLOBAL'),
 dict(id='worldbank', name='World Bank · GDP / CPI', category='历史宏观', kind='worldbank', url='https://api.worldbank.org/v2/country/USA;CHN/indicator/NY.GDP.MKTP.KD.ZG?format=json&date=2006:2025&per_page=100', authority=1.0, coverage='2006–2025 美国/中国GDP、CPI年度数据（若已发布）', history='部分序列1960起；缺失值保留为空', region='GLOBAL'),
 dict(id='stooq', name='Stooq · US daily bars', category='交易行情', kind='stooq', url='https://stooq.com/q/d/l/?s=spy.us&i=d&d1=20060101&d2=20261231', authority=.7, coverage='SPY / GLD / NVDA 日线OHLCV，2006起按实际上市及可用日期', history='交易量不是资金净流入；复权口径需另核', region='US'),
 dict(id='eastmoney', name='东方财富 · A股日线', category='交易行情', kind='eastmoney', url='https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000300&klt=101&fqt=0&beg=20060101&end=20500101&lmt=10000&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61', authority=.6, coverage='沪深300 / 山东黄金日线；非官方接口，无可用性保证', history='请求2006起；实际覆盖以返回数据为准', region='CN'),
 dict(id='sse', name='上海证券交易所', category='官方披露', kind='reference', url='https://www.sse.com.cn/disclosure/listedinfo/announcement/', authority=1.0, coverage='官方公告入口；尚无自动采集连接器', history='需要合规档案接入或用户导入', region='CN'),
 dict(id='cninfo', name='巨潮资讯 CNINFO', category='官方披露', kind='reference', url='https://www.cninfo.com.cn/', authority=1.0, coverage='法定信息披露平台；当前仅来源目录', history='不宣称已抓取20年公告', region='CN'),
 dict(id='gdelt', name='GDELT · global news', category='全球新闻', kind='reference', url='https://www.gdeltproject.org/', authority=.65, coverage='待开发历史事件归档连接器；DOC API滚动窗口非20年全文', history='事件数据1979起、GKG 2013起、GDELT2 2015起；三者口径不同', region='GLOBAL'),
 dict(id='funds', name='SEC 13F · Berkshire Hathaway', category='披露持仓', kind='sec13f', url='https://data.sec.gov/submissions/CIK0001067983.json', authority=1.0, coverage='最新可用13F-HR披露的伯克希尔股票持仓；非完整组合，非实时资金流', history='当前仅最新一期；最长延迟45天，N-PORT尚未接入', region='US'),
]

# Multiple feeds from the same publisher never create independent breadth.
for source in SOURCES:
    source.setdefault('publisher_group', source['id'])
    source['heat_eligible'] = source['kind'] in ('rss','atom','official_index') and source['id'] != 'hn'


from .evidence_rules import CORE_TERMS
for theme in THEMES:
    if theme["id"] in CORE_TERMS: theme["terms"] = CORE_TERMS[theme["id"]]

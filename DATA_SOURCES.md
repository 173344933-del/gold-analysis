# 数据来源、口径与权利记录

## 中国历史价格

仓库：https://github.com/qiutian02/WisdomGathering-Stock-Data

固定提交：`dfb469b9fdba8b3bd2bad7af4e68091a88aefa9f`。

取用路径：`index/index_daily/` 与 `stock_daily/` 的分段7z档案。下载文件通过Git对象ID核验，选取六个指数和七个代表性个股，逐日去重，保留实际日期与原始数量字段。`volume`为上游原始数量口径，不进行金额推断。个股使用未复权收盘；现金分红、送转、拆合股都会使长期收益与真实持有回报不一致。暂未统一停复牌、退市与全部企业行动，因此不能把代表性存续个股子集当成无幸存者偏差的市场回测。

仓库MIT说明不构成我们对其上游供应商与交易所商业授权的独立确认。以下保留上游许可文本：

```
MIT License

Copyright (c) 2025 qiutian02

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 美国长期基准

仓库：https://github.com/datasets/s-and-p-500

固定提交：`87a2284276f79d75041c71c8f6d9f2aa1c965e84`。

原始整理者：Robert Shiller，http://www.econ.yale.edu/~shiller/data.htm 。上游2023-07后用FRED SP500续接：https://fred.stlouisfed.org/series/SP500 。历史段为月度平均价格；不是个股日线、月末收盘、总回报或可直接交易的月内信号。原始CSV对后期财务字段使用零占位，本产品**没有导入这些占位零**，不据此计算CAPE或盈利变化。续接段的精确聚合口径应在商业化前再次与上游生成脚本核对。

仓库声明：Open Data Commons Public Domain Dedication and License v1.0，https://opendatacommons.org/licenses/pddl/ 。其README也说明原始数据没有明确授权声明。这一差异保留，不能把整理仓库的许可直接当成原始数据的完整商业授权。

## 当前资讯与行情连接器

官网/原始API地址、权威度启发式、实际响应状态、日期范围逐源列于 `radar/catalog.py` 与网站数据源页。RSS仅保存标题、短摘要、时间与链接；公开构建摘要最多280字符，不保存完整付费文章。arXiv为预印本，HN为社区讨论，GitHub stars为采用代理指标；三者均不是公司盈利或真实投资决策。

SEC 13F仅为特定经理的最新可用13F-HR信息表；尚未合并13F-HR/A修订、N-PORT或其他资产。原文value的历史美元/千美元口径未统一，因此不计算跨期资金净流入或组合金额。PUT/CALL与SH/PRN字段单独保留。

## 历史事件

29个事件日期由研究框架人工整理，链接指向参考机构或文档，部分为机构首页而非逐条原文。网站明确标为尚未全部核验；这是研究索引而非已审计事实库。事后峰谷仅用于周期回顾，与当时可知事件区分。需要进一步建立正式逐事件文档、发布时间、时区、市场开闭市、修订与撤回证据后，才能进行更严格的因果和策略研究。

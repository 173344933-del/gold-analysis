"""Small, auditable relevance rules; publisher groups are not event corroboration."""
import re

CORE_TERMS = {
    'ai': ['data center', 'data centre', 'datacenter', 'semiconductor', 'gpu',
           'hbm', 'tpu', 'nvidia', 'ai infrastructure', 'ai accelerator',
           '算力', '智算', '数据中心', '芯片', '半导体'],
    'china': ['社会融资', '社融', '信贷', '贷款', '货币政策', '金融工作',
              '财政', '采购经理', '民间投资', '固定资产投资', '工业企业利润',
              '应收账款', '拖欠企业账款', '房地产', '内需', '消费',
              'china stimulus', 'china credit', 'chinese economy'],
    'power': ['electricity', 'power grid', 'transmission', 'substation',
              'nuclear', 'battery storage', 'solar generation', '电网', '电力',
              '用电量', '特高压', '输变电', '核电', '储能', '发电量'],
}

def matched_terms(theme, title, summary=''):
    text = (title + ' ' + summary).casefold()
    if theme['id'] == 'gold':
        # Scientific evaluation terminology is not precious-metal evidence.
        text = re.sub(r'\bgold(?:en)?[- ](?:answer|standard|label|reference)s?\b', '', text)
    terms = CORE_TERMS.get(theme['id'], theme['terms'])
    return [term for term in terms if (
        term in text if re.search(r'[\u4e00-\u9fff]', term) else
        re.search(r'(?<![a-z0-9])' + re.escape(term) + r'(?![a-z0-9])', text)
    )]

def publisher(source_id, catalog):
    source = catalog.get(source_id, {})
    return source.get('publisher_group', source_id)

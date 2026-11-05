"""Bank registry: the union of banks shown in the two reference screenshots.

status:
  live         - public source verified & parsed (plain request) in this prototype
  local_test   - rate page known or site blocks our overseas/cloud test host
                 (connection reset / 403 / 520); re-test from a mainland network
  app_only     - no public rate page on the official website; quotes appear to
                 live only in mobile banking / WeChat channels
  unknown      - institution not yet identified

`demo_usd` = (customer 购汇 price, customer 结汇 price) for USD 现汇 as shown in the
reference screenshots on 2026-11-05 (CNY per 100 USD). Used ONLY as clearly-labelled
demo data in the prototype. Values partially hidden behind the floating button in the
screenshot are marked with  # obscured.
"""

BANKS = [
    # code,     short, full name,               status,        demo_usd (购汇, 结汇)
    ("huanyu",  "寰宇", "寰宇（全称待确认）",      "unknown",    (668.0450, 666.7750)),
    ("cgb",     "广发", "广发银行",               "local_test",    (668.2400, 665.8400)),
    ("ncb",     "南洋", "南洋商业银行（中国）",     "live",    (668.2400, 665.9800)),
    ("hxb",     "华夏", "华夏银行",               "live",    (668.3300, 665.8600)),
    ("cbhb",    "渤海", "渤海银行",               "app_only",    (668.3900, 665.7000)),  # obscured
    ("bosc",    "上海", "上海银行",               "local_test",    (668.5100, 665.5600)),  # obscured
    ("ceb",     "光大", "中国光大银行",            "local_test",  (668.5156, 665.8479)),
    ("egb",     "恒丰", "恒丰银行",               "local_test",    (668.5400, 665.8600)),
    ("bob",     "北京", "北京银行",               "local_test",    (668.5900, 665.7000)),
    ("abc",     "农行", "中国农业银行",            "local_test",  (668.6080, 665.8060)),
    ("psbc",    "邮储", "中国邮政储蓄银行",        "local_test",  (668.6400, 665.8400)),
    ("czb",     "浙商", "浙商银行",               "local_test",    (668.6600, 665.9200)),
    ("cib",     "兴业", "兴业银行",               "local_test", (668.6800, 666.1400)),
    ("pab",     "平安", "平安银行",               "local_test",  (668.6867, 665.9340)),
    ("icbc",    "工行", "中国工商银行",            "local_test",  (668.7500, 665.2800)),
    ("bocom",   "交行", "交通银行",               "local_test",  (668.8500, 665.9900)),
    ("boc",     "中行", "中国银行",               "live",        (668.8800, 666.0800)),
    ("njcb",    "南京", "南京银行",               "local_test",    (668.9000, 665.9000)),
    ("cmbc",    "民生", "中国民生银行",            "app_only", (668.9000, 665.9000)),
    ("ccb",     "建行", "中国建设银行",            "local_test",  (668.9100, 665.4400)),
    ("cmb",     "招行", "招商银行",               "live",        (668.9180, 666.0160)),
    ("citic",   "中信", "中信银行",               "app_only", (668.9800, 666.1000)),
    ("spdb",    "浦发", "上海浦东发展银行",        "local_test",  (669.0200, 665.9500)),  # obscured
    ("hzb",     "杭州", "杭州银行",               "app_only",    (669.0700, 666.0700)),  # obscured
    ("nbcb",    "宁波", "宁波银行",               "local_test",    (669.1500, 666.1000)),
    ("hsbc",    "汇丰", "汇丰银行（中国）",        "local_test", (670.2822, 663.6281)),
    ("dbs",     "星展", "星展银行（中国）",        "app_only", (670.3432, 663.9482)),
    ("uob",     "大华", "大华银行（中国）",        "app_only",    (671.0000, 663.0000)),
    ("hangseng", "恒生", "恒生银行（中国）",       "app_only", (677.0862, 657.0738)),
]

BANK_MAP = {b[0]: dict(code=b[0], short=b[1], name=b[2], status=b[3], demo_usd=b[4])
            for b in BANKS}

CURRENCIES = [
    ("USD", "美元"), ("JPY", "日元"), ("HKD", "港元"), ("AUD", "澳元"),
    ("EUR", "欧元"), ("GBP", "英镑"), ("KRW", "韩元"), ("CAD", "加元"),
    ("SGD", "新加坡元"), ("CHF", "瑞士法郎"), ("NZD", "新西兰元"), ("MOP", "澳门元"),
]

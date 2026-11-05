"""Data-source adapters.

Each adapter has a pure ``parse`` function (unit-testable against saved fixtures)
and a ``fetch`` that performs a plain HTTP GET. Per the design doc (section 4.5):
no spoofed browser headers, no captcha/anti-bot circumvention.

All prices are normalised to **CNY per 100 units of foreign currency** (the unit
banks display), stored as Decimal.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import unescape

import httpx

UA = "fx-compare-prototype/0.1 (rate comparison research)"
TIMEOUT = 12.0

# Chinese currency names used by bank pages -> ISO 4217
CN_TO_ISO = {
    "美元": "USD", "日元": "JPY", "港币": "HKD", "港元": "HKD", "澳大利亚元": "AUD",
    "澳元": "AUD", "欧元": "EUR", "英镑": "GBP", "韩国元": "KRW", "韩元": "KRW",
    "加拿大元": "CAD", "加元": "CAD", "新加坡元": "SGD", "瑞士法郎": "CHF",
    "新西兰元": "NZD", "澳门元": "MOP", "泰国铢": "THB", "泰铢": "THB",
    "新台币": "TWD", "卢布": "RUB", "林吉特": "MYR", "瑞典克朗": "SEK",
    "挪威克朗": "NOK", "丹麦克朗": "DKK", "南非兰特": "ZAR",
}


@dataclass
class Quote:
    bank: str
    currency: str
    spot_buy: Decimal | None   # bank buys foreign currency (customer 结汇)
    spot_sell: Decimal | None  # bank sells foreign currency (customer 购汇)
    cash_buy: Decimal | None
    cash_sell: Decimal | None
    mid: Decimal | None
    published_at: str | None

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = float(v)
        return d


def _dec(s: str | None) -> Decimal | None:
    if s is None:
        return None
    s = s.strip()
    if s in ("", "-", "--", "---", "0", "0.0"):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _get(url: str) -> str:
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------------- 中国银行 (BOC)
BOC_URL = "https://www.boc.cn/sourcedb/whpj/"


def parse_boc(html: str) -> list[Quote]:
    out = []
    for name, row in re.findall(r"<tr data-currency='([^']+)'>(.*?)</tr>", html, re.S):
        iso = CN_TO_ISO.get(name)
        if not iso:
            continue
        cells = [unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 7:
            continue
        # 货币名称 现汇买入 现钞买入 现汇卖出 现钞卖出 中行折算价 发布日期 [发布时间]
        out.append(Quote("boc", iso, _dec(cells[1]), _dec(cells[3]), _dec(cells[2]),
                         _dec(cells[4]), _dec(cells[5]), cells[6].replace("/", "-")))
    return out


def fetch_boc() -> list[Quote]:
    return parse_boc(_get(BOC_URL))


# ---------------------------------------------------------------- 招商银行 (CMB)
CMB_URL = "https://fx.cmbchina.com/api/v1/fx/rate"


def parse_cmb(text: str) -> list[Quote]:
    data = json.loads(text)
    if data.get("returnCode") != "SUC0000":
        raise ValueError(f"cmb returnCode={data.get('returnCode')}")
    out = []
    for x in data["body"]:
        iso = x["ccyNbrEng"].split()[-1]
        m = re.match(r"(\d+)年(\d+)月(\d+)日", x.get("ratDat", ""))
        date = f"{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}" if m else ""
        # Field mapping inferred (rth*=现汇, rtc*=现钞, Bid=银行买入, Ofr=银行卖出,
        # rtbBid=折算价) and cross-checked against BOC: values are per 100 units.
        out.append(Quote("cmb", iso, _dec(x["rthBid"]), _dec(x["rthOfr"]), _dec(x["rtcBid"]),
                         _dec(x["rtcOfr"]), _dec(x["rtbBid"]),
                         f"{date} {x.get('ratTim', '')}".strip()))
    return out


def fetch_cmb() -> list[Quote]:
    return parse_cmb(_get(CMB_URL))


# ------------------------------------------------- 央行中间价 (CFETS central parity)
# NOTE: CFETS states commercial use of its data requires written authorisation.
# Prototype only — obtain a licence (or a licensed vendor) before production.
CFETS_URL = "https://www.chinamoney.com.cn/r/cms/www/chinamoney/data/fx/ccpr.json"


def parse_cfets(text: str) -> dict:
    data = json.loads(text)
    rates = {}
    for r in data["records"]:
        pair, price = r["vrtEName"], _dec(r["price"])
        if price is None:
            continue
        base, quote = pair.split("/")
        if quote == "CNY":                      # e.g. USD/CNY 6.7156, 100JPY/CNY 4.2283
            n = 100 if base.startswith("100") else 1
            iso = base.removeprefix("100")
            rates[iso] = (price * 100 / n).quantize(Decimal("0.0001"))
        elif base == "CNY":                     # e.g. CNY/KRW 200.54 -> CNY per 100 KRW
            rates[quote] = (Decimal(100) / price).quantize(Decimal("0.0001"))
    return {"date": data["data"].get("lastDate"), "rates": rates}


def fetch_cfets() -> dict:
    return parse_cfets(_get(CFETS_URL))


# --------------------------------------------------- 南洋商业银行（中国）(NCB)
# Public JSON API called by the official rate page
# (ncbchina.cn/website/ncb-zh/view/personFinance/person_01_01.html).
NCB_URL = "https://ibs.ncbchina.cn/NCB/mForeignExchangePriceQuery"


def parse_ncb(text: str) -> list[Quote]:
    data = json.loads(text)
    if data.get("resCode") != "CIP0000000":
        raise ValueError(f"ncb resCode={data.get('resCode')}")
    out = []
    for x in data.get("mktQtnInfoArrList") or []:
        base, quote = x["ccyPair"].split("/")

        def conv(v):
            d = _dec(v)
            if d is None:
                return None
            if quote == "CNY":            # USD/CNY 6.6814 -> per 100; JPY already per 100
                return d if base == "JPY" else d * 100
            return (Decimal(100) / d).quantize(Decimal("0.0001"))   # CNY/DKK inverted

        iso = base if quote == "CNY" else quote
        ex = [conv(x.get("cstExgBuyPrc")), conv(x.get("cstExgSellPrc"))]
        cash = [conv(x.get("cstCashBuyPrc")), conv(x.get("cstCashSellPrc"))]
        if None in ex:
            continue
        cash = cash if None not in cash else ex
        dt, tm = x.get("mktQtnDt", ""), x.get("mktQtnTm", "")
        ts = f"{dt[:4]}-{dt[4:6]}-{dt[6:]} {tm[:2]}:{tm[2:4]}:{tm[4:]}" if len(dt) == 8 and len(tm) == 6 else None
        # bank sells at the higher CNY-per-foreign price, buys at the lower
        out.append(Quote("ncb", iso, min(ex), max(ex), min(cash), max(cash), conv(x.get("cstExgMdlPrc")), ts))
    return out


def fetch_ncb() -> list[Quote]:
    r = httpx.post(NCB_URL, json={"ccyPair": "", "bsnsTp": "1"},
                   headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return parse_ncb(r.text)


# ---------------------------------------------------------------- 华夏银行 (HXB)
HXB_URL = "https://psbank.hxb.com.cn/gateway/forexquote.jsp"


def parse_hxb(html: str) -> list[Quote]:
    out = []
    for row in re.findall(r"<TR class=table_list_body[^>]*>(.*?)</TR>", html, re.S | re.I):
        c = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<TD[^>]*>(.*?)</TD>", row, re.S | re.I)]
        # 货币种类(USDCNY) 序号 现汇买入 现钞买入 现汇现钞卖出 现汇中间价 发布时间 ; per 100 units
        if len(c) < 7 or not c[0].endswith("CNY"):
            continue
        sell = _dec(c[4])
        out.append(Quote("hxb", c[0][:3], _dec(c[2]), sell, _dec(c[3]), sell, _dec(c[5]), c[6]))
    return out


def fetch_hxb() -> list[Quote]:
    return parse_hxb(_get(HXB_URL))


LIVE_ADAPTERS = {"boc": fetch_boc, "cmb": fetch_cmb, "ncb": fetch_ncb, "hxb": fetch_hxb}

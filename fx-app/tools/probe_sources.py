#!/usr/bin/env python3
"""Probe bank FX-rate sources with plain GET requests (no spoofed headers).

Usage:
  python3 probe_sources.py                 # probe all banks
  python3 probe_sources.py icbc abc ccb    # probe selected bank codes
  python3 probe_sources.py --links         # also scan homepages for 牌价/汇率 links
  python3 probe_sources.py --local --links # the 17 banks that need a mainland re-test

For each candidate URL prints HTTP status, content type, size, and whether the
body looks like it contains FX quotes (e.g. "美元" + a 6xx.xx style price).
Run it from a mainland-China network to re-test banks that reset connections
from overseas/cloud hosts. Be polite: it sends one request per URL.
"""
import re
import sys
import urllib.parse

import httpx

UA = "fx-compare-prototype/0.1 (rate comparison research)"

# code: (homepage, [candidate rate URLs])  -- candidates come from public info and
# must be verified; many are guesses to be confirmed by the --links scan.
BANKS = {
    "boc":      ("https://www.boc.cn/", ["https://www.boc.cn/sourcedb/whpj/"]),
    "cmb":      ("https://www.cmbchina.com/", ["https://fx.cmbchina.com/api/v1/fx/rate"]),
    "icbc":     ("https://www.icbc.com.cn/", ["https://papi.icbc.com.cn/exchanges/ns/getLatest"]),
    "abc":      ("https://www.abchina.com.cn/", ["https://www.abchina.com.cn/cn/PublicPlate/ExchangeRate/"]),
    "ccb":      ("https://www.ccb.com/", ["https://forex.ccb.com/cn/forex/exchange-quotations.html"]),
    "bocom":    ("https://www.bankcomm.com/", ["https://www.bankcomm.com/BankCommSite/zonghang/cn/whpj/foreignExchangeSearch_Cn.jsp"]),
    "psbc":     ("https://www.psbc.com/", []),
    "ceb":      ("https://www.cebbank.com/", []),
    "spdb":     ("https://www.spdb.com.cn/", []),
    "pab":      ("https://bank.pingan.com/", []),
    "citic":    ("https://www.citicbank.com/", []),
    "cmbc":     ("https://www.cmbc.com.cn/", []),
    "cib":      ("https://www.cib.com.cn/", ["https://personalbank.cib.com.cn/pers/main/pubinfo/ifxQuotationQuery.do",
                                          "https://personalbank.cib.com.cn/pers/main/pubinfo/ifxQuotationQuery/list"]),
    "hsbc":     ("https://www.hsbc.com.cn/", ["https://www.services.cn-banking.hsbc.com.cn/PublicContent/common/rate/zh/exchange-rates.html"]),
    "hangseng": ("https://www.hangseng.com.cn/", []),
    "dbs":      ("https://www.dbs.com.cn/", []),
    "cgb":      ("https://www.cgbchina.com.cn/", ["http://www.cgbchina.com.cn/CN/exchange/index.html"]),
    "ncb":      ("https://www.ncbchina.cn/", []),  # JSON POST, see backend/adapters.py
    "hxb":      ("https://www.hxb.com.cn/", ["https://psbank.hxb.com.cn/gateway/forexquote.jsp"]),
    "cbhb":     ("https://www.cbhb.com.cn/", []),
    "bosc":     ("https://www.bosc.cn/", []),
    "egb":      ("https://www.hfbank.com.cn/", []),
    "bob":      ("https://www.bankofbeijing.com.cn/", []),
    "czb":      ("https://www.czbank.com/", ["https://perbank.czbank.com/PERBANK/system/whpjInfoService_req_dispatch.jsp"]),  # legacy TLS; page auto-POSTs dse_operationName=whpjInfoServiceSrvOp to ../WebBank
    "njcb":     ("https://www.njcb.com.cn/", []),
    "hzb":      ("https://www.hzbank.com.cn/", []),
    "nbcb":     ("https://www.nbcb.com.cn/", []),
    "uob":      ("https://www.uobchina.com.cn/", []),
}

KEYWORDS = re.compile(r"牌价|汇率|外汇|exchange[\s_-]?rate|fxrate|whpj", re.I)
QUOTE_HINT = re.compile(r"(美元|USD).{0,400}?\b6\d\d\.\d{2,4}\b", re.S)


def get(client, url):
    try:
        r = client.get(url)
        body = r.text if "text" in r.headers.get("content-type", "") or "json" in r.headers.get("content-type", "") else ""
        return r, body, None
    except Exception as e:  # noqa: BLE001
        return None, "", f"{type(e).__name__}: {str(e)[:80]}"


def scan_links(base, html):
    out = []
    for href, text in re.findall(r'<a[^>]+href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
        text = re.sub(r"<[^>]+>|\s+", " ", text).strip()
        if KEYWORDS.search(text) or KEYWORDS.search(href):
            out.append((text[:20], urllib.parse.urljoin(base, href)))
    seen, uniq = set(), []
    for t, u in out:
        if u not in seen:
            seen.add(u)
            uniq.append((t, u))
    return uniq[:12]


# Banks to re-test from a mainland network (status local_test in backend/banks.py)
LOCAL_TEST = ["icbc", "abc", "ccb", "bocom", "psbc", "ceb", "spdb", "pab",
              "bosc", "egb", "bob", "njcb", "nbcb", "cgb", "hsbc", "cib", "czb"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--local" in sys.argv:
        args = LOCAL_TEST
    links = "--links" in sys.argv
    codes = args or list(BANKS)
    with httpx.Client(headers={"User-Agent": UA}, timeout=12, follow_redirects=True) as c:
        for code in codes:
            home, cands = BANKS[code]
            urls = ([home] if links or not cands else []) + cands
            for u in urls:
                r, body, err = get(c, u)
                if err:
                    print(f"{code:9} FAIL  {u}  {err}")
                    continue
                hint = "QUOTES?" if QUOTE_HINT.search(body) else ""
                print(f"{code:9} {r.status_code}   {u}  {r.headers.get('content-type','')[:30]} {len(r.content)}B {hint}")
                if links and u == home and body:
                    for t, l in scan_links(str(r.url), body):
                        print(f"{'':9}   -> {t:20} {l}")


if __name__ == "__main__":
    main()

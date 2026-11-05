"""Rate service: schedule-aware caching, demo data, ranking."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from adapters import LIVE_ADAPTERS, Quote, fetch_cfets
from banks import BANK_MAP, BANKS

log = logging.getLogger("fx")
CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- cache policy
# Observed: bank board rates refresh at minute level during the day (BOC/CMB both
# re-stamped within minutes), and are quiet overnight/weekends. CFETS central parity
# is published once per trading day at 09:15 Beijing time.
ACTIVE_TTL = 60          # 08:00–23:30 Mon–Fri  -> refresh at most every 60 s
QUIET_TTL = 15 * 60      # nights & weekends    -> every 15 min
ERROR_RETRY = 30         # after a failed fetch, retry no sooner than 30 s; serve stale


def bank_ttl(now: datetime | None = None) -> int:
    now = now or datetime.now(CST)
    if now.weekday() >= 5:
        return QUIET_TTL
    minutes = now.hour * 60 + now.minute
    return ACTIVE_TTL if 8 * 60 <= minutes <= 23 * 60 + 30 else QUIET_TTL


def cfets_expiry(now: datetime | None = None) -> float:
    """Cache central parity until the next 09:20 Beijing time (5-min buffer)."""
    now = now or datetime.now(CST)
    nxt = now.replace(hour=9, minute=20, second=0, microsecond=0)
    if now >= nxt:
        nxt += timedelta(days=1)
    return nxt.timestamp()


class Entry:
    def __init__(self):
        self.value = None
        self.expires = 0.0
        self.fetched_at: float | None = None
        self.error: str | None = None
        self.lock = threading.Lock()


_cache: dict[str, Entry] = {}


def _cached(key: str, loader, expiry_fn):
    e = _cache.setdefault(key, Entry())
    if time.time() < e.expires and e.value is not None:
        return e
    with e.lock:
        if time.time() < e.expires and e.value is not None:
            return e
        try:
            e.value = loader()
            e.fetched_at = time.time()
            e.error = None
            e.expires = expiry_fn()
        except Exception as ex:  # serve stale value, retry soon
            log.warning("fetch %s failed: %s", key, ex)
            e.error = str(ex)[:200]
            e.expires = time.time() + ERROR_RETRY
    return e


def live_quotes(bank: str) -> Entry:
    return _cached(f"bank:{bank}", lambda: {q.currency: q for q in LIVE_ADAPTERS[bank]()},
                   lambda: time.time() + bank_ttl())


def central_parity() -> Entry:
    return _cached("cfets", fetch_cfets, cfets_expiry)


# ---------------------------------------------------------------- demo data
def _demo_quote(bank: dict, currency: str, ref: Quote | None) -> Quote | None:
    """USD: screenshot values. Other currencies: scale the reference bank (BOC live)
    by the bank's relative USD spread. Synthetic — always flagged as demo."""
    sell_usd, buy_usd = bank["demo_usd"]   # (customer 购汇 = bank sell, customer 结汇 = bank buy)
    if currency == "USD":
        s, b = Decimal(str(sell_usd)), Decimal(str(buy_usd))
        return Quote(bank["code"], "USD", b, s, b, s, None, None)
    if ref is None or ref.spot_sell is None or ref.spot_buy is None:
        return None
    boc_sell, boc_buy = BANK_MAP["boc"]["demo_usd"]
    fs = Decimal(str(sell_usd / boc_sell))
    fb = Decimal(str(buy_usd / boc_buy))
    q4 = Decimal("0.0001")
    sell, buy = (ref.spot_sell * fs).quantize(q4), (ref.spot_buy * fb).quantize(q4)
    cs = (ref.cash_sell * fs).quantize(q4) if ref.cash_sell else sell
    cb = (ref.cash_buy * fb).quantize(q4) if ref.cash_buy else buy
    return Quote(bank["code"], currency, buy, sell, cb, cs, None, None)


# ---------------------------------------------------------------- ranking
def dense_rank(values: list[float | None], ascending: bool) -> list[int | None]:
    uniq = sorted({v for v in values if v is not None}, reverse=not ascending)
    pos = {v: i + 1 for i, v in enumerate(uniq)}
    return [pos.get(v) if v is not None else None for v in values]


def build_rates(currency: str, region: str, channel: str, demo: bool) -> dict:
    banks_out, sources = [], {}
    live = {}
    for code in LIVE_ADAPTERS:
        e = live_quotes(code)
        sources[code] = {"ok": e.error is None, "error": e.error, "fetched_at": e.fetched_at}
        if e.value:
            live[code] = e.value

    if region == "mainland":
        ref = live.get("boc", {}).get(currency)
        for code, short, name, status, _ in BANKS:
            bank = BANK_MAP[code]
            q, src = None, None
            if code in live and currency in live[code]:
                q, src = live[code][currency], "live"
            elif demo:
                q, src = _demo_quote(bank, currency, ref), "demo"
            if q is None:
                continue
            if channel == "spot":
                buy_price, sell_price = q.spot_sell, q.spot_buy    # customer view
            else:
                buy_price, sell_price = q.cash_sell, q.cash_buy
            banks_out.append({
                "code": code, "short": short, "name": name, "status": status,
                "source": src,
                "buy": float(buy_price) if buy_price else None,     # 购汇 (lower better)
                "sell": float(sell_price) if sell_price else None,  # 结汇 (higher better)
                "mid": float(q.mid) if q.mid else None,
                "published_at": q.published_at,
            })

    br = dense_rank([b["buy"] for b in banks_out], ascending=True)
    sr = dense_rank([b["sell"] for b in banks_out], ascending=False)
    for b, r1, r2 in zip(banks_out, br, sr):
        b["buy_rank"], b["sell_rank"] = r1, r2

    cp = central_parity()
    mid = None
    if cp.value and currency in cp.value["rates"]:
        mid = {"price": float(cp.value["rates"][currency]), "date": cp.value["date"],
               "source": "CFETS 中国外汇交易中心"}
    return {
        "currency": currency, "region": region, "channel": channel, "unit": 100,
        "central_parity": mid,
        "server_time": datetime.now(CST).isoformat(timespec="seconds"),
        "cache_ttl": bank_ttl(),
        "sources": sources,
        "banks": banks_out,
    }

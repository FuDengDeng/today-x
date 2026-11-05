import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from adapters import parse_boc, parse_cfets, parse_cmb  # noqa: E402
from service import CST, bank_ttl, dense_rank  # noqa: E402

FX = ROOT / "fixtures"


def test_boc_parse():
    qs = {q.currency: q for q in parse_boc((FX / "boc_whpj.html").read_text("utf-8"))}
    assert {"USD", "JPY", "HKD", "EUR", "KRW"} <= qs.keys()
    usd = qs["USD"]
    assert usd.spot_sell > usd.spot_buy
    assert Decimal("500") < usd.spot_sell < Decimal("900")   # per 100 USD
    assert qs["JPY"].spot_sell < Decimal("10")                # per 100 JPY


def test_cmb_parse():
    qs = {q.currency: q for q in parse_cmb((FX / "cmb_rate.json").read_text("utf-8"))}
    assert "USD" in qs and "KRW" not in qs
    assert qs["USD"].spot_sell > qs["USD"].spot_buy
    assert qs["JPY"].spot_sell < Decimal("10")                # same unit as BOC


def test_cfets_parse_and_matches_boc_conversion_price():
    cp = parse_cfets((FX / "cfets_ccpr.json").read_text("utf-8"))["rates"]
    boc = {q.currency: q for q in parse_boc((FX / "boc_whpj.html").read_text("utf-8"))}
    for c in ("USD", "JPY", "KRW", "EUR"):
        # 中行折算价 equals CFETS central parity (per 100 units)
        assert abs(cp[c] - boc[c].mid) / boc[c].mid < Decimal("0.001"), c


def test_dense_rank():
    assert dense_rank([668.045, 668.24, 668.24, 668.33, None], True) == [1, 2, 2, 3, None]
    assert dense_rank([666.1, 666.775, 666.1], False) == [2, 1, 2]


def test_ttl_schedule():
    assert bank_ttl(datetime(2026, 11, 5, 10, 0, tzinfo=CST)) == 60     # Thu daytime
    assert bank_ttl(datetime(2026, 11, 5, 2, 0, tzinfo=CST)) == 900     # night
    assert bank_ttl(datetime(2026, 11, 7, 10, 0, tzinfo=CST)) == 900    # Saturday

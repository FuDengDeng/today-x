"""FastAPI app: JSON API + serves the mobile web (H5) prototype.

Run:  cd fx-app/backend && uvicorn app:app --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from banks import BANKS, CURRENCIES
from service import build_rates, central_parity

app = FastAPI(title="FX compare prototype")
WEB = Path(__file__).resolve().parent.parent / "web"


@app.get("/api/v1/currencies")
def currencies():
    return [{"code": c, "name": n} for c, n in CURRENCIES]


@app.get("/api/v1/rates")
def rates(currency: str = "USD",
          region: str = Query("mainland", pattern="^(mainland|hk)$"),
          channel: str = Query("spot", pattern="^(spot|cash)$"),
          demo: bool = True):
    return build_rates(currency.upper(), region, channel, demo)


@app.get("/api/v1/central-parity")
def cp():
    e = central_parity()
    if not e.value:
        return {"ok": False, "error": e.error}
    return {"ok": True, "date": e.value["date"],
            "rates": {k: float(v) for k, v in e.value["rates"].items()}}


@app.get("/api/v1/sources")
def sources():
    return [{"code": b[0], "short": b[1], "name": b[2], "status": b[3]} for b in BANKS]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")

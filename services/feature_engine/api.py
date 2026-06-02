"""Feature Engine API - FastAPI service exposing technical indicators."""
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from services.market_data.client import MarketDataClient
from services.feature_engine.indicators import compute_all_features, get_latest_features
from services.core.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Feature Engine API",
    description="Computes technical indicators from market data",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config()
market_client = MarketDataClient()


@app.get("/health")
def health():
    return {"status": "ok", "service": "feature_engine"}


@app.get("/features/{symbol}")
def get_features(
    symbol: str,
    period: str = Query(default="1y", description="Data period: 1mo, 3mo, 6mo, 1y, 2y"),
):
    """Return latest feature snapshot for a symbol."""
    symbol = symbol.upper()
    allowed = config.get_symbols()
    if symbol not in allowed:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} not in allowed list: {allowed}")

    try:
        df = market_client.get_daily_bars(symbol, period=period)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market data error: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No market data for {symbol}")

    features = get_latest_features(df)
    if features is None:
        raise HTTPException(status_code=422, detail=f"Could not compute features for {symbol}")

    return {"symbol": symbol, "features": features}


@app.get("/features/{symbol}/history")
def get_features_history(
    symbol: str,
    period: str = Query(default="6mo"),
    rows: int = Query(default=30, ge=1, le=500),
):
    """Return historical feature rows for backtesting/analysis."""
    symbol = symbol.upper()
    allowed = config.get_symbols()
    if symbol not in allowed:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} not allowed")

    try:
        df = market_client.get_daily_bars(symbol, period=period)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market data error: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No market data for {symbol}")

    enriched = compute_all_features(df)
    if enriched is None or enriched.empty:
        raise HTTPException(status_code=422, detail="Feature computation failed")

    # Return last N rows as list of dicts
    tail = enriched.tail(rows).reset_index()
    tail["date"] = tail["Date"].astype(str) if "Date" in tail.columns else tail.index.astype(str)
    records = tail.drop(columns=["Date"], errors="ignore").to_dict(orient="records")
    return {"symbol": symbol, "rows": len(records), "data": records}


@app.get("/symbols")
def list_symbols():
    """Return configured tradeable symbols."""
    return {"symbols": config.get_symbols()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

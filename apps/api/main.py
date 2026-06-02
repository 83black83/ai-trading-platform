"""FastAPI Backend - API REST principale per la piattaforma di trading AI."""
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.core.config import Config
from services.market_data.client import MarketDataClient
from services.feature_engine.indicators import get_latest_features
from services.agents.supervisor import SupervisorAgent, DebateResult
from services.risk_engine.engine import RiskEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title="AI Trading Platform API",
    description="Backend API per la piattaforma multi-agent di trading",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Istanze globali
config = Config()
market_client = MarketDataClient()
risk_engine = RiskEngine()
supervisor = SupervisorAgent(risk_engine=risk_engine)

PORTFOLIO_VALUE = float(os.getenv("PORTFOLIO_VALUE", "10000"))


# --- Modelli Pydantic ---
class SignalRequest(BaseModel):
    symbol: str
    portfolio_value: Optional[float] = None
    period: str = "1y"


class SignalResponse(BaseModel):
    symbol: str
    action: str
    confidence: float
    quantity: float
    approved_by_risk: bool
    debate_summary: str
    timestamp: str
    agent_signals: List[Dict[str, Any]]


class PortfolioUpdate(BaseModel):
    portfolio_value: float
    positions: Optional[Dict[str, float]] = None


# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-trading-api", "timestamp": datetime.utcnow().isoformat()}


@app.get("/symbols")
def list_symbols():
    """Lista dei simboli configurati."""
    return {"symbols": config.get_symbols()}


@app.get("/features/{symbol}")
def get_features(symbol: str, period: str = Query(default="1y")):
    """Ultime features tecniche per un simbolo."""
    symbol = symbol.upper()
    if symbol not in config.get_symbols():
        raise HTTPException(400, f"Simbolo {symbol} non configurato")

    df = market_client.get_daily_bars(symbol, period=period)
    if df is None or df.empty:
        raise HTTPException(404, f"Nessun dato per {symbol}")

    features = get_latest_features(df)
    if not features:
        raise HTTPException(422, "Calcolo features fallito")

    return {"symbol": symbol, "features": features, "timestamp": datetime.utcnow().isoformat()}


@app.post("/signal", response_model=SignalResponse)
def generate_signal(req: SignalRequest):
    """Genera un segnale di trading per un simbolo tramite il ciclo multi-agent completo."""
    symbol = req.symbol.upper()
    if symbol not in config.get_symbols():
        raise HTTPException(400, f"Simbolo {symbol} non configurato")

    df = market_client.get_daily_bars(symbol, period=req.period)
    if df is None or df.empty:
        raise HTTPException(404, f"Nessun dato per {symbol}")

    features = get_latest_features(df)
    if not features:
        raise HTTPException(422, "Calcolo features fallito")

    portfolio_val = req.portfolio_value or PORTFOLIO_VALUE
    result: DebateResult = supervisor.run_debate(
        symbol=symbol,
        features=features,
        current_price=features.get("close", 0.0),
        portfolio_value=portfolio_val,
    )

    agent_signals = [
        {
            "agent": s.agent,
            "action": s.action,
            "confidence": s.confidence,
            "reasoning": s.reasoning[:300],
        }
        for s in result.signals
    ]

    return SignalResponse(
        symbol=result.symbol,
        action=result.final_action,
        confidence=result.final_confidence,
        quantity=result.quantity,
        approved_by_risk=result.approved_by_risk,
        debate_summary=result.debate_summary,
        timestamp=result.timestamp,
        agent_signals=agent_signals,
    )


@app.post("/signal/all")
def generate_all_signals(portfolio_value: float = Query(default=10000.0)):
    """Genera segnali per tutti i simboli configurati."""
    symbols = config.get_symbols()
    results = []

    for symbol in symbols:
        try:
            df = market_client.get_daily_bars(symbol, period="1y")
            if df is None or df.empty:
                continue
            features = get_latest_features(df)
            if not features:
                continue
            result = supervisor.run_debate(
                symbol=symbol,
                features=features,
                current_price=features.get("close", 0.0),
                portfolio_value=portfolio_value,
            )
            results.append({
                "symbol": result.symbol,
                "action": result.final_action,
                "confidence": result.final_confidence,
                "quantity": result.quantity,
                "approved": result.approved_by_risk,
                "summary": result.debate_summary[:200],
            })
        except Exception as e:
            logger.error(f"Errore segnale {symbol}: {e}")

    return {"results": results, "timestamp": datetime.utcnow().isoformat()}


@app.post("/portfolio/update")
def update_portfolio(update: PortfolioUpdate):
    """Aggiorna il valore del portafoglio nel Risk Engine."""
    global PORTFOLIO_VALUE
    PORTFOLIO_VALUE = update.portfolio_value
    risk_engine.update_portfolio(
        positions=update.positions or {},
        portfolio_value=update.portfolio_value,
    )
    return {"status": "updated", "portfolio_value": update.portfolio_value}


@app.get("/risk/status")
def get_risk_status():
    """Stato corrente del Risk Engine."""
    return {
        "daily_trades": risk_engine.daily_trades,
        "daily_pnl": risk_engine.daily_pnl,
        "portfolio_value": risk_engine.portfolio_value,
        "positions": risk_engine.positions,
        "max_trades_per_day": risk_engine.risk_cfg.get("max_trades_per_day", 10),
        "max_position_size_pct": risk_engine.risk_cfg.get("max_position_size_pct", 0.10),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

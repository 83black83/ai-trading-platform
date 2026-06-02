"""Risk Engine - valuta se un trade proposto rispetta i limiti di rischio."""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from services.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class RiskDecision:
    approved: bool
    symbol: str
    action: str  # BUY / SELL / HOLD
    quantity: float
    reason: str
    risk_score: float  # 0-100, higher = riskier
    timestamp: str


class RiskEngine:
    """Valuta ogni segnale di trading rispetto alle regole di rischio configurate."""

    def __init__(self):
        self.config = Config()
        self.risk_cfg = self.config.risk
        self.positions: Dict[str, float] = {}  # symbol -> current qty
        self.portfolio_value: float = 0.0
        self.daily_trades: int = 0
        self.daily_pnl: float = 0.0

    def update_portfolio(self, positions: Dict[str, float], portfolio_value: float):
        """Aggiorna snapshot corrente del portafoglio."""
        self.positions = positions
        self.portfolio_value = portfolio_value

    def reset_daily_counters(self):
        """Chiamare ogni giorno a market open."""
        self.daily_trades = 0
        self.daily_pnl = 0.0

    def evaluate(
        self,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        features: Optional[Dict[str, Any]] = None,
        confidence: float = 0.5,
    ) -> RiskDecision:
        """Valuta un segnale di trading e restituisce un RiskDecision."""
        action = action.upper()
        reasons = []
        risk_score = 0.0

        # --- Regola 1: Limiti operativi di base ---
        max_trades = self.risk_cfg.get("max_trades_per_day", 10)
        if self.daily_trades >= max_trades:
            return RiskDecision(
                approved=False,
                symbol=symbol,
                action=action,
                quantity=quantity,
                reason=f"Raggiunto limite giornaliero trades: {max_trades}",
                risk_score=100.0,
                timestamp=datetime.utcnow().isoformat(),
            )

        # --- Regola 2: Dimensione posizione ---
        max_position_pct = self.risk_cfg.get("max_position_size_pct", 0.10)
        trade_value = quantity * price

        if self.portfolio_value > 0:
            position_pct = trade_value / self.portfolio_value
            if position_pct > max_position_pct:
                # Ridimensiona automaticamente
                adjusted_qty = (max_position_pct * self.portfolio_value) / price
                reasons.append(
                    f"Qty ridimensionata da {quantity:.2f} a {adjusted_qty:.2f} "
                    f"(max {max_position_pct*100:.0f}% portfolio)"
                )
                quantity = adjusted_qty
                trade_value = quantity * price
                risk_score += 20

        # --- Regola 3: Max drawdown giornaliero ---
        max_drawdown = self.risk_cfg.get("max_daily_drawdown_pct", 0.02)
        if self.portfolio_value > 0:
            drawdown_pct = abs(self.daily_pnl) / self.portfolio_value
            if drawdown_pct >= max_drawdown and self.daily_pnl < 0:
                return RiskDecision(
                    approved=False,
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    reason=f"Drawdown giornaliero raggiunto: {drawdown_pct*100:.2f}% >= {max_drawdown*100:.0f}%",
                    risk_score=100.0,
                    timestamp=datetime.utcnow().isoformat(),
                )

        # --- Regola 4: Volatilita' ---
        if features:
            vol = features.get("volatility_20d", 0)
            max_vol = self.risk_cfg.get("max_volatility_threshold", 0.05)
            if vol > max_vol:
                risk_score += 30
                reasons.append(f"Alta volatilita': {vol:.4f} > soglia {max_vol}")

        # --- Regola 5: Confidence minima ---
        min_confidence = self.risk_cfg.get("min_confidence", 0.6)
        if confidence < min_confidence:
            return RiskDecision(
                approved=False,
                symbol=symbol,
                action=action,
                quantity=quantity,
                reason=f"Confidence {confidence:.2f} sotto soglia {min_confidence}",
                risk_score=risk_score + 40,
                timestamp=datetime.utcnow().isoformat(),
            )
        else:
            # Confidence alta riduce il rischio
            risk_score = max(0, risk_score - (confidence - min_confidence) * 50)

        # --- Regola 6: Quantita' minima ---
        if quantity < 0.01:
            return RiskDecision(
                approved=False,
                symbol=symbol,
                action=action,
                quantity=quantity,
                reason="Quantita' troppo bassa dopo ridimensionamento",
                risk_score=risk_score,
                timestamp=datetime.utcnow().isoformat(),
            )

        # --- APPROVATO ---
        reason_str = "; ".join(reasons) if reasons else "Tutti i controlli superati"
        self.daily_trades += 1
        logger.info(
            f"[RiskEngine] APPROVATO {action} {quantity:.4f} {symbol} "
            f"@ {price:.2f} | risk_score={risk_score:.1f} | {reason_str}"
        )
        return RiskDecision(
            approved=True,
            symbol=symbol,
            action=action,
            quantity=round(quantity, 4),
            reason=reason_str,
            risk_score=round(risk_score, 1),
            timestamp=datetime.utcnow().isoformat(),
        )

    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        confidence: float,
        volatility: float,
    ) -> float:
        """Kelly-inspired position sizing ridotto per sicurezza."""
        base_pct = self.risk_cfg.get("max_position_size_pct", 0.10)
        # Scala in base a confidence e volatilita' inversa
        vol_factor = max(0.1, 1 - (volatility * 10))  # alta vol = meno size
        kelly_fraction = 0.25  # frazione Kelly conservativa
        size_pct = base_pct * confidence * vol_factor * kelly_fraction
        size_pct = max(0.01, min(size_pct, base_pct))  # clamp

        if self.portfolio_value > 0:
            qty = (self.portfolio_value * size_pct) / price
        else:
            qty = 1.0

        logger.debug(
            f"[PositionSize] {symbol} price={price:.2f} conf={confidence:.2f} "
            f"vol={volatility:.4f} -> qty={qty:.4f} ({size_pct*100:.1f}%)"
        )
        return round(qty, 4)

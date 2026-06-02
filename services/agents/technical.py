"""Technical Analyst Agent - analizza indicatori tecnici e genera un segnale."""
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AgentSignal:
    agent: str
    symbol: str
    action: str        # BUY / SELL / HOLD
    confidence: float  # 0.0 - 1.0
    reasoning: str
    features_used: Dict[str, Any]
    timestamp: str


class TechnicalAnalystAgent:
    """
    Agente analista tecnico che interpreta indicatori quantitativi
    e produce un segnale BUY/SELL/HOLD con confidence score.
    Non predice il futuro: analizza pattern storici dei prezzi.
    """

    NAME = "TechnicalAnalyst"

    def analyze(self, symbol: str, features: Dict[str, Any]) -> AgentSignal:
        """Analizza le features e restituisce un AgentSignal."""
        reasons = []
        bull_score = 0.0
        bear_score = 0.0
        weight_total = 0.0

        # --- RSI (0-100): oversold < 30, overbought > 70 ---
        rsi = features.get("rsi_14")
        if rsi is not None:
            weight_total += 2.0
            if rsi < 30:
                bull_score += 2.0
                reasons.append(f"RSI={rsi:.1f} oversold (BUY segnale)")
            elif rsi > 70:
                bear_score += 2.0
                reasons.append(f"RSI={rsi:.1f} overbought (SELL segnale)")
            elif rsi < 45:
                bull_score += 0.5
                reasons.append(f"RSI={rsi:.1f} zona ribassista lieve")
            elif rsi > 55:
                bear_score += 0.5
                reasons.append(f"RSI={rsi:.1f} zona rialzista lieve")

        # --- MACD: histogram positivo = momentum rialzista ---
        macd_hist = features.get("macd_hist")
        macd = features.get("macd")
        macd_signal = features.get("macd_signal")
        if macd_hist is not None:
            weight_total += 2.0
            if macd_hist > 0 and macd is not None and macd > macd_signal:
                bull_score += 2.0
                reasons.append(f"MACD hist={macd_hist:.4f} positivo, MACD sopra signal")
            elif macd_hist < 0 and macd is not None and macd < macd_signal:
                bear_score += 2.0
                reasons.append(f"MACD hist={macd_hist:.4f} negativo, MACD sotto signal")
            elif macd_hist > 0:
                bull_score += 1.0
                reasons.append(f"MACD hist={macd_hist:.4f} positivo")
            else:
                bear_score += 1.0
                reasons.append(f"MACD hist={macd_hist:.4f} negativo")

        # --- Bollinger Bands: bb_pct (0=low band, 1=high band) ---
        bb_pct = features.get("bb_pct")
        if bb_pct is not None:
            weight_total += 1.5
            if bb_pct < 0.2:
                bull_score += 1.5
                reasons.append(f"BB%={bb_pct:.2f} vicino banda inferiore (rimbalzo potenziale)")
            elif bb_pct > 0.8:
                bear_score += 1.5
                reasons.append(f"BB%={bb_pct:.2f} vicino banda superiore (ritracciamento potenziale)")
            else:
                reasons.append(f"BB%={bb_pct:.2f} zona centrale")

        # --- Trend: EMA20 vs EMA50 ---
        ema20 = features.get("ema_20")
        ema50 = features.get("ema_50")
        if ema20 is not None and ema50 is not None:
            weight_total += 2.0
            if ema20 > ema50:
                bull_score += 2.0
                reasons.append(f"EMA20={ema20:.2f} sopra EMA50={ema50:.2f} (trend rialzista)")
            else:
                bear_score += 2.0
                reasons.append(f"EMA20={ema20:.2f} sotto EMA50={ema50:.2f} (trend ribassista)")

        # --- SMA crossover: SMA20 vs SMA50 ---
        sma20 = features.get("sma_20")
        sma50 = features.get("sma_50")
        if sma20 is not None and sma50 is not None:
            weight_total += 1.5
            if sma20 > sma50:
                bull_score += 1.5
                reasons.append(f"SMA20 > SMA50: golden cross zone")
            else:
                bear_score += 1.5
                reasons.append(f"SMA20 < SMA50: death cross zone")

        # --- Volume ratio ---
        vol_ratio = features.get("volume_ratio")
        if vol_ratio is not None:
            weight_total += 1.0
            if vol_ratio > 1.5:
                reasons.append(f"Volume ratio={vol_ratio:.2f}: volume elevato (conferma movimento)")
                # Amplifica il segnale prevalente
                if bull_score > bear_score:
                    bull_score += 1.0
                else:
                    bear_score += 1.0

        # --- ATR volatility context ---
        volatility = features.get("volatility_20d", 0)
        if volatility > 0.04:
            reasons.append(f"Alta volatilita' ({volatility:.3f}): segnale meno affidabile")

        # --- Calcola action e confidence ---
        if weight_total == 0:
            return AgentSignal(
                agent=self.NAME, symbol=symbol, action="HOLD",
                confidence=0.0, reasoning="Nessun dato sufficiente",
                features_used=features, timestamp=datetime.utcnow().isoformat()
            )

        net_score = (bull_score - bear_score) / weight_total  # range approx -1..+1

        if net_score > 0.15:
            action = "BUY"
            confidence = min(0.95, 0.5 + net_score * 0.5)
        elif net_score < -0.15:
            action = "SELL"
            confidence = min(0.95, 0.5 + abs(net_score) * 0.5)
        else:
            action = "HOLD"
            confidence = 0.5 - abs(net_score)

        # Penalizza confidence se alta volatilita'
        if volatility > 0.04:
            confidence *= 0.85

        reasoning = " | ".join(reasons)
        logger.info(
            f"[{self.NAME}] {symbol}: {action} confidence={confidence:.2f} "
            f"bull={bull_score:.1f} bear={bear_score:.1f}"
        )

        return AgentSignal(
            agent=self.NAME,
            symbol=symbol,
            action=action,
            confidence=round(confidence, 3),
            reasoning=reasoning,
            features_used={
                k: features[k] for k in
                ["rsi_14", "macd_hist", "bb_pct", "ema_20", "ema_50",
                 "sma_20", "sma_50", "volume_ratio", "volatility_20d"]
                if k in features
            },
            timestamp=datetime.utcnow().isoformat(),
        )

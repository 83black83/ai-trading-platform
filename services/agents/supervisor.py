"""Supervisor Agent - orchestra il debate tra agenti e prende la decisione finale."""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import Counter

from services.agents.technical import TechnicalAnalystAgent, AgentSignal
from services.risk_engine.engine import RiskEngine, RiskDecision

logger = logging.getLogger(__name__)


@dataclass
class DebateResult:
    symbol: str
    final_action: str
    final_confidence: float
    approved_by_risk: bool
    risk_decision: Optional[RiskDecision]
    signals: List[AgentSignal]
    debate_summary: str
    timestamp: str
    quantity: float = 0.0


class SupervisorAgent:
    """
    Supervisor che:
    1. Raccoglie segnali da tutti gli agenti analisti
    2. Conduce un debate (votazione ponderata)
    3. Sottopone la decisione al Risk Engine
    4. Produce un DebateResult finale con audit trail completo
    """

    def __init__(self, risk_engine: Optional[RiskEngine] = None):
        # Agenti analisti (espandibile)
        self.agents = [
            TechnicalAnalystAgent(),
            # SentimentAnalystAgent(),  # da aggiungere
            # NewsAnalystAgent(),       # da aggiungere
        ]
        self.risk_engine = risk_engine or RiskEngine()

    def run_debate(
        self,
        symbol: str,
        features: Dict[str, Any],
        current_price: float,
        portfolio_value: float = 0.0,
        positions: Optional[Dict[str, float]] = None,
    ) -> DebateResult:
        """Esegue il ciclo completo: analisi -> debate -> risk check -> decisione."""

        logger.info(f"[Supervisor] Avvio debate per {symbol} @ {current_price:.2f}")

        # --- Step 1: Raccolta segnali ---
        signals: List[AgentSignal] = []
        for agent in self.agents:
            try:
                sig = agent.analyze(symbol, features)
                signals.append(sig)
                logger.info(
                    f"  [{sig.agent}] {sig.action} conf={sig.confidence:.2f}: {sig.reasoning[:80]}..."
                )
            except Exception as e:
                logger.error(f"  Errore agente {agent.__class__.__name__}: {e}")

        if not signals:
            return DebateResult(
                symbol=symbol, final_action="HOLD", final_confidence=0.0,
                approved_by_risk=False, risk_decision=None, signals=[],
                debate_summary="Nessun agente ha prodotto segnali",
                timestamp=datetime.utcnow().isoformat(),
            )

        # --- Step 2: Debate - votazione ponderata per confidence ---
        vote_weights: Dict[str, float] = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        for sig in signals:
            vote_weights[sig.action] = vote_weights.get(sig.action, 0.0) + sig.confidence

        total_weight = sum(vote_weights.values())
        winning_action = max(vote_weights, key=vote_weights.get)
        winning_weight = vote_weights[winning_action]
        consensus_confidence = winning_weight / total_weight if total_weight > 0 else 0.0

        # Calcola quorum: almeno 50% degli agenti concorda
        action_votes = Counter(s.action for s in signals)
        n_agents = len(signals)
        quorum_pct = action_votes[winning_action] / n_agents

        debate_lines = [
            f"Debate {symbol}: {n_agents} agenti",
            f"Voti: BUY={vote_weights['BUY']:.2f} SELL={vote_weights['SELL']:.2f} HOLD={vote_weights['HOLD']:.2f}",
            f"Vincitore: {winning_action} (weight={winning_weight:.2f}, quorum={quorum_pct:.0%})",
            f"Confidence consensus: {consensus_confidence:.2f}",
        ]

        # Penalizza se c'e' forte disaccordo
        if quorum_pct < 0.5 and n_agents > 1:
            consensus_confidence *= 0.7
            debate_lines.append("Penalita' disaccordo applicata (-30% confidence)")

        debate_summary = " | ".join(debate_lines)
        logger.info(f"[Supervisor] {debate_summary}")

        # --- Step 3: Valutazione Risk Engine ---
        if positions:
            self.risk_engine.update_portfolio(positions, portfolio_value)
        elif portfolio_value > 0:
            self.risk_engine.update_portfolio({}, portfolio_value)

        volatility = features.get("volatility_20d", 0.02)
        quantity = self.risk_engine.calculate_position_size(
            symbol=symbol,
            price=current_price,
            confidence=consensus_confidence,
            volatility=volatility,
        )

        risk_decision = self.risk_engine.evaluate(
            symbol=symbol,
            action=winning_action,
            quantity=quantity,
            price=current_price,
            features=features,
            confidence=consensus_confidence,
        )

        # --- Step 4: Risultato finale ---
        final_action = winning_action if risk_decision.approved else "HOLD"
        final_qty = risk_decision.quantity if risk_decision.approved else 0.0

        if not risk_decision.approved:
            debate_lines.append(f"BLOCCATO da RiskEngine: {risk_decision.reason}")
            debate_summary = " | ".join(debate_lines)
            logger.warning(f"[Supervisor] Trade BLOCCATO: {risk_decision.reason}")
        else:
            logger.info(
                f"[Supervisor] APPROVATO: {final_action} {final_qty:.4f} {symbol} "
                f"risk_score={risk_decision.risk_score}"
            )

        return DebateResult(
            symbol=symbol,
            final_action=final_action,
            final_confidence=round(consensus_confidence, 3),
            approved_by_risk=risk_decision.approved,
            risk_decision=risk_decision,
            signals=signals,
            debate_summary=debate_summary,
            timestamp=datetime.utcnow().isoformat(),
            quantity=final_qty,
        )

    def run_all_symbols(
        self,
        symbols: List[str],
        features_map: Dict[str, Dict[str, Any]],
        prices_map: Dict[str, float],
        portfolio_value: float = 0.0,
        positions: Optional[Dict[str, float]] = None,
    ) -> List[DebateResult]:
        """Esegue debate per tutti i simboli configurati."""
        results = []
        for symbol in symbols:
            if symbol not in features_map or symbol not in prices_map:
                logger.warning(f"[Supervisor] Dati mancanti per {symbol}, skip")
                continue
            result = self.run_debate(
                symbol=symbol,
                features=features_map[symbol],
                current_price=prices_map[symbol],
                portfolio_value=portfolio_value,
                positions=positions,
            )
            results.append(result)
        return results

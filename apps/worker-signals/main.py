"""Worker Signals - loop schedulato che genera segnali di trading per tutti i simboli."""
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any

from services.core.config import Config
from services.market_data.client import MarketDataClient
from services.feature_engine.indicators import get_latest_features
from services.agents.supervisor import SupervisorAgent
from services.risk_engine.engine import RiskEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker-signals")

SIGNAL_INTERVAL_SECONDS = int(os.getenv("SIGNAL_INTERVAL_SECONDS", "3600"))  # default: ogni ora


def fetch_all_features(config: Config, market_client: MarketDataClient) -> tuple:
    """Scarica dati e calcola features per tutti i simboli configurati."""
    features_map: Dict[str, Dict[str, Any]] = {}
    prices_map: Dict[str, float] = {}

    for symbol in config.get_symbols():
        try:
            df = market_client.get_daily_bars(symbol, period="1y")
            if df is None or df.empty:
                logger.warning(f"Nessun dato per {symbol}, skip")
                continue

            features = get_latest_features(df)
            if features is None:
                logger.warning(f"Feature computation fallita per {symbol}")
                continue

            price = features.get("close", 0.0)
            features_map[symbol] = features
            prices_map[symbol] = price
            logger.info(f"{symbol}: close={price:.2f} rsi={features.get('rsi_14', 'N/A')}")

        except Exception as e:
            logger.error(f"Errore fetch {symbol}: {e}")

    return features_map, prices_map


def run_signal_cycle(config: Config, supervisor: SupervisorAgent, market_client: MarketDataClient):
    """Esegue un ciclo di analisi completo per tutti i simboli."""
    logger.info(f"=== AVVIO CICLO SEGNALI: {datetime.utcnow().isoformat()} ===")

    features_map, prices_map = fetch_all_features(config, market_client)

    if not features_map:
        logger.warning("Nessuna feature disponibile, ciclo saltato")
        return

    symbols = list(features_map.keys())
    results = supervisor.run_all_symbols(
        symbols=symbols,
        features_map=features_map,
        prices_map=prices_map,
        portfolio_value=float(os.getenv("PORTFOLIO_VALUE", "10000")),
    )

    actionable = [r for r in results if r.final_action != "HOLD" and r.approved_by_risk]
    logger.info(f"Ciclo completato: {len(results)} simboli analizzati, {len(actionable)} segnali attivi")

    for r in results:
        status = "ATTIVO" if (r.final_action != "HOLD" and r.approved_by_risk) else "HOLD/BLOCCATO"
        logger.info(
            f"  {r.symbol}: {r.final_action} qty={r.quantity:.4f} "
            f"conf={r.final_confidence:.2f} [{status}]"
        )
        if r.risk_decision and not r.risk_decision.approved:
            logger.warning(f"    Risk block: {r.risk_decision.reason}")

    return results


def main():
    """Entry point principale del worker segnali."""
    logger.info("Worker Signals avviato")
    logger.info(f"Intervallo ciclo: {SIGNAL_INTERVAL_SECONDS}s")

    config = Config()
    market_client = MarketDataClient()
    risk_engine = RiskEngine()
    supervisor = SupervisorAgent(risk_engine=risk_engine)

    symbols = config.get_symbols()
    logger.info(f"Simboli configurati: {symbols}")

    cycle_count = 0
    while True:
        cycle_count += 1
        logger.info(f"--- Ciclo #{cycle_count} ---")

        # Reset contatori giornalieri a mezzanotte UTC
        hour = datetime.utcnow().hour
        if hour == 0 and cycle_count > 1:
            risk_engine.reset_daily_counters()
            logger.info("Contatori giornalieri resettati (mezzanotte UTC)")

        try:
            run_signal_cycle(config, supervisor, market_client)
        except Exception as e:
            logger.error(f"Errore nel ciclo #{cycle_count}: {e}", exc_info=True)

        logger.info(f"Prossimo ciclo tra {SIGNAL_INTERVAL_SECONDS}s...")
        time.sleep(SIGNAL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

"""Worker Execution - esegue ordini di trading su Alpaca (paper trading)."""
import logging
import time
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("worker-execution")

PAPER_MODE = os.getenv("TRADING_MODE", "paper").lower() == "paper"
ALPACA_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    action: str
    quantity: float
    status: str
    filled_price: Optional[float]
    error: Optional[str]
    timestamp: str
    paper: bool


class AlpacaExecutor:
    """Adattatore per esecuzione ordini su Alpaca (paper e live)."""

    def __init__(self):
        self.paper = PAPER_MODE
        self.client = None
        self._init_client()

    def _init_client(self):
        if not ALPACA_KEY or not ALPACA_SECRET:
            logger.warning("Credenziali Alpaca non configurate. Modalita' DRY RUN attiva.")
            return
        try:
            import alpaca_trade_api as tradeapi
            self.client = tradeapi.REST(
                ALPACA_KEY,
                ALPACA_SECRET,
                base_url=ALPACA_BASE_URL,
            )
            account = self.client.get_account()
            logger.info(
                f"Alpaca connesso: account={account.id} "
                f"equity={account.equity} paper={self.paper}"
            )
        except ImportError:
            logger.warning("alpaca-trade-api non installato. Modalita' DRY RUN.")
        except Exception as e:
            logger.error(f"Errore connessione Alpaca: {e}")

    def get_portfolio_value(self) -> float:
        if not self.client:
            return float(os.getenv("PORTFOLIO_VALUE", "10000"))
        try:
            account = self.client.get_account()
            return float(account.portfolio_value)
        except Exception as e:
            logger.error(f"Errore get_portfolio_value: {e}")
            return 0.0

    def get_positions(self) -> dict:
        if not self.client:
            return {}
        try:
            positions = self.client.list_positions()
            return {p.symbol: float(p.qty) for p in positions}
        except Exception as e:
            logger.error(f"Errore get_positions: {e}")
            return {}

    def submit_order(
        self,
        symbol: str,
        action: str,
        quantity: float,
    ) -> OrderResult:
        """Invia un ordine a mercato. Modalita' DRY RUN se client non disponibile."""
        ts = datetime.utcnow().isoformat()
        action = action.upper()

        if quantity <= 0:
            return OrderResult(
                order_id="", symbol=symbol, action=action, quantity=quantity,
                status="REJECTED", filled_price=None,
                error="Quantita' non valida", timestamp=ts, paper=self.paper
            )

        # DRY RUN
        if not self.client:
            fake_id = f"DRY-{symbol}-{int(time.time())}"
            logger.info(
                f"[DRY RUN] {action} {quantity:.4f} {symbol} - ordine simulato id={fake_id}"
            )
            return OrderResult(
                order_id=fake_id, symbol=symbol, action=action, quantity=quantity,
                status="SIMULATED", filled_price=None,
                error=None, timestamp=ts, paper=True
            )

        # Esecuzione reale su Alpaca
        try:
            side = "buy" if action == "BUY" else "sell"
            order = self.client.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                type="market",
                time_in_force="day",
            )
            logger.info(
                f"[Alpaca] Ordine inviato: {action} {quantity:.4f} {symbol} "
                f"id={order.id} status={order.status}"
            )
            return OrderResult(
                order_id=order.id,
                symbol=symbol,
                action=action,
                quantity=float(order.qty),
                status=order.status.upper(),
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                error=None,
                timestamp=ts,
                paper=self.paper,
            )
        except Exception as e:
            logger.error(f"Errore submit_order {symbol}: {e}")
            return OrderResult(
                order_id="", symbol=symbol, action=action, quantity=quantity,
                status="ERROR", filled_price=None,
                error=str(e), timestamp=ts, paper=self.paper
            )

    def cancel_all_orders(self):
        """Cancella tutti gli ordini aperti (safety net)."""
        if not self.client:
            return
        try:
            self.client.cancel_all_orders()
            logger.info("Tutti gli ordini aperti cancellati")
        except Exception as e:
            logger.error(f"Errore cancel_all_orders: {e}")


def main():
    """Entry point del worker esecuzione."""
    logger.info(f"Worker Execution avviato | paper={PAPER_MODE}")

    if not PAPER_MODE:
        logger.critical(
            "ATTENZIONE: modalita' LIVE attiva! "
            "Assicurarsi che tutto sia testato in paper prima."
        )

    executor = AlpacaExecutor()

    # Heartbeat loop - in produzione riceve segnali da una queue/DB
    while True:
        portfolio = executor.get_portfolio_value()
        positions = executor.get_positions()
        logger.info(
            f"Heartbeat: portfolio={portfolio:.2f} "
            f"posizioni aperte={len(positions)}"
        )
        if positions:
            for sym, qty in positions.items():
                logger.info(f"  {sym}: {qty:.4f} shares")

        # TODO: leggere segnali dalla coda/DB e eseguire ordini
        # Esempio di integrazione futura:
        # signals = read_pending_signals_from_db()
        # for signal in signals:
        #     if signal.approved_by_risk and signal.action != 'HOLD':
        #         result = executor.submit_order(signal.symbol, signal.action, signal.quantity)
        #         log_order_to_db(result)

        time.sleep(60)  # check ogni minuto


if __name__ == "__main__":
    main()

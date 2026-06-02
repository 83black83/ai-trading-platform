"""Telegram Bot - notifiche e comandi per la piattaforma di trading."""
import logging
import os
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class TelegramNotifier:
    """
    Notificatore Telegram con fallback graceful se il token non e' configurato.
    Supporta notifiche per: segnali, ordini, errori, status del sistema.
    """

    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.bot = None
        self._init_bot()

    def _init_bot(self):
        if not self.token or not self.chat_id:
            logger.warning("Telegram non configurato (TOKEN o CHAT_ID mancanti). Notifiche disabilitate.")
            return
        try:
            import telegram
            self.bot = telegram.Bot(token=self.token)
            logger.info("Telegram Bot inizializzato")
        except ImportError:
            logger.warning("python-telegram-bot non installato. Notifiche Telegram disabilitate.")
        except Exception as e:
            logger.error(f"Errore inizializzazione Telegram: {e}")

    def _send(self, message: str, parse_mode: str = "HTML") -> bool:
        """Invia un messaggio. Ritorna True se successo."""
        if not self.bot:
            logger.info(f"[TELEGRAM-DRY] {message}")
            return False
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Errore invio Telegram: {e}")
            return False

    def notify_signal(
        self,
        symbol: str,
        action: str,
        confidence: float,
        quantity: float,
        price: float,
        debate_summary: str,
        approved: bool,
    ) -> bool:
        """Notifica un segnale di trading generato."""
        emoji = {"BUY": "SEGNALE BUY", "SELL": "SEGNALE SELL", "HOLD": "HOLD"}.get(action, action)
        status = "APPROVATO" if approved else "BLOCCATO da Risk Engine"

        msg = (
            f"<b>{emoji} - {symbol}</b>\n"
            f"Azione: <code>{action}</code>\n"
            f"Quantita': <code>{quantity:.4f}</code>\n"
            f"Prezzo: <code>${price:.2f}</code>\n"
            f"Confidence: <code>{confidence:.1%}</code>\n"
            f"Status: <b>{status}</b>\n"
            f"<i>{debate_summary[:200]}</i>\n"
            f"Ore: {datetime.utcnow().strftime('%H:%M UTC')}"
        )
        return self._send(msg)

    def notify_order_filled(
        self,
        symbol: str,
        action: str,
        quantity: float,
        filled_price: Optional[float],
        order_id: str,
        paper: bool,
    ) -> bool:
        """Notifica esecuzione ordine."""
        mode = "PAPER" if paper else "LIVE"
        price_str = f"${filled_price:.2f}" if filled_price else "market"
        value = quantity * (filled_price or 0)

        msg = (
            f"<b>ORDINE ESEGUITO [{mode}]</b>\n"
            f"{action} <code>{quantity:.4f} {symbol}</code>\n"
            f"Prezzo fill: <code>{price_str}</code>\n"
            f"Valore: <code>${value:.2f}</code>\n"
            f"ID: <code>{order_id}</code>\n"
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        return self._send(msg)

    def notify_error(self, component: str, error: str) -> bool:
        """Notifica errore critico."""
        msg = (
            f"<b>ERRORE - {component}</b>\n"
            f"<code>{error[:500]}</code>\n"
            f"{datetime.utcnow().strftime('%H:%M UTC')}"
        )
        return self._send(msg)

    def notify_status(
        self,
        portfolio_value: float,
        n_positions: int,
        daily_pnl: float,
        n_trades_today: int,
    ) -> bool:
        """Report di status giornaliero."""
        pnl_emoji = "su" if daily_pnl >= 0 else "giu"
        pnl_pct = (daily_pnl / portfolio_value * 100) if portfolio_value > 0 else 0

        msg = (
            f"<b>STATUS GIORNALIERO</b>\n"
            f"Portfolio: <code>${portfolio_value:,.2f}</code>\n"
            f"P&L oggi: <code>{'+' if daily_pnl>=0 else ''}{daily_pnl:.2f} ({pnl_pct:+.2f}%)</code> {pnl_emoji}\n"
            f"Posizioni aperte: <code>{n_positions}</code>\n"
            f"Trade oggi: <code>{n_trades_today}</code>\n"
            f"{datetime.utcnow().strftime('%Y-%m-%d')}"
        )
        return self._send(msg)

    def notify_system_start(self, paper_mode: bool) -> bool:
        """Notifica avvio sistema."""
        mode = "PAPER TRADING" if paper_mode else "LIVE TRADING"
        msg = (
            f"<b>Sistema AI Trading avviato</b>\n"
            f"Modalita': <b>{mode}</b>\n"
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        return self._send(msg)

    def notify_system_stop(self, reason: str = "Shutdown normale") -> bool:
        """Notifica arresto sistema."""
        msg = (
            f"<b>Sistema AI Trading ARRESTATO</b>\n"
            f"Motivo: {reason}\n"
            f"{datetime.utcnow().strftime('%H:%M UTC')}"
        )
        return self._send(msg)


# Singleton per uso globale
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """Restituisce l'istanza singleton del notificatore."""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


if __name__ == "__main__":
    # Test rapido
    logging.basicConfig(level=logging.INFO)
    notifier = get_notifier()
    notifier.notify_status(
        portfolio_value=10000.0,
        n_positions=2,
        daily_pnl=45.50,
        n_trades_today=3,
    )

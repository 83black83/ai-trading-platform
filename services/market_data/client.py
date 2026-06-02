"""
Market Data Client - AI Trading Platform
Acquisisce prezzi OHLCV storici e real-time da Alpaca.
Fallback su Yahoo Finance se Alpaca non disponibile.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from services.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MarketDataClient:
    """Client per acquisizione dati di mercato."""

    def __init__(self):
        self._alpaca_client = None
        self._init_alpaca()

    def _init_alpaca(self):
        """Inizializza client Alpaca se API key disponibile."""
        if settings.ALPACA_API_KEY:
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                self._alpaca_client = StockHistoricalDataClient(
                    api_key=settings.ALPACA_API_KEY,
                    secret_key=settings.ALPACA_API_SECRET,
                )
                logger.info("Alpaca client inizializzato")
            except Exception as e:
                logger.warning(f"Alpaca non disponibile: {e}. Uso Yahoo Finance.")

    def get_historical_bars(
        self,
        symbol: str,
        days: int = 90,
    ) -> pd.DataFrame:
        """
        Restituisce DataFrame OHLCV per il simbolo indicato.
        Tenta prima Alpaca, poi fallback su Yahoo Finance.
        """
        if self._alpaca_client:
            try:
                return self._get_alpaca_bars(symbol, days)
            except Exception as e:
                logger.warning(f"Alpaca bars fallito per {symbol}: {e}. Uso yfinance.")

        return self._get_yfinance_bars(symbol, days)

    def _get_alpaca_bars(self, symbol: str, days: int) -> pd.DataFrame:
        """Recupera barre da Alpaca."""
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.utcnow() - timedelta(days=days),
            end=datetime.utcnow(),
        )
        bars = self._alpaca_client.get_stock_bars(request)
        df = bars.df
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level=0)
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                                 "close": "Close", "volume": "Volume",
                                 "vwap": "VWAP"})
        logger.info(f"Alpaca: {len(df)} barre per {symbol}")
        return df

    def _get_yfinance_bars(self, symbol: str, days: int) -> pd.DataFrame:
        """Recupera barre da Yahoo Finance."""
        period = f"{days}d"
        df = yf.download(symbol, period=period, interval="1d", progress=False)
        if df.empty:
            raise ValueError(f"Nessun dato disponibile per {symbol}")
        logger.info(f"yfinance: {len(df)} barre per {symbol}")
        return df

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Restituisce l'ultimo prezzo disponibile."""
        try:
            df = self.get_historical_bars(symbol, days=5)
            if not df.empty:
                return float(df["Close"].iloc[-1])
        except Exception as e:
            logger.error(f"Errore get_latest_price {symbol}: {e}")
        return None

    def get_multiple_bars(
        self, symbols: List[str], days: int = 90
    ) -> Dict[str, pd.DataFrame]:
        """Recupera barre per multipli simboli."""
        result = {}
        for symbol in symbols:
            try:
                result[symbol] = self.get_historical_bars(symbol, days)
            except Exception as e:
                logger.error(f"Errore dati {symbol}: {e}")
        return result


# Singleton
_client: Optional[MarketDataClient] = None


def get_market_data_client() -> MarketDataClient:
    global _client
    if _client is None:
        _client = MarketDataClient()
    return _client

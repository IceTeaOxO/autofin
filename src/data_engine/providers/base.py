from abc import ABC, abstractmethod
import pandas as pd

class BaseProvider(ABC):
    @abstractmethod
    def fetch_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch OHLCV data for a list of tickers.
        Returns a DataFrame with columns: [timestamp, ticker, open, high, low, close, volume]
        """
        pass

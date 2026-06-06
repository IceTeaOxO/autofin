import numpy as np
import pandas as pd

class Processor:
    @staticmethod
    def clean_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the raw OHLCV data.
        - Removes duplicates.
        - Forward fills missing values per ticker.
        """
        if df.empty:
            return df
            
        # 1. Remove duplicates
        df = df.drop_duplicates(subset=['timestamp', 'ticker'])
        
        # 2. Sort for proper filling
        df = df.sort_values(['ticker', 'timestamp'])
        
        # 3. Forward fill missing prices within each ticker
        # Note: group_keys=False is used for compatibility with newer pandas
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df.groupby('ticker')[col].ffill()
        
        # 4. Remove any rows that still have NaNs (at the start)
        df = df.dropna(subset=['close'])
        
        return df

    @staticmethod
    def calculate_log_returns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates log returns for each ticker in the dataframe.
        Input df expects columns: [timestamp, ticker, close]
        Output df columns: [timestamp, ticker, feature_name, value]
        """
        if df.empty:
            return pd.DataFrame()
            
        # Ensure data is sorted by timestamp
        df = df.sort_values(['ticker', 'timestamp'])
        
        # Group by ticker and calculate log returns
        df['prev_close'] = df.groupby('ticker')['close'].shift(1)
        df['value'] = np.log(df['close'] / df['prev_close'])
        
        # Clean up
        df = df.dropna(subset=['value'])
        df['feature_name'] = 'log_return'
        
        return df[['timestamp', 'ticker', 'feature_name', 'value']]

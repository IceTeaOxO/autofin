import pandas as pd
import numpy as np
from factor_factory.utils import FactorUtils

class MomentumFactor:
    def __init__(self, windows=[20, 60]):
        self.windows = windows

    def calculate(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Momentum factor (Cross-sectional Return ranking).
        """
        results = []
        df = price_df.copy()
        df = df.sort_values(['ticker', 'timestamp'])
        
        for window in self.windows:
            # Group by ticker and calculate percentage change
            df_ret = df.copy()
            df_ret['ret'] = df_ret.groupby('ticker')['close'].pct_change(window, fill_method=None)
            
            # Cross-sectional rank per timestamp
            df_ret['value'] = df_ret.groupby('timestamp')['ret'].transform(FactorUtils.rank)
            df_ret['factor_name'] = f'mom_{window}'
            results.append(df_ret[['timestamp', 'ticker', 'factor_name', 'value']])
            
        return pd.concat(results).dropna()

class MeanReversionFactor:
    def __init__(self, window=20):
        self.window = window

    def calculate(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Mean Reversion (Z-Score of price relative to rolling mean).
        """
        df = price_df.copy()
        df = df.sort_values(['ticker', 'timestamp'])
        
        # Calculate Rolling Z-Score
        def get_zscore(x):
            if len(x) < self.window: return np.nan
            std = x.std()
            if std == 0: return 0
            return (x.iloc[-1] - x.mean()) / std

        df['zscore'] = df.groupby('ticker')['close'].transform(
            lambda x: x.rolling(self.window).apply(get_zscore)
        )
        
        df['value'] = df['zscore'].clip(-3, 3) # Winsorize
        df['factor_name'] = f'rev_{self.window}'
        
        return df[['timestamp', 'ticker', 'factor_name', 'value']].dropna()

class VolatilityFactor:
    def __init__(self, window=30):
        self.window = window

    def calculate(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Volatility factor (Annualized STD of returns).
        """
        df = price_df.copy()
        df = df.sort_values(['ticker', 'timestamp'])
        df['ret'] = df.groupby('ticker')['close'].pct_change(fill_method=None)
        
        # 252 trading days in a year
        df['vol'] = df.groupby('ticker')['ret'].transform(
            lambda x: x.rolling(self.window).std() * np.sqrt(252)
        )
        
        df['value'] = df['vol']
        df['factor_name'] = f'vol_{self.window}'
        
        return df[['timestamp', 'ticker', 'factor_name', 'value']].dropna()

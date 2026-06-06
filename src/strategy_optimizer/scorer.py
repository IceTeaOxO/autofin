import pandas as pd
import numpy as np

class Scorer:
    """
    Base class for robust factor scoring.
    """
    @staticmethod
    def winsorize(df: pd.DataFrame, column: str = 'value', limits=(0.01, 0.01)) -> pd.DataFrame:
        """
        Clips extreme values at specified percentiles.
        """
        res = df.copy()
        lower = res[column].quantile(limits[0])
        upper = res[column].quantile(1 - limits[1])
        res[column] = res[column].clip(lower, upper)
        return res

    @staticmethod
    def rank_standardize(df: pd.DataFrame, column: str = 'value') -> pd.DataFrame:
        """
        Converts values to cross-sectional ranks scaled between -1 and 1.
        """
        res = df.copy()
        # Group by timestamp to ensure cross-sectional ranking
        res[column] = res.groupby('timestamp')[column].rank(pct=True)
        res[column] = (res[column] - 0.5) * 2
        return res

    @staticmethod
    def zscore_standardize(df: pd.DataFrame, column: str = 'value') -> pd.DataFrame:
        """
        Performs cross-sectional Z-score standardization.
        """
        res = df.copy()
        def get_zscore(x):
            std = x.std()
            if std == 0 or np.isnan(std): return x - x.mean()
            return (x - x.mean()) / std
            
        res[column] = res.groupby('timestamp')[column].transform(get_zscore)
        return res

    @classmethod
    def process_scores(cls, df: pd.DataFrame, method: str = 'rank') -> pd.DataFrame:
        """
        Pipeline to clean and standardize scores.
        """
        if df.empty: return df
        
        # 1. Winsorize first to remove impact of extreme outliers on mean/std
        df = cls.winsorize(df)
        
        # 2. Standardize
        if method == 'rank':
            df = cls.rank_standardize(df)
        elif method == 'zscore':
            df = cls.zscore_standardize(df)
            
        return df

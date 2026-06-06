import pandas as pd
import numpy as np

class FactorUtils:
    @staticmethod
    def standardize(series: pd.Series) -> pd.Series:
        """
        Z-Score standardization (winsorized at 3 std).
        """
        mu = series.mean()
        sigma = series.std()
        if sigma == 0:
            return series * 0
        
        z = (series - mu) / sigma
        return z.clip(-3, 3)

    @staticmethod
    def rank(series: pd.Series) -> pd.Series:
        """
        Cross-sectional ranking (0 to 1).
        """
        return series.rank(pct=True)

    @staticmethod
    def neutralize(df: pd.DataFrame, factor_col: str, group_col: str = None) -> pd.Series:
        """
        Neutralizes a factor by removing the mean of the group (e.g., sector).
        If no group_col, removes the global mean (market neutral).
        """
        if group_col and group_col in df.columns:
            return df.groupby(group_col)[factor_col].transform(lambda x: x - x.mean())
        else:
            return df[factor_col] - df[factor_col].mean()

import pandas as pd
import numpy as np
from scipy.stats import spearmanr

class ICAnalyzer:
    """
    Analyzes the predictive power of factors using Information Coefficients.
    """
    
    @staticmethod
    def calculate_forward_returns(price_df: pd.DataFrame, period: int = 1) -> pd.DataFrame:
        """
        Calculates forward returns for a given period.
        Aligns return at T+period with timestamp T.
        """
        df = price_df.copy()
        df = df.sort_values(['ticker', 'timestamp'])
        
        # Calculate log returns for the period
        df['ret'] = df.groupby('ticker')['close'].pct_change(period)
        
        # Shift returns back to align with factor at time T
        # Example: return from T to T+1 is shifted to T
        df['fwd_ret'] = df.groupby('ticker')['ret'].shift(-period)
        
        return df[['timestamp', 'ticker', 'fwd_ret']].dropna()

    @staticmethod
    def calculate_rank_ic(factor_df: pd.DataFrame, return_df: pd.DataFrame) -> pd.Series:
        """
        Calculates Spearman Rank IC between factors and forward returns.
        Expects factor_df in long format with [timestamp, ticker, factor_name, value].
        """
        # Merge factor and returns
        merged = pd.merge(factor_df, return_df, on=['timestamp', 'ticker'])
        
        if merged.empty:
            return pd.Series()

        def spearman_ic(group):
            if len(group) < 2: return np.nan
            # Spearman correlation between factor value and forward return
            corr, _ = spearmanr(group['value'], group['fwd_ret'])
            return corr

        # Calculate IC for each timestamp and factor_name
        ic_series = merged.groupby(['timestamp', 'factor_name']).apply(spearman_ic)
        return ic_series

    @classmethod
    def get_summary_stats(cls, ic_series: pd.Series) -> pd.DataFrame:
        """
        Calculates summary statistics for the IC series: Mean IC, Std IC, and IR.
        """
        if ic_series.empty:
            return pd.DataFrame()
            
        # Group by factor_name (level 1 in the index)
        summary = ic_series.groupby(level=1).agg(['mean', 'std'])
        summary.columns = ['mean_ic', 'std_ic']
        
        # IR = Mean IC / Std IC (Stability of the factor)
        summary['ir'] = summary['mean_ic'] / summary['std_ic']
        
        return summary

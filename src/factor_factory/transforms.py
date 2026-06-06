import numpy as np
import pandas as pd
from factor_factory.stats import StatsAnalyzer

class Transformers:
    @staticmethod
    def get_weights_ffd(d: float, thres: float, size: int) -> np.array:
        """
        Computes weights for Fixed Window Fractional Differentiation (FFD).
        """
        w = [1.0]
        for k in range(1, size):
            w_next = -w[-1] * ((d - k + 1) / k)
            if abs(w_next) < thres:
                break
            w.append(w_next)
        w = np.array(w[::-1]).reshape(-1, 1)
        return w

    @staticmethod
    def frac_diff_ffd(series: pd.Series, d: float, thres: float = 1e-4) -> pd.Series:
        """
        Applies Fixed Window Fractional Differentiation (FFD).
        Ensures stationarity while preserving memory.
        """
        series_filled = series.ffill().dropna()
        if len(series_filled) < 2:
            return series * np.nan
            
        w = Transformers.get_weights_ffd(d, thres, len(series_filled))
        width = len(w) - 1
        
        output = {}
        for i in range(width, len(series_filled)):
            loc = series_filled.index[i]
            # Dot product of weights and slice of series
            output[loc] = np.dot(w.T, series_filled.iloc[i-width:i+1].values.reshape(-1, 1))[0,0]
            
        return pd.Series(output, name=series.name)

    @staticmethod
    def find_optimal_d(series: pd.Series, ds: np.array = None) -> float:
        """
        Iterates through d values to find the minimum d that makes the series stationary.
        """
        if ds is None:
            ds = np.linspace(0, 1, 11) # 0.0, 0.1, ..., 1.0
            
        analyzer = StatsAnalyzer()
        
        for d in ds:
            diff_series = Transformers.frac_diff_ffd(series, d)
            if len(diff_series.dropna()) < 20: # Minimum sample size for ADF
                continue
            
            res = analyzer.run_adf_test(diff_series)
            if res['stationary']:
                return float(d)
                
        return 1.0 # Default to first order difference if no d found

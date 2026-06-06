import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

class StatsAnalyzer:
    @staticmethod
    def run_adf_test(series: pd.Series) -> dict:
        """
        Runs Augmented Dickey-Fuller test on a series.
        """
        if len(series) < 20: # Minimum sample size
            return {"stationary": False, "p_value": 1.0, "error": "Insufficient data"}
            
        try:
            result = adfuller(series.dropna())
            return {
                "stationary": result[1] < 0.05,
                "p_value": result[1],
                "t_stat": result[0],
                "crit_values": result[4]
            }
        except Exception as e:
            return {"stationary": False, "p_value": 1.0, "error": str(e)}

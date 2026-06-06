import pandas as pd
import numpy as np

class Backtester:
    """
    Simulates strategy performance using vectorized operations with realistic constraints.
    """
    
    @staticmethod
    def calculate_strategy_returns(weight_df: pd.DataFrame, 
                                   return_df: pd.DataFrame, 
                                   tc: float = 0.001) -> pd.DataFrame:
        """
        Calculates daily strategy returns including transaction costs.
        - weight_df: [timestamp, ticker, weight]
        - return_df: [timestamp, ticker, fwd_ret]
        - tc: Transaction cost (0.001 = 0.1%)
        """
        # Align weights with returns
        merged = pd.merge(weight_df, return_df, on=['timestamp', 'ticker'])
        
        if merged.empty:
            return pd.DataFrame()

        # 1. Calculate Gross Returns
        merged['gross_ret'] = merged['weight'] * merged['fwd_ret']
        daily_gross = merged.groupby('timestamp')['gross_ret'].sum()
        
        # 2. Calculate Turnover & Transaction Costs
        # Pivot weights to calculate daily changes
        weights_pivot = weight_df.pivot(index='timestamp', columns='ticker', values='weight').fillna(0)
        daily_diff = weights_pivot.diff().abs().sum(axis=1)
        # Initial turnover on day 1
        daily_diff.iloc[0] = weights_pivot.iloc[0].sum()
        
        daily_tc = daily_diff * tc
        
        # 3. Net Returns
        daily_net = daily_gross - daily_tc
        
        res = pd.DataFrame({
            'gross_return': daily_gross,
            'turnover': daily_diff,
            'transaction_cost': daily_tc,
            'net_return': daily_net
        })
        
        return res

    @staticmethod
    def calculate_performance_metrics(results: pd.DataFrame) -> dict:
        """
        Calculates comprehensive performance metrics.
        """
        if results.empty:
            return {}

        rets = results['net_return'].fillna(0)
        
        # 1. Cumulative Returns
        cum_rets = (1 + rets).cumprod()
        if len(cum_rets) > 0:
            total_ret = cum_rets.iloc[-1] - 1
        else:
            total_ret = 0
        
        # 2. Annualized Stats
        ann_ret = rets.mean() * 252
        ann_vol = rets.std() * np.sqrt(252)
        sharpe = ann_ret / ann_vol if ann_vol != 0 else 0
        
        # 3. Maximum Drawdown
        peak = cum_rets.expanding(min_periods=1).max()
        drawdown = (cum_rets / peak) - 1
        max_dd = drawdown.min()
        
        # 4. Calmar Ratio
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
        
        # 5. Average Turnover
        avg_turnover = results['turnover'].mean()
        
        return {
            "Total Net Return": f"{total_ret:.2%}",
            "Annualized Net Return": f"{ann_ret:.2%}",
            "Annualized Volatility": f"{ann_vol:.2%}",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Calmar Ratio": f"{calmar:.2f}",
            "Max Drawdown": f"{max_dd:.2%}",
            "Avg Daily Turnover": f"{avg_turnover:.2%}"
        }

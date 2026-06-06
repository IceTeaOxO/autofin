import pandas as pd
import numpy as np

class Allocator:
    """
    Handles asset allocation logic with risk management and constraints.
    """
    
    @staticmethod
    def calculate_inverse_vol_weights(price_df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
        """
        Calculates weights based on inverse historical volatility.
        Higher volatility assets get lower weights.
        """
        df = price_df.copy()
        df = df.sort_values(['ticker', 'timestamp'])
        
        # Calculate daily returns
        df['ret'] = df.groupby('ticker')['close'].pct_change()
        
        # Calculate rolling volatility (annualized)
        df['vol'] = df.groupby('ticker')['ret'].transform(
            lambda x: x.rolling(window).std() * np.sqrt(252)
        )
        
        # Get latest volatility per ticker for cross-sectional weighting
        # For backtesting, we need this daily.
        def get_inv_vol_weights(group):
            vols = group['vol']
            if vols.isna().all(): return group.assign(weight=0)
            
            # Inverse Volatility
            inv_vol = 1.0 / vols.replace(0, np.nan)
            weights = inv_vol / inv_vol.sum()
            return group.assign(risk_weight=weights.fillna(0))

        df = df.groupby('timestamp', group_keys=False).apply(get_inv_vol_weights)
        return df[['timestamp', 'ticker', 'risk_weight']]

    @classmethod
    def allocate_weights(cls, 
                         signal_df: pd.DataFrame, 
                         risk_weight_df: pd.DataFrame, 
                         max_weight: float = 0.2) -> pd.DataFrame:
        """
        Combines Alpha signals with Risk weights and applies constraints.
        - signal_df: [timestamp, ticker, value] (Alpha)
        - risk_weight_df: [timestamp, ticker, risk_weight] (Beta)
        """
        # Merge signal and risk weights
        merged = pd.merge(signal_df, risk_weight_df, on=['timestamp', 'ticker'])
        
        # Final Score = Signal * Risk Weight
        # We ensure signal is positive for long-only allocation
        merged['raw_score'] = merged['value'].clip(lower=0) * merged['risk_weight']
        
        def apply_constraints(group):
            # 1. Initial normalization
            total_score = group['raw_score'].sum()
            if total_score == 0: return group.assign(weight=0)
            
            weights = group['raw_score'] / total_score
            
            # 2. Clip weights at max_weight (e.g., 20%)
            weights = weights.clip(upper=max_weight)
            
            # 3. Re-normalize after clipping
            weights = weights / weights.sum()
            
            return group.assign(weight=weights)

        final_df = merged.groupby('timestamp', group_keys=False).apply(apply_constraints)
        return final_df[['timestamp', 'ticker', 'weight']]

    @staticmethod
    def apply_rebalance_buffer(weight_df: pd.DataFrame, 
                               threshold: float = 0.05,
                               vol_series: pd.Series = None) -> pd.DataFrame:
        """
        Applies a persistence buffer to weights to reduce turnover.
        - threshold: Base threshold.
        - vol_series: Optional market volatility series to scale threshold.
        """
        if weight_df.empty: return weight_df

        # Pivot weights for time-series iteration
        pivot_weights = weight_df.pivot(index='timestamp', columns='ticker', values='weight').fillna(0)
        buffered_weights = pivot_weights.copy()

        # Calculate dynamic threshold factor if vol_series is provided
        # Threshold = Base * (Current_Vol / Median_Vol)
        thresh_factor = pd.Series(1.0, index=pivot_weights.index)
        if vol_series is not None:
            # Reindex vol_series to match pivot_weights
            vol_aligned = vol_series.reindex(pivot_weights.index).ffill()
            median_vol = vol_aligned.median()
            if median_vol > 0:
                thresh_factor = vol_aligned / median_vol

        # Iterate through dates starting from the second row
        for i in range(1, len(pivot_weights)):
            prev_weights = buffered_weights.iloc[i-1]
            target_weights = pivot_weights.iloc[i]

            # Scaled threshold for this specific day
            daily_threshold = threshold * thresh_factor.iloc[i]

            # Check if any ticker's weight change exceeds daily_threshold
            diff = (target_weights - prev_weights).abs()

            if (diff > daily_threshold).any():
                # Rebalance: use target weights
                buffered_weights.iloc[i] = target_weights
            else:
                # Buffer: keep previous weights
                buffered_weights.iloc[i] = prev_weights

        # Melt back to long format
        res = buffered_weights.reset_index().melt(id_vars='timestamp', var_name='ticker', value_name='weight')
        return res.sort_values(['timestamp', 'ticker'])


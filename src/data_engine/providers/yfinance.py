import yfinance as yf
import pandas as pd
from .base import BaseProvider

class YFinanceProvider(BaseProvider):
    def fetch_data(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        if not tickers:
            return pd.DataFrame()
            
        # Fetch data
        df = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=True, threads=False)
        
        if df.empty:
            return pd.DataFrame()
            
        all_data = []
        
        # Handle single vs multiple tickers in yfinance output
        if len(tickers) == 1:
            ticker = tickers[0]
            temp_df = df.copy()
            # If yf returns MultiIndex for single ticker
            if isinstance(temp_df.columns, pd.MultiIndex):
                temp_df.columns = temp_df.columns.get_level_values(-1)
            temp_df['ticker'] = ticker
            temp_df = temp_df.reset_index()
            all_data.append(temp_df)
        else:
            for ticker in tickers:
                # Check if ticker exists in columns
                if isinstance(df.columns, pd.MultiIndex):
                    if ticker in df.columns.levels[0]:
                        temp_df = df[ticker].copy()
                        temp_df['ticker'] = ticker
                        temp_df = temp_df.reset_index()
                        all_data.append(temp_df)
                else:
                    # Single level columns but multiple tickers (rare with group_by='ticker')
                    if ticker in df.columns:
                        temp_df = df[[ticker]].copy()
                        temp_df['ticker'] = ticker
                        temp_df = temp_df.reset_index()
                        all_data.append(temp_df)
        
        if not all_data:
            return pd.DataFrame()
            
        final_df = pd.concat(all_data)
        
        # Flatten columns if they are still tuples
        final_df.columns = [col[0] if isinstance(col, tuple) else col for col in final_df.columns]
        final_df.columns = [str(col).lower() for col in final_df.columns]
        # Rename 'date' to 'timestamp' if it exists
        if 'date' in final_df.columns:
            final_df = final_df.rename(columns={'date': 'timestamp'})
            
        # Ensure standard columns exist
        expected_cols = ['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        return final_df[expected_cols]

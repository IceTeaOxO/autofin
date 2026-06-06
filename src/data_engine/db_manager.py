import duckdb
import pandas as pd
import os

class DBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.connection() as conn:
            # Create raw_prices table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_prices (
                    timestamp TIMESTAMP,
                    ticker VARCHAR,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    PRIMARY KEY (timestamp, ticker)
                )
            """)
            
            # Create processed_data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_data (
                    timestamp TIMESTAMP,
                    ticker VARCHAR,
                    feature_name VARCHAR,
                    value DOUBLE,
                    PRIMARY KEY (timestamp, ticker, feature_name)
                )
            """)

            # Create factor_scores table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS factor_scores (
                    timestamp TIMESTAMP,
                    ticker VARCHAR,
                    factor_name VARCHAR,
                    value DOUBLE,
                    PRIMARY KEY (timestamp, ticker, factor_name)
                )
            """)

            # Add indices for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_ticker_time ON raw_prices (ticker, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_ticker_time ON factor_scores (ticker, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_name ON factor_scores (factor_name)")

    def save_raw_prices(self, df: pd.DataFrame):
        if df.empty:
            return
        
        with self.connection() as conn:
            conn.register('df_view', df)
            conn.execute("""
                INSERT OR IGNORE INTO raw_prices 
                SELECT * FROM df_view
            """)

    def save_processed_data(self, df: pd.DataFrame):
        if df.empty:
            return
            
        with self.connection() as conn:
            conn.register('df_view', df)
            conn.execute("""
                INSERT OR IGNORE INTO processed_data 
                SELECT timestamp, ticker, feature_name, value FROM df_view
            """)

    def save_factor_scores(self, df: pd.DataFrame):
        if df.empty:
            return
            
        with self.connection() as conn:
            conn.register('df_view', df)
            conn.execute("""
                INSERT OR IGNORE INTO factor_scores 
                SELECT timestamp, ticker, factor_name, value FROM df_view
            """)

    def get_raw_prices(self, tickers: list = None) -> pd.DataFrame:
        with self.connection() as conn:
            if tickers:
                tickers_str = "', '".join(tickers)
                query = f"SELECT * FROM raw_prices WHERE ticker IN ('{tickers_str}') ORDER BY timestamp"
            else:
                query = "SELECT * FROM raw_prices ORDER BY timestamp"
            return conn.execute(query).df()

    def get_latest_timestamp(self, ticker: str) -> pd.Timestamp:
        """
        Returns the latest timestamp for a given ticker in the raw_prices table.
        """
        with self.connection() as conn:
            res = conn.execute(f"SELECT max(timestamp) FROM raw_prices WHERE ticker = '{ticker}'").fetchone()
            return res[0] if res and res[0] else None

    def get_processed_data(self, tickers: list = None, feature_name: str = None) -> pd.DataFrame:
        with self.connection() as conn:
            query = "SELECT * FROM processed_data WHERE 1=1"
            if tickers:
                tickers_str = "', '".join(tickers)
                query += f" AND ticker IN ('{tickers_str}')"
            if feature_name:
                query += f" AND feature_name = '{feature_name}'"
            query += " ORDER BY timestamp"
            return conn.execute(query).df()

    def get_factor_matrix(self, tickers: list = None) -> pd.DataFrame:
        """
        Returns a wide-format matrix of factors (timestamp, ticker, factor1, factor2, ...)
        Uses DuckDB's PIVOT feature.
        """
        with self.connection() as conn:
            where_clause = ""
            if tickers:
                tickers_str = "', '".join(tickers)
                where_clause = f"WHERE ticker IN ('{tickers_str}')"
            
            query = f"""
                PIVOT (SELECT timestamp, ticker, factor_name, value FROM factor_scores {where_clause})
                ON factor_name
                USING first(value)
                GROUP BY timestamp, ticker
                ORDER BY timestamp, ticker
            """
            return conn.execute(query).df()

    def connection(self):
        return duckdb.connect(self.db_path)

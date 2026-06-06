import requests
import json
import logging
import pandas as pd

class Notifier:
    """
    Handles sending investment reports via the provided Email API.
    """
    def __init__(self, api_url: str, recipient: str):
        self.api_url = api_url
        self.recipient = recipient
        self.logger = logging.getLogger("Notifier")

    def format_html_report(self, metrics: dict, portfolio: list) -> str:
        """
        Formats performance metrics and target portfolio into an HTML report.
        """
        # 1. Performance Table
        metrics_html = "<h3>📊 策略績效事實表 (Performance Factsheet)</h3>"
        metrics_html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
        metrics_html += "<tr style='background-color: #f2f2f2;'><th>指標</th><th>數值</th></tr>"
        for k, v in metrics.items():
            metrics_html += f"<tr><td>{k}</td><td>{v}</td></tr>"
        metrics_html += "</table>"

        # 2. Portfolio Table
        portfolio_html = "<h3>🚀 最新目標持倉建議 (Target Portfolio)</h3>"
        portfolio_html += "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
        portfolio_html += "<tr style='background-color: #f2f2f2;'><th>代號 (Ticker)</th><th>建議權重 (Weight)</th></tr>"
        
        # Sort portfolio by weight descending
        sorted_port = sorted(portfolio, key=lambda x: x['weight'], reverse=True)
        for item in sorted_port:
            weight_str = f"{item['weight']:.2%}"
            color = "#e6fffa" if item['weight'] > 0 else "#ffffff"
            portfolio_html += f"<tr style='background-color: {color};'><td>{item['ticker']}</td><td>{weight_str}</td></tr>"
        portfolio_html += "</table>"

        # Combine
        full_html = f"""
        <html>
        <body style='font-family: sans-serif;'>
            <h2>📈 通用型自動理財系統 - 每日建議報告</h2>
            <hr>
            {metrics_html}
            <br>
            {portfolio_html}
            <br>
            <p style='color: #666; font-size: 0.8em;'>* 本報告由自動化系統根據統計模型產出，不構成投資建議。</p>
        </body>
        </html>
        """
        return full_html

    def send_report(self, metrics: dict, portfolio: list):
        """
        Sends the report via the Email API.
        """
        html_content = self.format_html_report(metrics, portfolio)
        
        payload = {
            "to": self.recipient,
            "subject": f"每日持倉建議 - {pd.Timestamp.now().strftime('%Y-%m-%d')}",
            "text": "請查看 HTML 版本報告。",
            "html": html_content
        }

        try:
            response = requests.post(
                self.api_url,
                headers={"accept": "application/json", "Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=10
            )
            if response.status_code == 200 or response.status_code == 201:
                self.logger.info("Email report sent successfully.")
            else:
                self.logger.error(f"Failed to send email. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")

# Note: We'll need pandas in main_strategy to pass the correct portfolio format

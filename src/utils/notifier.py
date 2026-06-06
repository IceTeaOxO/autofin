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
        Formats performance metrics and target portfolio into an HTML report with educational info.
        """
        # 0. Dynamic Commentary
        has_allocation = any(item['weight'] > 0.01 for item in portfolio)
        commentary = ""
        if not has_allocation:
            commentary = """
            <div style='background-color: #fff3cd; padding: 15px; border-left: 5px solid #ffc107; margin-bottom: 20px;'>
                <strong>🛡️ 系統防禦提醒：</strong><br>
                目前所有標的的統計得分均低於預期門檻。為了保護您的資本，系統已自動切換至 <strong>100% 空倉 (Cash)</strong> 狀態。這通常發生在市場波動劇烈或下行趨勢顯著時。
            </div>
            """
        else:
            commentary = """
            <div style='background-color: #d1ecf1; padding: 15px; border-left: 5px solid #17a2b8; margin-bottom: 20px;'>
                <strong>📈 策略執行中：</strong><br>
                系統已識別出具有統計優勢的投資機會。已根據<strong>風險平價 (Risk Parity)</strong> 原則分配權重，確保高波動標的不會過度影響組合穩定性。
            </div>
            """

        # 1. Performance Table
        metrics_html = "<h3>📊 策略績效事實表 (Performance Factsheet)</h3>"
        metrics_html += "<table border='1' cellpadding='8' style='border-collapse: collapse; width: 100%;'>"
        metrics_html += "<tr style='background-color: #f2f2f2;'><th>指標 (Metric)</th><th>數值 (Value)</th><th>解釋 (Description)</th></tr>"
        
        descriptions = {
            "Total Net Return": "扣除交易成本後的累積總報酬率。",
            "Annualized Net Return": "平均每年的淨報酬率。",
            "Annualized Volatility": "年化波動度，代表資產價格變動的劇烈程度。",
            "Sharpe Ratio": "夏普比率。每承擔一單位風險所能換取的超額回報，越高越好。",
            "Max Drawdown": "歷史最大回撤。從高峰到低谷的最大跌幅，代表最糟情況。",
            "Avg Daily Turnover": "平均每日換手率。代表系統調倉的頻率，受動態緩衝區控制。"
        }

        for k, v in metrics.items():
            desc = descriptions.get(k, "")
            metrics_html += f"<tr><td><b>{k}</b></td><td>{v}</td><td><small>{desc}</small></td></tr>"
        metrics_html += "</table>"

        # 2. Portfolio Table
        portfolio_html = "<h3>🚀 最新目標持倉建議 (Target Portfolio)</h3>"
        portfolio_html += "<table border='1' cellpadding='8' style='border-collapse: collapse; width: 100%;'>"
        portfolio_html += "<tr style='background-color: #f2f2f2;'><th>代號 (Ticker)</th><th>建議權重 (Weight)</th><th>操作狀態 (Status)</th></tr>"
        
        sorted_port = sorted(portfolio, key=lambda x: x['weight'], reverse=True)
        for item in sorted_port:
            weight = item['weight']
            weight_str = f"{weight:.2%}"
            status = "持有 / 買入" if weight > 0 else "空倉觀望"
            color = "#e6fffa" if weight > 0 else "#ffffff"
            portfolio_html += f"<tr style='background-color: {color};'><td>{item['ticker']}</td><td>{weight_str}</td><td>{status}</td></tr>"
        portfolio_html += "</table>"

        # 3. Strategy Glossary
        glossary_html = """
        <div style='background-color: #f8f9fa; padding: 15px; border: 1px solid #dee2e6; margin-top: 30px;'>
            <h4>📚 理財百科 (Strategy Glossary)</h4>
            <ul>
                <li><strong>分數階微分 (FracDiff)</strong>: 一種進階統計技術。它能在讓價格數據變為「平穩」（可預測）的同時，儘可能保留原始價格的「長期記憶」，適合捕捉長線趨勢。</li>
                <li><strong>動能因子 (Momentum)</strong>: 遵循「強者恆強」原則，選擇過去一段時間表現優於市場的標的。</li>
                <li><strong>均值回歸 (Mean Reversion)</strong>: 捕捉「過度反應」後的反彈機會。當價格跌幅異常過大時，系統會給予較高的回歸得分。</li>
                <li><strong>動態調倉緩衝區</strong>: 當建議權重變化不大時（例如僅改變 2%），系統會選擇不交易以節省手續費。只有顯著變化時才會觸發調倉。</li>
            </ul>
        </div>
        """

        # Combine
        full_html = f"""
        <html>
        <body style='font-family: sans-serif; color: #333; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px;'>
            <div style='text-align: center;'>
                <h1 style='color: #2c3e50;'>📈 通用型自動理財系統</h1>
                <p style='color: #7f8c8d;'>您的每日量化投資決策助手</p>
            </div>
            <hr style='border: 0; border-top: 1px solid #eee;'>
            {commentary}
            {metrics_html}
            <br>
            {portfolio_html}
            {glossary_html}
            <br>
            <p style='color: #95a5a6; font-size: 0.8em; text-align: center;'>
                執行時間: {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M:%S')} (Taipei Time)<br>
                * 本報告由自動化系統根據統計模型產出，不構成投資建議。投資有風險，入市需謹慎。
            </p>
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

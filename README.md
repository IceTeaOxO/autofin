# 📈 通用型自動理財系統 (Universal Automated Fin-Bot)

這是一個基於統計學原理開發的生產級自動化理財系統。它結合了進階特徵工程、風險平價配置與自動化郵件回報，旨在為投資者提供穩健、透明且低摩擦的量化投資建議。

## 🌟 核心特色

1.  **進階統計特徵**：
    *   **動態分數階微分 (Dynamic FracDiff)**：自動搜尋最佳微分階數，保留價格長期記憶的同時確保數據平穩性。
    *   **多因子合成**：整合動能 (Momentum)、均值回歸 (Mean Reversion) 與波動率因子，並透過 **IC/IR (信息比率)** 進行動態加權。
2.  **專業級風險控管**：
    *   **風險平價配置 (Risk Parity)**：根據標的波動度自動分配權重，降低單一高風險資產的衝擊。
    *   **動態調倉緩衝區 (Adaptive Buffer)**：隨市場波動度調整交易門檻，大幅減少無謂的換手與交易成本。
    *   **自動空倉避險**：當市場整體統計得分過低時，系統會自動切換至防禦模式（100% 現金）。
3.  **生產級自動化**：
    *   **Docker 容器化**：一鍵部署，支援持久化資料庫儲存。
    *   **智能排程**：每日美東時間 08:30 (開盤前一小時) 自動生成報告。
    *   **教育型報表**：寄送包含名詞解釋與策略評論的 HTML 精美郵件。

---

## 🚀 快速開始

### 1. 環境準備
確保已安裝 [Docker](https://www.docker.com/) 與 [Docker Compose](https://docs.docker.com/compose/)。

### 2. 啟動服務
在專案根目錄執行：
```bash
docker-compose up --build -d
```
系統將會在背景持續運行，並在每日美東時間 08:30 寄送報告。

---

## ⚡ 立即取得報告 (手動觸發)

如果你不想等到排程時間，有兩種方式可以立即獲得最新的投資建議：

### 方式 A：透過 Docker 指令立即執行
```bash
docker exec -it autofin-bot python3 src/scheduler.py --now
```

### 方式 B：啟動時立即執行
在 `docker-compose.yml` 或啟動命令中加入 `RUN_IMMEDIATELY=true`：
```bash
docker run -e RUN_IMMEDIATELY=true ... 
```

---

## ⚙️ 配置指南 (`config.yaml`)

你可以透過修改 `config.yaml` 來調整系統行為：

*   **`asset_pools`**: 定義追蹤的股票或加密貨幣代號。
*   **`factors`**: 調整因子計算窗口（如動能天數）。
*   **`rebalance_threshold`**: 設定調倉緩衝門檻（預設 5%）。
*   **環境變數**:
    *   `EMAIL_API_URL`: 郵件發送 API 地址。
    *   `EMAIL_RECIPIENT`: 接收報表的信箱。

---

## 🛠️ 系統架構

1.  **Data Engine**: 負責從 Yahoo Finance 抓取數據並存入 DuckDB。
2.  **Factor Factory**: 並行計算 20+ 個標的之複雜統計特徵。
3.  **Analysis Engine**: 執行因子有效性檢驗 (IC/IR) 並模擬歷史回測。
4.  **Strategy Optimizer**: 執行風險平價權重分配與緩衝區過濾。
5.  **Notifier**: 將決策結果格式化為 HTML 並寄送。

---
*免責聲明：本系統所有輸出均基於統計模型，僅供研究參考，不構成實際投資建議。*

# 名字
基於IoT之智慧居家防盜與遠端門禁控制系統

# 簡介
本專題是一套整合實體硬體感測與雲端通訊軟體的物聯網門禁保全系統。透過樹莓派核心進行邊緣運算，當實體感測器觸發時，系統會自動擷取影像並透過網路穿透技術將即時圖文警報推播至使用者的 LINE；使用者亦可透過 LINE 聊天室發送文字指令，遠端反向遙控實體門鎖致動器。

# 系統架構與功能
1. **主動防盜與即時影像推播**：
   - 部署於門口的紅外線人體感測器（PIR）偵測到異常移動。
   - 樹莓派接收硬體訊號，立刻呼叫相機模組進行現場拍攝，並動態生成帶有時間戳記的獨立照片檔案。
   - 透過 Flask 伺服器與 ngrok 反向代理，將本地影像映射至公網，並調用 LINE Messaging API 發送含有精確時間戳記的圖文警告訊息。
2. **遠端雙向控制門鎖**：
   - 使用者於 LINE 聊天室接收到照片後，可即時判斷安全性。
   - 聊天室輸入「是」或「對」，系統透過 Webhook 機制即時傳回樹莓派，以非同步執行緒驅動實體門鎖（LED 模擬）解鎖 3 秒鐘。
   - 聊天室輸入「否」或「不是」，門鎖維持關閉，確保場所安全。

# 硬體環境架構與腳位接線
- Raspberry Pi 5
- IMX219 相機模組
- PIR 紅外線人體感測器 (GPIO 17)
- LED 燈與適當電阻 (模擬門鎖，GPIO 27)

# 各程式功用說明
- **`app.py`**：系統的主程式。負責控制硬體（紅外線感測、相機拍照、LED 開關），以及處理 LINE 訊息的發送與接收。
- **`.env.example`**：環境變數範本。提供 LINE API 金鑰和 ngrok 網址的填寫格式，供使用者參考設定。
- **`requirements.txt`**：套件依賴清單。記錄系統執行所需的 Python 函式庫，方便使用者一鍵安裝所有必備環境。

# 軟體安裝與部署步驟

## 1. 環境初始化
將專案下載至樹莓派，並建立獨立的虛擬環境以安裝套件：
```bash
git clone <你的 GitHub 倉庫網址>
cd <專案資料夾名稱>

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. LINE 官方金鑰取得步驟
1. 瀏覽並登入 LINE Developers Console
2. 建立一個 Provider，並在建立一個 **Messaging API** 類型的新 Channel
3. 取得 Channel Secret 與 User ID
4. 取得 Channel Access Token

## 3. ngrok 固定網址申請步驟
1. 瀏覽並登入 ngrok Dashboard。
2. 在左側選單中點擊 **Cloud Edge** -> **Domains**。
3. 點擊 **Create Domain** 或 **New Domain** 建立一組免費的固定靜態網域（例如：`tattoo-bagpipe-mug.ngrok-free.dev`）。
4. 記下這組專屬的網址名稱。

## 4. 環境變數與金鑰配置
1. 使用文字編輯器創建 `.env`，按照.env.example的格式將上述步驟取得的資料準確填入：
   ```text
   LINE_CHANNEL_ACCESS_TOKEN=貼上你的_Channel_Access_Token
   LINE_CHANNEL_SECRET=貼上你的_Channel_Secret
   LINE_USER_ID=貼上你的_Your_user_ID
   NGROK_BASE_URL=[https://貼上你的固定網址.ngrok-free.dev](https://貼上你的固定網址.ngrok-free.dev)
   ```

## 5. 啟動系統與 Webhook 綁定
1. **啟動網路穿透**：在樹莓派終端機執行以下指令並替換為你的固定網址，讓外部網路可以連入本地 5000 埠：
   ```bash
   sudo snap install ngrok
   ngrok config add-authtoken XXXXXX
   ngrok http 5000
   ```
2. **設定 LINE Webhook**：
   - 回到 LINE Developers Console 的 **Messaging API** 頁籤。
   - 找到 **Webhook URL** 欄位，點擊 Edit 輸入：`https://你的固定網址.ngrok-free.dev/callback`
   - 點擊 **Update** 儲存，接著點擊 **Verify** 進行連線測試，必須顯示 **Success**。
   - 務必將下方的 **Use webhook** 功能切換為開啟（ON）狀態。
3. **執行主程式**：保持 ngrok 視窗運行，開啟新終端機視窗並進入虛擬環境，執行以下指令啟動保全系統：
   ```bash
   python app.py
   ```

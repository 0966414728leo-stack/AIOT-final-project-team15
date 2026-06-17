import os
import sys
import threading
import time
import subprocess
from datetime import datetime
from flask import Flask, request, abort
from dotenv import load_dotenv

from gpiozero import MotionSensor, LED

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage

# --- 載入環境變數 ---
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
USER_ID = os.getenv("LINE_USER_ID")
NGROK_BASE_URL = os.getenv("NGROK_BASE_URL")

if not all([CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET, USER_ID, NGROK_BASE_URL]):
    print("請確認 .env 檔案中已設定所有變數，包含 NGROK_BASE_URL。")
    sys.exit(1)

app = Flask(__name__, static_folder='static', static_url_path='/static')
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- 硬體腳位設定 ---
pir = MotionSensor(17)
door_lock = LED(27)

# --- 硬體控制與處理邏輯 ---
def open_door():
    """控制 LED 模擬開門"""
    print("執行開門動作 (LED 亮起)")
    door_lock.on()
    time.sleep(3) # 門鎖開啟 3 秒
    door_lock.off()
    print("門已上鎖 (LED 熄滅)")

last_capture_time = 0

def capture_and_send():
    """PIR 觸發後的中斷處理邏輯：拍照並推播"""
    global last_capture_time
    current_time = time.time()
    
    # 冷卻時間維持 3 秒
    if current_time - last_capture_time < 3:
        return
    last_capture_time = current_time

    print("偵測到移動！準備拍照...")
    
    # 產生不重複的動態檔名 (格式: intruder_YYYYMMDD_HHMMSS.jpg)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"intruder_{timestamp_str}.jpg"
    image_path = f"static/{filename}"
    
    try:
        subprocess.run(["rpicam-still", "-o", image_path, "--nopreview", "-t", "1000"], check=True)
    except Exception as e:
        print(f"拍照失敗: {e}")
        return

    # 使用新的獨立檔名組合 URL
    image_url = f"{NGROK_BASE_URL.rstrip('/')}/static/{filename}"
    print(f"拍照完成，發送圖片至 LINE: {image_url}")

    try:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        image_message = ImageSendMessage(
            original_content_url=image_url,
            preview_image_url=image_url
        )
        
        text_message = TextSendMessage(text=f"[{current_datetime}] 有人在門前，是否要開鎖")
        
        line_bot_api.push_message(USER_ID, [image_message, text_message])
    except Exception as e:
        print(f"LINE 發送失敗: {e}")

pir.when_motion = capture_and_send

# --- Webhook 路由 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    
    if msg in ["是", "對"]:
        threading.Thread(target=open_door).start()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="指令確認：門鎖已解開 3 秒鐘。")
        )
    elif msg in ["否", "不是"]:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="指令確認：門鎖維持關閉。")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"收到未知指令: {msg}。請輸入「是/對」或「否/不是」以控制門鎖。")
        )

if __name__ == "__main__":
    try:
        print("系統啟動中... 等待 LINE 訊息或 PIR 觸發。")
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n系統手動關閉")
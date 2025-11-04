# 涼メ〜ル - LINE Messaging API サーバー
# Python + Flask

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from datetime import datetime

app = Flask(__name__)

# LINE設定（環境変数から取得）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ユーザーデータベース（簡易版）
# 本番では PostgreSQL や MySQL を使用
users = {}

@app.route("/")
def home():
    return "涼メ〜ル - 熱中症見守りシステム稼働中"

@app.route("/webhook", methods=['POST'])
def webhook():
    """LINE Webhook エンドポイント"""
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """メッセージ受信時の処理"""
    user_id = event.source.user_id
    text = event.message.text
    
    # ユーザー登録
    if text == "登録":
        users[user_id] = {
            'name': None,
            'location': None,
            'registered_at': datetime.now().isoformat()
        }
        reply_text = "登録を開始します。\nお名前を教えてください。"
        
    # 名前の入力待ち
    elif user_id in users and users[user_id]['name'] is None:
        users[user_id]['name'] = text
        reply_text = f"{text}さん、ありがとうございます。\n次に作業場所を教えてください。"
        
    # 場所の入力待ち
    elif user_id in users and users[user_id]['location'] is None:
        users[user_id]['location'] = text
        reply_text = f"登録完了しました！\n\n名前: {users[user_id]['name']}\n場所: {text}\n\n監視を開始します。"
        
    # ステータス確認
    elif text == "状態":
        if user_id in users:
            user = users[user_id]
            reply_text = f"【現在の状態】\n名前: {user['name']}\n場所: {user['location']}\n\n監視中です。"
        else:
            reply_text = "まだ登録されていません。\n「登録」と送信して登録してください。"
            
    else:
        reply_text = "コマンド一覧:\n・登録: 新規登録\n・状態: 現在の状態確認"
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@app.route("/alert", methods=['POST'])
def alert():
    """ESP32からのアラート受信エンドポイント"""
    data = request.get_json()
    
    device_id = data.get('device_id')
    temperature = data.get('temperature')
    humidity = data.get('humidity')
    di = data.get('discomfort_index')
    risk_level = data.get('risk_level')
    duration = data.get('duration_minutes')
    
    # デバイスIDに対応するユーザーを探す
    # 簡易版ではdevice_idをuser_idとして使用
    user_id = device_id
    
    if user_id in users:
        user = users[user_id]
        
        # アラートメッセージ作成
        message = f"""🚨 熱中症警報 🚨

作業者: {user['name']}
場所: {user['location']}

━━━━━━━━━━━━━━━
📊 環境データ
━━━━━━━━━━━━━━━
気温: {temperature}℃
湿度: {humidity}%
不快指数: {di}

⚠️ リスクレベル: {risk_level}
⏱️ 継続時間: {duration}分

━━━━━━━━━━━━━━━
💡 推奨対応
━━━━━━━━━━━━━━━
• すぐに日陰で休憩
• 水分・塩分を補給
• 涼しい場所へ移動
• 体調確認

━━━━━━━━━━━━━━━
"""
        
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text=message)
            )
            return {'status': 'success'}, 200
        except Exception as e:
            print(f"Error sending message: {e}")
            return {'status': 'error', 'message': str(e)}, 500
    else:
        return {'status': 'error', 'message': 'User not registered'}, 404

@app.route("/status", methods=['POST'])
def status():
    """ESP32からの定期ステータス受信エンドポイント"""
    data = request.get_json()
    
    # ログに記録（本番ではデータベースに保存）
    print(f"Status update: {data}")
    
    return {'status': 'received'}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

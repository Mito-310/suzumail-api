# 涼メ〜ル - LINE Messaging API サーバー
# Python + Flask (プリセット選択式)

from flask import Flask, request, abort, jsonify
import os
from datetime import datetime
import json

app = Flask(__name__)

# LINE設定（環境変数から取得）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# 環境変数チェック
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    print("WARNING: LINE環境変数が設定されていません")
    print(f"LINE_CHANNEL_ACCESS_TOKEN: {'設定済み' if LINE_CHANNEL_ACCESS_TOKEN else '未設定'}")
    print(f"LINE_CHANNEL_SECRET: {'設定済み' if LINE_CHANNEL_SECRET else '未設定'}")

# LINE Bot APIの初期化（環境変数がある場合のみ）
line_bot_api = None
handler = None

if LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET:
    try:
        from linebot import LineBotApi, WebhookHandler
        from linebot.exceptions import InvalidSignatureError
        from linebot.models import MessageEvent, TextMessage, TextSendMessage
        
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        handler = WebhookHandler(LINE_CHANNEL_SECRET)
        print("LINE Bot API初期化成功")
    except Exception as e:
        print(f"LINE Bot API初期化エラー: {e}")

# ユーザーデータベース（簡易版）
users = {}

# ユーザー設定データベース
user_settings = {}

# プリセット設定
PRESETS = {
    '室内モード': {
        'caution_threshold': 45.0,
        'warning_threshold': 50.0,
        'severe_threshold': 55.0,
        'danger_threshold': 60.0,
        'alert_interval_minutes': 2,
        'description': '室内でのテスト用設定'
    },
    '軽作業モード': {
        'caution_threshold': 70.0,
        'warning_threshold': 75.0,
        'severe_threshold': 80.0,
        'danger_threshold': 85.0,
        'alert_interval_minutes': 15,
        'description': '軽い作業向けの設定'
    },
    '屋外作業モード': {
        'caution_threshold': 75.0,
        'warning_threshold': 80.0,
        'severe_threshold': 85.0,
        'danger_threshold': 90.0,
        'alert_interval_minutes': 30,
        'description': '屋外での通常作業向け'
    },
    '高温注意モード': {
        'caution_threshold': 70.0,
        'warning_threshold': 75.0,
        'severe_threshold': 80.0,
        'danger_threshold': 85.0,
        'alert_interval_minutes': 10,
        'description': '高温環境での作業向け'
    },
    '高齢者モード': {
        'caution_threshold': 65.0,
        'warning_threshold': 70.0,
        'severe_threshold': 75.0,
        'danger_threshold': 80.0,
        'alert_interval_minutes': 20,
        'description': '高齢者や体調不安がある方向け'
    }
}

# デフォルト設定
DEFAULT_SETTINGS = PRESETS['室内モード'].copy()

@app.route("/")
def home():
    return "涼メ〜ル - 熱中症見守りシステム稼働中"

@app.route("/health")
def health():
    """ヘルスチェックエンドポイント"""
    status = {
        "status": "ok",
        "line_api": "設定済み" if line_bot_api else "未設定",
        "users": len(users),
        "configured_users": len(user_settings)
    }
    return jsonify(status)

# 設定取得エンドポイント
@app.route("/settings/<user_id>", methods=['GET'])
def get_settings(user_id):
    """ユーザー設定を取得"""
    if user_id in user_settings:
        return jsonify(user_settings[user_id])
    else:
        # デフォルト設定を返す
        return jsonify(DEFAULT_SETTINGS)

# 設定更新エンドポイント
@app.route("/settings/<user_id>", methods=['POST', 'PUT'])
def update_settings(user_id):
    """ユーザー設定を更新"""
    try:
        data = request.get_json()
        
        # 設定を保存
        if user_id not in user_settings:
            user_settings[user_id] = DEFAULT_SETTINGS.copy()
        
        # 更新
        user_settings[user_id].update(data)
        
        print(f"Settings updated for {user_id}: {user_settings[user_id]}")
        
        return jsonify({
            'status': 'success',
            'settings': user_settings[user_id]
        })
    except Exception as e:
        print(f"Settings update error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/webhook", methods=['POST'])
def webhook():
    """LINE Webhook エンドポイント"""
    if not handler:
        return 'LINE API not configured', 500
    
    signature = request.headers.get('X-Line-Signature')
    if not signature:
        abort(400)
    
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        print(f"Webhook error: {e}")
        abort(500)
    
    return 'OK'

# コマンド処理関数
def process_command(user_id, text):
    """LINEコマンドを処理"""
    
    # ユーザー設定の初期化
    if user_id not in user_settings:
        user_settings[user_id] = DEFAULT_SETTINGS.copy()
    
    settings = user_settings[user_id]
    
    # コマンド解析
    text = text.strip()
    
    # 設定メニュー表示
    if text == "設定" or text == "設定変更" or text == "モード選択":
        return """どの設定を使いますか？

1. 室内モード
   注意45 / 警戒50 / 通知2分
   （室内でのテスト用）

2. 軽作業モード
   注意70 / 警戒75 / 通知15分
   （軽い作業向け）

3. 屋外作業モード
   注意75 / 警戒80 / 通知30分
   （屋外での通常作業向け）

4. 高温注意モード
   注意70 / 警戒75 / 通知10分
   （高温環境での作業向け）

5. 高齢者モード
   注意65 / 警戒70 / 通知20分
   （高齢者や体調不安がある方向け）

番号またはモード名を送信してください
例: 1 または 室内モード"""
    
    # プリセット選択（番号）
    preset_map = {
        '1': '室内モード',
        '2': '軽作業モード',
        '3': '屋外作業モード',
        '4': '高温注意モード',
        '5': '高齢者モード'
    }
    
    if text in preset_map:
        preset_name = preset_map[text]
        preset = PRESETS[preset_name]
        
        # 設定を更新
        user_settings[user_id] = preset.copy()
        
        return f"""設定を変更しました

【{preset_name}】
{preset['description']}

注意レベル: {preset['caution_threshold']}
警戒レベル: {preset['warning_threshold']}
厳重警戒レベル: {preset['severe_threshold']}
危険レベル: {preset['danger_threshold']}
通知間隔: {preset['alert_interval_minutes']}分

ESP32が1分以内に新しい設定を読み込みます"""
    
    # プリセット選択（モード名）
    if text in PRESETS:
        preset = PRESETS[text]
        
        # 設定を更新
        user_settings[user_id] = preset.copy()
        
        return f"""設定を変更しました

【{text}】
{preset['description']}

注意レベル: {preset['caution_threshold']}
警戒レベル: {preset['warning_threshold']}
厳重警戒レベル: {preset['severe_threshold']}
危険レベル: {preset['danger_threshold']}
通知間隔: {preset['alert_interval_minutes']}分

ESP32が1分以内に新しい設定を読み込みます"""
    
    # 設定確認
    if text == "設定確認" or text == "現在の設定":
        return f"""現在の設定

注意レベル: {settings['caution_threshold']}
警戒レベル: {settings['warning_threshold']}
厳重警戒レベル: {settings['severe_threshold']}
危険レベル: {settings['danger_threshold']}
通知間隔: {settings['alert_interval_minutes']}分

設定を変更するには「設定」と送信してください"""
    
    # 個別設定変更（上級者向け）
    if text.startswith("注意 "):
        try:
            value = float(text.split()[-1])
            if 0 <= value <= 100:
                settings['caution_threshold'] = value
                return f"注意レベルを {value} に設定しました"
            else:
                return "値は0〜100の範囲で指定してください"
        except:
            return "数値を正しく入力してください\n例: 注意 75"
    
    if text.startswith("警戒 "):
        try:
            value = float(text.split()[-1])
            if 0 <= value <= 100:
                settings['warning_threshold'] = value
                return f"警戒レベルを {value} に設定しました"
            else:
                return "値は0〜100の範囲で指定してください"
        except:
            return "数値を正しく入力してください\n例: 警戒 80"
    
    if text.startswith("厳重警戒 "):
        try:
            value = float(text.split()[-1])
            if 0 <= value <= 100:
                settings['severe_threshold'] = value
                return f"厳重警戒レベルを {value} に設定しました"
            else:
                return "値は0〜100の範囲で指定してください"
        except:
            return "数値を正しく入力してください\n例: 厳重警戒 85"
    
    if text.startswith("危険 "):
        try:
            value = float(text.split()[-1])
            if 0 <= value <= 100:
                settings['danger_threshold'] = value
                return f"危険レベルを {value} に設定しました"
            else:
                return "値は0〜100の範囲で指定してください"
        except:
            return "数値を正しく入力してください\n例: 危険 90"
    
    if text.startswith("通知間隔 ") or text.startswith("間隔 "):
        try:
            value = int(text.split()[-1])
            if 1 <= value <= 180:
                settings['alert_interval_minutes'] = value
                return f"通知間隔を {value}分 に設定しました"
            else:
                return "値は1〜180分の範囲で指定してください"
        except:
            return "数値を正しく入力してください\n例: 通知間隔 30"
    
    # ヘルプ
    if text == "ヘルプ" or text == "help" or text == "使い方":
        return """使い方ガイド

【基本操作】
「設定」→ モード選択画面を表示
「設定確認」→ 現在の設定を表示

【モード選択】
設定メニューから番号を選択
1: 室内モード（テスト用）
2: 軽作業モード
3: 屋外作業モード
4: 高温注意モード
5: 高齢者モード

【その他】
「登録」→ 新規登録
「状態」→ 現在の状態確認
「ID確認」→ デバイスIDを表示"""
    
    # デフォルト応答なし（他のコマンド処理に任せる）
    return None

# メッセージハンドラー（LINE APIが有効な場合のみ）
if handler:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        """メッセージ受信時の処理"""
        user_id = event.source.user_id
        text = event.message.text
        
        # コマンド処理を試行
        command_response = process_command(user_id, text)
        
        if command_response:
            # コマンドが処理された
            reply_text = command_response
            
        # 以下、既存のコマンド処理
        elif text == "登録":
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
            reply_text = f"登録完了しました！\n\n名前: {users[user_id]['name']}\n場所: {text}\n\n監視を開始します。\n\n設定を変更するには「設定」と送信してください。"
            
        # ステータス確認
        elif text == "状態":
            if user_id in users:
                user = users[user_id]
                reply_text = f"【現在の状態】\n名前: {user['name']}\n場所: {user['location']}\n\n監視中です。"
            else:
                reply_text = "まだ登録されていません。\n「登録」と送信して登録してください。"
                
        # User ID確認
        elif text == "ID確認" or text == "id確認":
            reply_text = f"あなたのUser ID:\n{user_id}\n\nこのIDをESP32に設定してください。"
            
        else:
            reply_text = """コマンド一覧:
・設定: モード選択
・設定確認: 現在の設定
・ヘルプ: 使い方ガイド
・登録: 新規登録
・状態: 現在の状態確認
・ID確認: User IDを表示"""
        
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        except Exception as e:
            print(f"Reply error: {e}")

@app.route("/alert", methods=['POST'])
def alert():
    """ESP32からのアラート受信エンドポイント"""
    if not line_bot_api:
        return {'status': 'error', 'message': 'LINE API not configured'}, 500
    
    try:
        data = request.get_json()
        
        device_id = data.get('device_id')
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        di = data.get('discomfort_index')
        risk_level = data.get('risk_level')
        duration = data.get('duration_minutes')
        
        # デバイスIDに対応するユーザーを探す
        user_id = device_id
        
        # ユーザー情報の取得
        user_name = "作業者"
        user_location = "現場"
        if user_id in users:
            user = users[user_id]
            user_name = user.get('name', user_name)
            user_location = user.get('location', user_location)
        
        # アラートメッセージ作成
        message = f"""熱中症警報

作業者: {user_name}
場所: {user_location}

━━━━━━━━━━━━━━━
環境データ
━━━━━━━━━━━━━━━
気温: {temperature}℃
湿度: {humidity}%
不快指数: {di}

リスクレベル: {risk_level}
継続時間: {duration}分

━━━━━━━━━━━━━━━
推奨対応
━━━━━━━━━━━━━━━
・すぐに日陰で休憩
・水分と塩分を補給
・涼しい場所へ移動
・体調を確認

━━━━━━━━━━━━━━━
設定変更は「設定」と送信
"""
        
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=message)
        )
        return {'status': 'success'}, 200
        
    except Exception as e:
        print(f"Alert error: {e}")
        return {'status': 'error', 'message': str(e)}, 500

@app.route("/status", methods=['POST'])
def status():
    """ESP32からの定期ステータス受信エンドポイント"""
    try:
        data = request.get_json()
        print(f"Status update: {data}")
        return {'status': 'received'}, 200
    except Exception as e:
        print(f"Status error: {e}")
        return {'status': 'error', 'message': str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)

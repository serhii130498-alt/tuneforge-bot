import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SPACE_URL = "https://facebook-musicgen.hf.space/api/predict"

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        
        if text == "/start":
            send_message(chat_id, "Привет! 🎧 Я **TuneForge** — твой генератор музыки.\n\nОтправь мне текстовое описание трека на английском (например: *'ambient drone'*), и я создам трек!")
            return "OK", 200
        
        send_message(chat_id, "🎵 Запрос принят! Ставлю трек в очередь на сервере...")
        
        try:
            payload = {
                "data": [text, "melody"],
                "fn_index": 0
            }
            headers = {
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # Запрос к Hugging Face без ограничения в 30 секунд
            response = requests.post(SPACE_URL, json=payload, headers=headers, timeout=120)
            
            if response.status_code == 200:
                json_result = response.json()
                if json_result and "data" in json_result and json_result["data"]:
                    audio_url = json_result["data"][0].get("url") or json_result["data"][0]
                    audio_resp = requests.get(audio_url)
                    if audio_resp.status_code == 200:
                        send_audio(chat_id, audio_resp.content, f"✨ Твой трек от TuneForge готов!\nПромпт: {text}")
                    else:
                        send_message(chat_id, "❌ Не удалось скачать аудиофайл.")
                else:
                    send_message(chat_id, "❌ Не удалось получить аудиофайл от сервера.")
            else:
                send_message(chat_id, "⚠️ Сервер перегружен или разогревается. Попробуй еще раз.")
                
        except Exception as e:
            send_message(chat_id, f"❌ Ошибка: {str(e)}")
            
    return "OK", 200

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })

def send_audio(chat_id, audio_bytes, caption):
    files = {"audio": ("TuneForge_track.mp3", audio_bytes, "audio/mpeg")}
    data = {"chat_id": chat_id, "caption": caption}
    requests.post(f"{TELEGRAM_API}/sendAudio", data=data, files=files)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

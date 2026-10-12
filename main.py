import os
import time
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_URL = "https://tuneforge-bot.onrender.com"

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Автоустановка вебхука при старте сервера
if TELEGRAM_TOKEN:
  try:
    requests.get(f"{TELEGRAM_API}/setWebhook?url={RENDER_URL}/")
  except Exception as e:
    print(f"Webhook set error: {e}")


def query_huggingface(payload):
  api_url = "https://api-inference.huggingface.co/models/facebook/musicgen-small"
  headers = {"Authorization": f"Bearer {HF_TOKEN}"}

  # Ждем до 6 попыток (если модель разогревается)
  for attempt in range(6):
    response = requests.post(api_url, headers=headers, json=payload)
    try:
      data = response.json()
    except Exception:
      data = {}

    if "error" in data and (
        "is loading" in str(data["error"]).lower() or response.status_code == 503
    ):
      time.sleep(10)  # ждем 10 секунд пока модель проснется
      continue
    return response
  return response


def send_telegram_message(chat_id, text):
  url = f"{TELEGRAM_API}/sendMessage"
  requests.post(url, json={"chat_id": chat_id, "text": text})


@app.route("/", methods=["POST"])
def webhook():
  update = request.get_json()
  if not update:
    return "ok", 200

  if "message" in update:
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text == "/start":
      send_telegram_message(
          chat_id,
          "Привет! 🎧 Я TuneForge — твой генератор музыки.\n\nОтправь мне"
          " текстовое описание трека на английском (например: 'ambient"
          " drone'), и я создам трек!",
      )
    else:
      send_telegram_message(
          chat_id,
          "🎵 Запрос принят! Ставлю трек в очередь, модель разогревается...",
      )

      hf_payload = {"inputs": text}
      hf_response = query_huggingface(hf_payload)

      if hf_response.status_code == 200:
        send_telegram_message(chat_id, "✅ Трек успешно сгенерирован!")
      else:
        send_telegram_message(
            chat_id,
            "⚠️ Модель всё еще запускается. Пожалуйста, отправьте запрос еще"
            " раз через минуту.",
        )

  return "ok", 200


@app.route("/", methods=["GET"])
def index():
  return "TuneForge Bot is running!", 200


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

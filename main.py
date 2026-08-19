import os
import time
import requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
URL = f"https://api.telegram.org/bot{TOKEN}"

offset = 0

print("Telegram bot started")

while True:
    try:
        response = requests.get(
            f"{URL}/getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35,
        )

        data = response.json()

        if data.get("ok"):
            for update in data["result"]:
                offset = update["update_id"] + 1

                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "")

                if text == "/start":
                    requests.post(
                        f"{URL}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "✅ Бот работает! Railway и Telegram подключены."
                        },
                        timeout=10,
                    )

    except Exception as e:
        print("Error:", e)
        time.sleep(5)

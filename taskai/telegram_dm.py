# pip install python-telegram-bot==20.0b0 requests
import requests, subprocess, os
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
USER_CHAT_IDS = {
    "maddie": 8445736211,
    "alex":8297692221
}


def send_dm(message, person):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": USER_CHAT_IDS[person.lower()],
            "text": message
        }
        response = requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")
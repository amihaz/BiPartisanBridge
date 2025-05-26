import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_ID

def send_bot_message(text: str):
    """
    Sends a message to the Telegram group/channel using the bot.
    
    Args:
        text (str): The message text to send.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.get(url, params={
        "chat_id": TELEGRAM_BOT_ID,
        "text": text
    })

    # Optional: raise an error if it fails
    if not response.ok:
        raise Exception(f"Failed to send message: {response.status_code} - {response.text}")

if __name__ == "__main__":
    send_bot_message("Hello from my bot!")

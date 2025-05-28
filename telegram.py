import requests
from telethon import TelegramClient
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_ID, LEFT_CHANNELS, RIGHT_CHANNELS

# Initialize global variables
left_channel_ids = set()
right_channel_ids = set()


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


async def init_channel_ids(client: TelegramClient) -> None:
    """
    Populate the global `left_channel_ids` and `right_channel_ids` sets.
    Call this once, after `await client.start()`, before entering your main loop.

    Args:
        client (TelegramClient): An initialized and started Telethon client.
    """
    global left_channel_ids, right_channel_ids
    
    # Resolve LEFT_CHANNELS usernames to IDs
    left_channel_ids = set()
    for username in LEFT_CHANNELS:
        try:
            entity = await client.get_entity(username)
            left_channel_ids.add(str(entity.id))
        except Exception as e:
            print(f"[ERROR] Failed to resolve left channel '{username}': {e}")

    # Resolve RIGHT_CHANNELS usernames to IDs
    right_channel_ids = set()
    for username in RIGHT_CHANNELS:
        try:
            entity = await client.get_entity(username)
            right_channel_ids.add(str(entity.id))
        except Exception as e:
            print(f"[ERROR] Failed to resolve right channel '{username}': {e}")

    # Log the resolved IDs
    print(f"[INIT] Left channel IDs: {left_channel_ids}")
    print(f"[INIT] Right channel IDs: {right_channel_ids}")


def get_channel_ids():
    """
    Returns the current channel ID sets.
    Useful for accessing the IDs from other modules.
    
    Returns:
        tuple: (left_channel_ids, right_channel_ids)
    """
    return left_channel_ids, right_channel_ids


def is_left_channel(channel_id: str) -> bool:
    """
    Check if a channel ID belongs to the left channels.
    
    Args:
        channel_id (str): The channel ID to check.
        
    Returns:
        bool: True if the channel is a left channel.
    """
    return channel_id in left_channel_ids


def is_right_channel(channel_id: str) -> bool:
    """
    Check if a channel ID belongs to the right channels.
    
    Args:
        channel_id (str): The channel ID to check.
        
    Returns:
        bool: True if the channel is a right channel.
    """
    return channel_id in right_channel_ids
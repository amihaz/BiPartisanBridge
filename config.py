import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Telegram Bot Config
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
LEFT_CHANNELS     = os.getenv("LEFT_CHANNELS", "").split(",")
RIGHT_CHANNELS    = os.getenv("RIGHT_CHANNELS", "").split(",")
CHANNELS          = LEFT_CHANNELS + RIGHT_CHANNELS
TELEGRAM_API_ID    = os.getenv("TELEGRAM_APP_ID")
TELEGRAM_API_HASH  = os.getenv("TELEGRAM_APP_HASH")

# Topic processing
TOPIC_THRESHOLD   = int(os.getenv("TOPIC_THRESHOLD", "1"))
MESSAGE_TTL_MINUTES = int(os.getenv("MESSAGE_TTL_MINUTES", "1"))
PROCESS_INTERVAL_SECONDS = int(os.getenv("PROCESS_INTERVAL_SECONDS", "30"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_ID    = os.getenv("TELEGRAM_BOT_ID")

# OpenRouter (LLM) Config
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_BASE = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/v1")

TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))

# CLI Constants
def validate_config():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN must be set")
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY must be set")

# Automatically validate on import
# validate_config()

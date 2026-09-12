import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_CHANNEL_ID = int(os.environ["PUBLIC_CHANNEL_ID"])
LOG_CHANNEL_ID = int(os.environ["LOG_CHANNEL_ID"])
ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split(",") if x.strip()]
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "")
REQUIRED_CHANNEL_URL = os.environ.get("REQUIRED_CHANNEL_URL", "")
PROXY = os.environ.get("PROXY") or None
SUPPORT_CHANNEL_ID = int(os.environ["SUPPORT_CHANNEL_ID"])

COOLDOWN = 2 * 60
DB_PATH = "data.db"
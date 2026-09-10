import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
ADMIN_PASSWORD = "admin123"
ADMIN_ID = [832127865]

ZOOM_LINK = os.getenv("ZOOM_LINK", "https://zoom.us/j/1234567890")

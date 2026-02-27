# config.py
import os
from datetime import datetime

# Bot configuration
BOT_TOKEN = "8338583447:AAEbRQZQM6ILrD_tYdFtCtbr1yGRpyl-N_s"
ADMIN_ID = 6689435577
MOVIES_CHANNEL = "-1003886823374"
SERIES_CHANNEL = "-1003601037185"
BACKUP_CHANNEL = "-1003844037351"
SUPPORT_CHANNEL = "https://t.me/iIl337"

# States
CHECK_SUB, SEARCH_NAME, REQUEST_MOVIE, ADD_MOVIE_NAME, ADD_EPISODE, ADMIN_ADDING = range(6)

# Database file
DB_FILE = "bot_data.db"

# Channel usernames for links
CHANNELS = {
    "movies": MOVIES_CHANNEL,
    "series": SERIES_CHANNEL,
    "backup": BACKUP_CHANNEL
}

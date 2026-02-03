import os


class Config:
    """Configuration settings for the bot"""

    # Check interval in seconds (default: 5 minutes)
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))

    # Discord bot token
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

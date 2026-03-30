import os
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()


class Config:
    """
    Simple configuration holder.

    BOT_TOKEN is read from environment variable BOT_TOKEN.
    You can create a .env file in the project root with:

        BOT_TOKEN=123456:ABC-DEF...
    """

    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()


config = Config()


def validate_config() -> None:
    """
    Validate that required configuration values are present.
    Raises ValueError if something important is missing.
    """
    if not config.BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN is not set. Please set BOT_TOKEN environment variable "
            "or create a .env file with BOT_TOKEN=..."
        )


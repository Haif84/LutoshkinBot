import logging

from telegram.ext import ApplicationBuilder, CommandHandler

from config import config, validate_config
from db import create_tables
from handlers import add_admin_command, build_conversation_handler


def main() -> None:
    """Main entry point: init DB, build application and start polling."""
    # Basic logging configuration
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    # Validate configuration and initialize database
    try:
        validate_config()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        raise

    try:
        create_tables()
    except Exception:
        logger.exception("Failed to initialize database.")
        raise

    # Build Telegram application
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # Register global command handlers
    application.add_handler(CommandHandler("addadmin", add_admin_command))

    # Register conversation and other handlers
    build_conversation_handler(application)

    logger.info("Bot is starting polling...")
    # Start bot (blocking call, manages its own event loop)
    application.run_polling()


if __name__ == "__main__":
    main()


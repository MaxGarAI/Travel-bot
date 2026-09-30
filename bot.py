import asyncio
import logging
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from database import init_db, close_db
from api_clients import openrouter_client, travel_api_client

from handlers.basic import (
    start, help_command, menu_command,
    handle_main_menu, process_natural_language, cancel, error_handler,
    MAIN_MENU,
)
from handlers.flights import (
    flight_search_start, flight_origin, flight_destination,
    flight_date_callback, flight_return_date, search_flights,
    FLIGHT_ORIGIN, FLIGHT_DESTINATION, FLIGHT_DATE, FLIGHT_RETURN_DATE,
)
from handlers.hotels import (
    hotel_search_start, hotel_city, hotel_checkin_callback,
    hotel_checkout, hotel_guests, search_hotels,
    HOTEL_CITY, HOTEL_CHECKIN, HOTEL_CHECKOUT, HOTEL_GUESTS,
)
from handlers.trains import (
    train_search_start, train_origin, train_destination,
    train_date_callback, search_trains,
    TRAIN_ORIGIN, TRAIN_DESTINATION, TRAIN_DATE,
)
from handlers.itineraries import (
    create_itinerary_start, itinerary_destination, itinerary_dates,
    itinerary_preferences, generate_itinerary,
    ITINERARY_DESTINATION, ITINERARY_DATES, ITINERARY_PREFERENCES,
)
from handlers.callbacks import handle_callback, handle_date_callback

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)

# Reduce noise from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database on startup."""
    await init_db()
    logger.info("Bot started successfully")


async def post_shutdown(application: Application) -> None:
    """Cleanup on shutdown."""
    await openrouter_client.close()
    await travel_api_client.close()
    await close_db()
    logger.info("Bot stopped")


def main() -> None:
    """Run the bot."""
    # Create application
    application = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Flight search conversation
    flight_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(flight_search_start, pattern="^search_flights"),
            CallbackQueryHandler(flight_search_start, pattern="^search_flights_round"),
        ],
        states={
            FLIGHT_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, flight_origin)],
            FLIGHT_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, flight_destination)],
            FLIGHT_DATE: [
                CallbackQueryHandler(flight_date_callback, pattern="^flight_depart_"),
            ],
            FLIGHT_RETURN_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, flight_return_date),
                CallbackQueryHandler(flight_date_callback, pattern="^flight_return_"),
                CallbackQueryHandler(flight_return_date, pattern="^flight_oneway$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel_flight$"),
        ],
        name="flight_search",
        persistent=False,
    )
    
    # Hotel search conversation
    hotel_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(hotel_search_start, pattern="^search_hotels$"),
        ],
        states={
            HOTEL_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, hotel_city)],
            HOTEL_CHECKIN: [
                CallbackQueryHandler(hotel_checkin_callback, pattern="^hotel_checkin_"),
            ],
            HOTEL_CHECKOUT: [
                CallbackQueryHandler(hotel_checkout, pattern="^hotel_checkout_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, hotel_checkout),
            ],
            HOTEL_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, hotel_guests)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel_hotel$"),
        ],
        name="hotel_search",
        persistent=False,
    )
    
    # Train search conversation
    train_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(train_search_start, pattern="^search_trains$"),
            CallbackQueryHandler(train_search_start, pattern="^search_trains_fast$"),
            CallbackQueryHandler(train_search_start, pattern="^search_trains_night$"),
        ],
        states={
            TRAIN_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, train_origin)],
            TRAIN_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, train_destination)],
            TRAIN_DATE: [
                CallbackQueryHandler(train_date_callback, pattern="^train_depart_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel_train$"),
        ],
        name="train_search",
        persistent=False,
    )
    
    # Itinerary creation conversation
    itinerary_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_itinerary_start, pattern="^create_itinerary$"),
        ],
        states={
            ITINERARY_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, itinerary_destination)],
            ITINERARY_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, itinerary_dates)],
            ITINERARY_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, itinerary_preferences)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel_itinerary$"),
        ],
        name="itinerary_creation",
        persistent=False,
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    
    # Conversation handlers
    application.add_handler(flight_conv)
    application.add_handler(hotel_conv)
    application.add_handler(train_conv)
    application.add_handler(itinerary_conv)
    
    # Main menu text handler
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r"^(🔍 Найти билеты|🏨 Отели|🚂 Поезда|🗺️ Маршруты|⭐ Избранное|👤 Профиль|❓ Помощь|❌ Отмена)$"),
            handle_main_menu,
        )
    )
    
    # Natural language processing for AI itinerary
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^(🔍 Найти билеты|🏨 Отели|🚂 Поезда|🗺️ Маршруты|⭐ Избранное|👤 Профиль|❓ Помощь|❌ Отмена)$"),
            process_natural_language,
        )
    )
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(CallbackQueryHandler(handle_date_callback, pattern=r".*_month_.*"))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Run
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
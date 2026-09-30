from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from sqlalchemy import select
import logging

from database import get_session
from models import User, Trip, Bookmark, ConversationContext
from keyboards import (
    get_main_keyboard, get_profile_keyboard,
    get_itinerary_keyboard, get_trip_actions_keyboard,
)
from handlers.flights import flight_search_start, flight_detail, flight_pagination, bookmark_flight, cancel_flight
from handlers.hotels import hotel_search_start, hotel_detail, hotel_pagination, bookmark_hotel, cancel_hotel
from handlers.trains import train_search_start, train_detail, bookmark_train, cancel_train
from handlers.itineraries import (
    create_itinerary_start, ai_itinerary, my_itineraries,
    view_trip, popular_destinations, quick_itinerary, cancel_itinerary,
)
from handlers.basic import show_profile

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main callback query handler - routes to appropriate handlers."""
    query = update.callback_query
    data = query.data
    
    try:
        # Main menu navigation
        if data == "main_menu":
            await query.answer()
            await query.edit_message_text(
                "🏠 Главное меню:",
                reply_markup=get_main_keyboard()
            )
        
        # Flight callbacks
        elif data == "search_flights":
            await flight_search_start(update, context)
        elif data == "search_flights_round":
            context.user_data['flight_round'] = True
            await flight_search_start(update, context)
        elif data == "search_flights_multi":
            await query.answer("Многородковые рейсы в разработке", show_alert=True)
        elif data == "search_flights_flexible":
            await query.answer("Гибкие даты в разработке", show_alert=True)
        elif data.startswith("flight_detail_"):
            await flight_detail(update, context)
        elif data.startswith("flights_page_"):
            await flight_pagination(update, context)
        elif data.startswith("bookmark_flight_"):
            await bookmark_flight(update, context)
        elif data == "cancel_flight":
            await cancel_flight(update, context)
        
        # Hotel callbacks
        elif data == "search_hotels":
            await hotel_search_start(update, context)
        elif data == "search_apartments":
            await query.answer("Апартаменты в разработке", show_alert=True)
        elif data == "search_hotels_rating":
            await query.answer("Сортировка по рейтингу в разработке", show_alert=True)
        elif data == "search_hotels_price":
            await query.answer("Сортировка по цене в разработке", show_alert=True)
        elif data.startswith("hotel_detail_"):
            await hotel_detail(update, context)
        elif data.startswith("hotels_page_"):
            await hotel_pagination(update, context)
        elif data.startswith("bookmark_hotel_"):
            await bookmark_hotel(update, context)
        elif data == "cancel_hotel":
            await cancel_hotel(update, context)
        
        # Train callbacks
        elif data == "search_trains":
            await train_search_start(update, context)
        elif data == "search_trains_fast":
            context.user_data['train_fast'] = True
            await train_search_start(update, context)
        elif data == "search_trains_night":
            context.user_data['train_night'] = True
            await train_search_start(update, context)
        elif data.startswith("train_detail_"):
            await train_detail(update, context)
        elif data.startswith("bookmark_train_"):
            await bookmark_train(update, context)
        elif data == "cancel_train":
            await cancel_train(update, context)
        
        # Itinerary callbacks
        elif data == "create_itinerary":
            await create_itinerary_start(update, context)
        elif data == "ai_itinerary":
            await ai_itinerary(update, context)
        elif data == "my_itineraries":
            await my_itineraries(update, context)
        elif data == "popular_destinations":
            await popular_destinations(update, context)
        elif data.startswith("view_trip_"):
            await view_trip(update, context)
        elif data.startswith("quick_itinerary_"):
            await quick_itinerary(update, context)
        elif data == "cancel_itinerary":
            await cancel_itinerary(update, context)
        
        # Trip actions
        elif data.startswith("view_itinerary_"):
            trip_id = int(data.replace("view_itinerary_", ""))
            context.user_data['current_trip_id'] = trip_id
            await view_trip(update, context)
        elif data.startswith("edit_trip_"):
            await query.answer("Редактирование в разработке", show_alert=True)
        elif data.startswith("trip_bookings_"):
            await query.answer("Бронирования в разработке", show_alert=True)
        elif data.startswith("trip_budget_"):
            await query.answer("Бюджет в разработке", show_alert=True)
        elif data.startswith("delete_trip_"):
            await confirm_delete_trip(update, context)
        
        # Profile callbacks
        elif data == "edit_profile":
            await query.answer("Редактирование профиля в разработке", show_alert=True)
        elif data == "budget_settings":
            await query.answer("Настройки бюджета в разработке", show_alert=True)
        elif data == "home_city":
            await query.answer("Настройка домашнего города в разработке", show_alert=True)
        elif data == "travel_style":
            await query.answer("Настройка стиля путешествий в разработке", show_alert=True)
        elif data == "notifications":
            await query.answer("Настройка уведомлений в разработке", show_alert=True)
        
        # Profile menu
        elif data == "profile_menu":
            await show_profile(update, context)
        
        # Itinerary menu
        elif data == "itinerary_menu":
            await query.answer()
            await query.edit_message_text(
                "🗺️ <b>Планировщик маршрутов</b>\n\nВыбери действие:",
                parse_mode="HTML",
                reply_markup=get_itinerary_keyboard()
            )
        
        # Date picker callbacks (handled by respective handlers)
        elif data.startswith(("flight_depart_", "flight_return_", "hotel_checkin_", "hotel_checkout_", "train_depart_")):
            # These are handled by conversation handlers
            pass
        
        # Noop
        elif data == "noop":
            await query.answer()
        
        # Confirmation callbacks
        elif data.startswith("confirm_delete_trip_"):
            await delete_trip(update, context)
        elif data.startswith("cancel_delete_trip_"):
            await query.answer("Удаление отменено")
            trip_id = int(data.replace("cancel_delete_trip_", ""))
            await view_trip(update, context)
        
        else:
            logger.warning(f"Unknown callback: {data}")
            await query.answer("Неизвестная команда", show_alert=True)
    
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка", show_alert=True)


async def confirm_delete_trip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm trip deletion."""
    query = update.callback_query
    await query.answer()
    
    trip_id = int(query.data.replace("delete_trip_", ""))
    
    async with get_session() as session:
        trip = await session.get(Trip, trip_id)
        if not trip:
            await query.edit_message_text("Поездка не найдена")
            return
    
    text = (
        f"🗑️ <b>Удалить поездку?</b>\n\n"
        f"<b>{trip.title}</b>\n"
        f"📅 {trip.start_date.strftime('%d.%m.%Y')} — {trip.end_date.strftime('%d.%m.%Y')}\n\n"
        "Это действие нельзя отменить. Все данные маршрута будут удалены."
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_trip_{trip_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_delete_trip_{trip_id}"),
        ]
    ])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def delete_trip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete trip."""
    query = update.callback_query
    await query.answer()
    
    trip_id = int(query.data.replace("confirm_delete_trip_", ""))
    
    async with get_session() as session:
        trip = await session.get(Trip, trip_id)
        if trip:
            await session.delete(trip)
    
    await query.edit_message_text(
        "✅ Поездка удалена",
        reply_markup=get_main_keyboard()
    )


async def handle_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle date picker callbacks."""
    query = update.callback_query
    data = query.data
    
    # Month navigation
    if "_month_" in data and not data.startswith(("flight_", "hotel_", "train_")):
        await query.answer()
        # Generic month navigation
        parts = data.split("_")
        if len(parts) >= 4:
            prefix = parts[0]
            year = int(parts[2])
            month = int(parts[3])
            
            # This would need the specific keyboard function
            # For now, just acknowledge
            await query.answer(f"Месяц: {month}.{year}")
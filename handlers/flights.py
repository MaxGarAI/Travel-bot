from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from datetime import datetime, date
import logging

from database import get_session
from models import User, SearchHistory, Trip, ItineraryItem, Bookmark
from keyboards import (
    get_main_keyboard, get_cancel_keyboard,
    get_flight_results_keyboard, get_hotel_results_keyboard,
    get_date_keyboard, get_confirm_keyboard,
)
from api_clients import travel_api_client

logger = logging.getLogger(__name__)

# Flight conversation states
FLIGHT_ORIGIN, FLIGHT_DESTINATION, FLIGHT_DATE, FLIGHT_RETURN_DATE, FLIGHT_PASSENGERS = range(100, 105)


async def flight_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start flight search."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "✈️ <b>Поиск авиабилетов</b>\n\n"
            "Введи город вылета (на русском или английском):\n"
            "Например: Москва, Санкт-Петербург, Москва (SVO)",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    else:
        await update.message.reply_text(
            "✈️ <b>Поиск авиабилетов</b>\n\n"
            "Введи город вылета:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    return FLIGHT_ORIGIN


async def flight_origin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle flight origin input."""
    context.user_data['flight_origin'] = update.message.text.strip()
    
    await update.message.reply_text(
        f"✈️ Вылет: <b>{context.user_data['flight_origin']}</b>\n\n"
        "Теперь введи город прилёта:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    return FLIGHT_DESTINATION


async def flight_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle flight destination input."""
    context.user_data['flight_destination'] = update.message.text.strip()
    
    await update.message.reply_text(
        f"✈️ Маршрут: <b>{context.user_data['flight_origin']} → {context.user_data['flight_destination']}</b>\n\n"
        "Введи дату вылета (ДД.ММ.ГГГГ) или выбери из календаря:",
        parse_mode="HTML",
        reply_markup=get_date_keyboard(date.today().year, date.today().month, "flight_depart")
    )
    return FLIGHT_DATE


async def flight_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle flight date selection from calendar."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("flight_depart_day_"):
        _, _, _, year, month, day = data.split("_")
        selected_date = date(int(year), int(month), int(day))
        context.user_data['flight_date'] = selected_date.strftime("%d.%m.%Y")
        
        await query.edit_message_text(
            f"✈️ Дата вылета: <b>{context.user_data['flight_date']}</b>\n\n"
            "Введи дату возвращения (ДД.ММ.ГГГГ) или нажми 'Только туда':",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Только туда", callback_data="flight_oneway"),
                InlineKeyboardButton("📅 Выбрать дату возвращения", callback_data="flight_return_calendar")
            ], [
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_flight")
            ]])
        )
        return FLIGHT_RETURN_DATE
    
    elif data == "flight_oneway":
        context.user_data['flight_return_date'] = None
        return await search_flights(update, context)
    
    elif data == "flight_return_calendar":
        await query.edit_message_text(
            "Выбери дату возвращения:",
            reply_markup=get_date_keyboard(date.today().year, date.today().month, "flight_return")
        )
        return FLIGHT_RETURN_DATE
    
    return FLIGHT_RETURN_DATE


async def flight_return_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle flight return date input."""
    text = update.message.text.strip()
    
    if text.lower() in ['только туда', 'односторонний', 'one way']:
        context.user_data['flight_return_date'] = None
    else:
        try:
            datetime.strptime(text, "%d.%m.%Y")
            context.user_data['flight_return_date'] = text
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используй ДД.ММ.ГГГГ",
                reply_markup=get_cancel_keyboard()
            )
            return FLIGHT_RETURN_DATE
    
    return await search_flights(update, context)


async def search_flights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Search flights and show results."""
    origin = context.user_data.get('flight_origin')
    destination = context.user_data.get('flight_destination')
    depart_date = context.user_data.get('flight_date')
    return_date = context.user_data.get('flight_return_date')
    
    if not all([origin, destination, depart_date]):
        await update.message.reply_text("❌ Не все данные заполнены")
        return ConversationHandler.END
    
    # Show loading
    if update.callback_query:
        await update.callback_query.edit_message_text("🔍 Ищу билеты...")
    else:
        await update.message.reply_text("🔍 Ищу билеты...")
    
    try:
        flights = await travel_api_client.search_flights_skyscanner(
            origin=origin,
            destination=destination,
            departure_date=depart_date,
            return_date=return_date,
        )
        
        # Save search history
        user = update.effective_user
        async with get_session() as session:
            search = SearchHistory(
                user_id=user.id,
                search_type="flights",
                query_params={
                    "origin": origin,
                    "destination": destination,
                    "depart_date": depart_date,
                    "return_date": return_date,
                },
                results_count=len(flights),
            )
            session.add(search)
        
        if not flights:
            text = "😔 Билеты не найдены. Попробуй другие даты или направления."
            keyboard = get_main_keyboard()
        else:
            text = (
                f"✈️ <b>Найдено {len(flights)} рейсов</b>\n"
                f"{origin} → {destination} на {depart_date}"
                f"{' → ' + return_date if return_date else ''}\n\n"
                "Выбери рейс для подробностей:"
            )
            keyboard = get_flight_results_keyboard(flights)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Flight search error: {e}")
        await update.message.reply_text(
            "❌ Ошибка поиска. Попробуй позже.",
            reply_markup=get_main_keyboard()
        )
    
    return ConversationHandler.END


async def flight_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show flight details."""
    query = update.callback_query
    await query.answer()
    
    flight_id = query.data.replace("flight_detail_", "")
    # In real implementation, fetch from cache or search again
    # For now, show mock detail
    
    detail_text = (
        f"✈️ <b>Детали рейса</b>\n\n"
        f"Рейс: {flight_id}\n"
        f"Авиакомпания: Аэрофлот\n"
        f"Номер: SU 1234\n"
        f"Вылет: 10:00 → Прилёт: 14:30\n"
        f"Длительность: 4ч 30м\n"
        f"Пересадок: 0\n"
        f"Цена: 15 000 RUB\n\n"
        f"Багаж: 23 кг включен\n"
        f"Ручная кладь: 10 кг\n"
        f"Выбор места: Бесплатно\n\n"
        f"Для бронирования перейди на сайт партнёра."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Забронировать", url="https://example.com/book")],
        [InlineKeyboardButton("⭐ В избранное", callback_data=f"bookmark_flight_{flight_id}")],
        [InlineKeyboardButton("⬅️ К результатам", callback_data="flights_page_0")],
    ])
    
    await query.edit_message_text(detail_text, parse_mode="HTML", reply_markup=keyboard)
    return ConversationHandler.END


async def flight_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle flight results pagination."""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split("_")[-1])
    # Would need to store flights in context or re-search
    await query.edit_message_text("Пагинация будет работать после сохранения результатов в контексте")
    return ConversationHandler.END


async def bookmark_flight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save flight to bookmarks."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    flight_id = query.data.replace("bookmark_flight_", "")
    
    async with get_session() as session:
        bookmark = Bookmark(
            user_id=user.id,
            bookmark_type="flight",
            title=f"Рейс {flight_id}",
            external_id=flight_id,
            extra_data={"origin": context.user_data.get('flight_origin'), "destination": context.user_data.get('flight_destination')},
        )
        session.add(bookmark)
    
    await query.answer("✅ Добавлено в избранное!", show_alert=True)
    return ConversationHandler.END


async def cancel_flight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel flight search."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Поиск отменён", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("❌ Поиск отменён", reply_markup=get_main_keyboard())
    return ConversationHandler.END
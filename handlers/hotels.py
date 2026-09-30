from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from datetime import datetime, date
import logging

from database import get_session
from models import User, SearchHistory, Bookmark
from keyboards import (
    get_main_keyboard, get_cancel_keyboard,
    get_hotel_results_keyboard, get_date_keyboard,
)
from api_clients import travel_api_client

logger = logging.getLogger(__name__)

# Hotel conversation states
HOTEL_CITY, HOTEL_CHECKIN, HOTEL_CHECKOUT, HOTEL_GUESTS = range(200, 204)


async def hotel_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start hotel search."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🏨 <b>Поиск отелей</b>\n\n"
            "Введи город или курорт:\n"
            "Например: Сочи, Санкт-Петербург, Дубай, Пхукет",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    else:
        await update.message.reply_text(
            "🏨 <b>Поиск отелей</b>\n\n"
            "Введи город:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    return HOTEL_CITY


async def hotel_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hotel city input."""
    context.user_data['hotel_city'] = update.message.text.strip()
    
    await update.message.reply_text(
        f"🏨 Город: <b>{context.user_data['hotel_city']}</b>\n\n"
        "Введи дату заезда (ДД.ММ.ГГГГ):",
        parse_mode="HTML",
        reply_markup=get_date_keyboard(date.today().year, date.today().month, "hotel_checkin")
    )
    return HOTEL_CHECKIN


async def hotel_checkin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hotel check-in date selection."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("hotel_checkin_day_"):
        _, _, _, year, month, day = data.split("_")
        selected_date = date(int(year), int(month), int(day))
        context.user_data['hotel_checkin'] = selected_date.strftime("%d.%m.%Y")
        
        await query.edit_message_text(
            f"🏨 Заезд: <b>{context.user_data['hotel_checkin']}</b>\n\n"
            "Введи дату выезда (ДД.ММ.ГГГГ):",
            parse_mode="HTML",
            reply_markup=get_date_keyboard(date.today().year, date.today().month, "hotel_checkout")
        )
        return HOTEL_CHECKOUT
    
    return HOTEL_CHECKIN


async def hotel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hotel checkout date."""
    query = update.callback_query
    if query:
        await query.answer()
        data = query.data
        if data.startswith("hotel_checkout_day_"):
            _, _, _, year, month, day = data.split("_")
            selected_date = date(int(year), int(month), int(day))
            context.user_data['hotel_checkout'] = selected_date.strftime("%d.%m.%Y")
        else:
            return HOTEL_CHECKOUT
    else:
        text = update.message.text.strip()
        try:
            datetime.strptime(text, "%d.%m.%Y")
            context.user_data['hotel_checkout'] = text
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используй ДД.ММ.ГГГГ",
                reply_markup=get_cancel_keyboard()
            )
            return HOTEL_CHECKOUT
    
    await (query.edit_message_text if query else update.message.reply_text)(
        f"🏨 Заезд: <b>{context.user_data['hotel_checkin']}</b> → Выезд: <b>{context.user_data['hotel_checkout']}</b>\n\n"
        "Сколько гостей и комнат?\n"
        "Формат: <b>взрослые дети комнаты</b> (например: 2 0 1)\n"
        "Дети указывай возрастом через запятую: 2 5,7 1",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    return HOTEL_GUESTS


async def hotel_guests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hotel guests input and search."""
    text = update.message.text.strip()
    parts = text.split()
    
    try:
        adults = int(parts[0]) if parts else 2
        children_ages = []
        if len(parts) > 1 and parts[1] != '0':
            children_ages = [int(x) for x in parts[1].split(',')]
        rooms = int(parts[2]) if len(parts) > 2 else 1
    except (ValueError, IndexError):
        adults, children_ages, rooms = 2, [], 1
    
    context.user_data['hotel_adults'] = adults
    context.user_data['hotel_children'] = children_ages
    context.user_data['hotel_rooms'] = rooms
    
    await update.message.reply_text("🔍 Ищу отели...")
    
    return await search_hotels(update, context)


async def search_hotels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Search hotels and show results."""
    city = context.user_data.get('hotel_city')
    checkin = context.user_data.get('hotel_checkin')
    checkout = context.user_data.get('hotel_checkout')
    adults = context.user_data.get('hotel_adults', 2)
    rooms = context.user_data.get('hotel_rooms', 1)
    
    if not all([city, checkin, checkout]):
        await update.message.reply_text("❌ Не все данные заполнены")
        return ConversationHandler.END
    
    try:
        hotels = await travel_api_client.search_hotels(
            city=city,
            check_in=checkin,
            check_out=checkout,
            adults=adults,
            rooms=rooms,
        )
        
        # Save search history
        user = update.effective_user
        async with get_session() as session:
            search = SearchHistory(
                user_id=user.id,
                search_type="hotels",
                query_params={
                    "city": city,
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": adults,
                    "rooms": rooms,
                },
                results_count=len(hotels),
            )
            session.add(search)
        
        if not hotels:
            text = "😔 Отели не найдены. Попробуй другие даты или город."
            keyboard = get_main_keyboard()
        else:
            nights = (datetime.strptime(checkout, "%d.%m.%Y") - datetime.strptime(checkin, "%d.%m.%Y")).days
            text = (
                f"🏨 <b>Найдено {len(hotels)} отелей</b>\n"
                f"📍 {city} | {checkin} → {checkout} ({nights} ночей)\n"
                f"👥 {adults} взрослых, {rooms} номера\n\n"
                "Выбери отель для подробностей:"
            )
            keyboard = get_hotel_results_keyboard(hotels)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Hotel search error: {e}")
        await update.message.reply_text(
            "❌ Ошибка поиска. Попробуй позже.",
            reply_markup=get_main_keyboard()
        )
    
    return ConversationHandler.END


async def hotel_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show hotel details."""
    query = update.callback_query
    await query.answer()
    
    hotel_id = query.data.replace("hotel_detail_", "")
    
    # In real implementation, fetch from cache
    detail_text = (
        f"🏨 <b>Отель: Grand Hotel {context.user_data.get('hotel_city', 'City')}</b>\n\n"
        f"⭐ Рейтинг: 4.5/5 (1200 отзывов)\n"
        f"📍 Адрес: Центр города\n"
        f"💰 Цена: 8 000 RUB/ночь\n"
        f"🛏 Номер: Стандарт, 2 взрослых\n\n"
        f"🏊 Удобства:\n"
        f"• Бесплатный WiFi\n"
        f"• Завкруг входит в цену\n"
        f"• Бассейн и спа\n"
        f"• Фитнес-центр\n"
        f"• Парковка\n\n"
        f"📋 Условия:\n"
        f"• Бесплатная отмена до заезда\n"
        f"• Оплата на месте или онлайн\n"
        f"• Заезд с 14:00, выезд до 12:00"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Забронировать", url="https://example.com/book")],
        [InlineKeyboardButton("⭐ В избранное", callback_data=f"bookmark_hotel_{hotel_id}")],
        [InlineKeyboardButton("⬅️ К результатам", callback_data="hotels_page_0")],
    ])
    
    await query.edit_message_text(detail_text, parse_mode="HTML", reply_markup=keyboard)
    return ConversationHandler.END


async def hotel_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hotel results pagination."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пагинация отелей")
    return ConversationHandler.END


async def bookmark_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save hotel to bookmarks."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    hotel_id = query.data.replace("bookmark_hotel_", "")
    
    async with get_session() as session:
        bookmark = Bookmark(
            user_id=user.id,
            bookmark_type="hotel",
            title=f"Отель {hotel_id}",
            city=context.user_data.get('hotel_city'),
            external_id=hotel_id,
            extra_data={
                "checkin": context.user_data.get('hotel_checkin'),
                "checkout": context.user_data.get('hotel_checkout'),
                "adults": context.user_data.get('hotel_adults'),
            },
        )
        session.add(bookmark)
    
    await query.answer("✅ Отель добавлен в избранное!", show_alert=True)
    return ConversationHandler.END


async def cancel_hotel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel hotel search."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Поиск отменён", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("❌ Поиск отменён", reply_markup=get_main_keyboard())
    return ConversationHandler.END
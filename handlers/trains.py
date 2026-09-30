from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from datetime import datetime, date
import logging

from database import get_session
from models import User, SearchHistory, Bookmark
from keyboards import (
    get_main_keyboard, get_cancel_keyboard,
    get_date_keyboard,
)
from api_clients import travel_api_client

logger = logging.getLogger(__name__)

# Train conversation states
TRAIN_ORIGIN, TRAIN_DESTINATION, TRAIN_DATE = range(300, 303)


async def train_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start train search."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🚂 <b>Поиск билетов на поезда</b>\n\n"
            "Введи станцию отправления:\n"
            "Например: Москва, Санкт-Петербург, Казань",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    else:
        await update.message.reply_text(
            "🚂 <b>Поиск билетов на поезда</b>\n\n"
            "Введи станцию отправления:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    return TRAIN_ORIGIN


async def train_origin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle train origin."""
    context.user_data['train_origin'] = update.message.text.strip()
    
    await update.message.reply_text(
        f"🚂 Отправление: <b>{context.user_data['train_origin']}</b>\n\n"
        "Введи станцию назначения:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    return TRAIN_DESTINATION


async def train_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle train destination."""
    context.user_data['train_destination'] = update.message.text.strip()
    
    await update.message.reply_text(
        f"🚂 Маршрут: <b>{context.user_data['train_origin']} → {context.user_data['train_destination']}</b>\n\n"
        "Введи дату отправления (ДД.ММ.ГГГГ):",
        parse_mode="HTML",
        reply_markup=get_date_keyboard(date.today().year, date.today().month, "train_depart")
    )
    return TRAIN_DATE


async def train_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle train date selection."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("train_depart_day_"):
        _, _, _, year, month, day = data.split("_")
        selected_date = date(int(year), int(month), int(day))
        context.user_data['train_date'] = selected_date.strftime("%d.%m.%Y")
        
        return await search_trains(update, context)
    
    return TRAIN_DATE


async def search_trains(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Search trains and show results."""
    origin = context.user_data.get('train_origin')
    destination = context.user_data.get('train_destination')
    depart_date = context.user_data.get('train_date')
    
    if not all([origin, destination, depart_date]):
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Не все данные заполнены")
        else:
            await update.message.reply_text("❌ Не все данные заполнены")
        return ConversationHandler.END
    
    if update.callback_query:
        await update.callback_query.edit_message_text("🔍 Ищу поезда...")
    else:
        await update.message.reply_text("🔍 Ищу поезда...")
    
    try:
        trains = await travel_api_client.search_trains(
            origin=origin,
            destination=destination,
            departure_date=depart_date,
        )
        
        # Save search history
        user = update.effective_user
        async with get_session() as session:
            search = SearchHistory(
                user_id=user.id,
                search_type="trains",
                query_params={
                    "origin": origin,
                    "destination": destination,
                    "date": depart_date,
                },
                results_count=len(trains),
            )
            session.add(search)
        
        if not trains:
            text = "😔 Поезда не найдены. Попробуй другие даты или направления."
            keyboard = get_main_keyboard()
        else:
            text = (
                f"🚂 <b>Найдено {len(trains)} поездов</b>\n"
                f"{origin} → {destination} на {depart_date}\n\n"
                "Выбери поезд:"
            )
            
            keyboard = InlineKeyboardMarkup([])
            for train in trains:
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        f"{train['train_name']} {train['train_number']} | {train['departure_time'][:16]} → {train['arrival_time'][:16]} | {train['price']} {train['currency']}",
                        callback_data=f"train_detail_{train['id']}"
                    )
                ])
            keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ К поиску", callback_data="search_trains")])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Train search error: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Ошибка поиска. Попробуй позже.",
                reply_markup=get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка поиска. Попробуй позже.",
                reply_markup=get_main_keyboard()
            )
    
    return ConversationHandler.END


async def train_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show train details."""
    query = update.callback_query
    await query.answer()
    
    train_id = query.data.replace("train_detail_", "")
    
    detail_text = (
        f"🚂 <b>Поезд: Сапсан 001А</b>\n\n"
        f"🚉 Маршрут: Москва → Санкт-Петербург\n"
        f"🕐 Отправление: 07:00 → Прибытие: 11:30\n"
        f"⏱ В пути: 4ч 30м\n"
        f"💺 Класс: Эконом\n"
        f"💰 Цена: 3 500 RUB\n\n"
        f"🎫 Включено:\n"
        f"• Места в вагоне\n"
        f"• Багаж до 36 кг\n"
        f"• WiFi в вагоне\n"
        f"• Розетки у каждого места\n\n"
        f"Для бронирования перейди на сайт РЖД."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Забронировать на РЖД", url="https://rzd.ru")],
        [InlineKeyboardButton("⭐ В избранное", callback_data=f"bookmark_train_{train_id}")],
        [InlineKeyboardButton("⬅️ К результатам", callback_data="search_trains")],
    ])
    
    await query.edit_message_text(detail_text, parse_mode="HTML", reply_markup=keyboard)
    return ConversationHandler.END


async def bookmark_train(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save train to bookmarks."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    train_id = query.data.replace("bookmark_train_", "")
    
    async with get_session() as session:
        bookmark = Bookmark(
            user_id=user.id,
            bookmark_type="train",
            title=f"Поезд {train_id}",
            external_id=train_id,
            extra_data={
                "origin": context.user_data.get('train_origin'),
                "destination": context.user_data.get('train_destination'),
                "date": context.user_data.get('train_date'),
            },
        )
        session.add(bookmark)
    
    await query.answer("✅ Поезд добавлен в избранное!", show_alert=True)
    return ConversationHandler.END


async def cancel_train(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel train search."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Поиск отменён", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("❌ Поиск отменён", reply_markup=get_main_keyboard())
    return ConversationHandler.END
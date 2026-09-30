from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
import logging

from database import get_session, get_or_create_user
from models import User, ConversationContext
from keyboards import (
    get_main_keyboard, get_cancel_keyboard,
    get_flight_search_keyboard, get_hotel_search_keyboard,
    get_train_search_keyboard, get_itinerary_keyboard, get_profile_keyboard,
)
from api_clients import travel_api_client

logger = logging.getLogger(__name__)

# Conversation states
(
    MAIN_MENU,
    FLIGHT_ORIGIN, FLIGHT_DESTINATION, FLIGHT_DATE, FLIGHT_RETURN_DATE,
    HOTEL_CITY, HOTEL_CHECKIN, HOTEL_CHECKOUT, HOTEL_GUESTS,
    TRAIN_ORIGIN, TRAIN_DESTINATION, TRAIN_DATE,
    ITINERARY_DESTINATION, ITINERARY_DATES, ITINERARY_PREFERENCES,
    PROFILE_EDIT, PROFILE_HOME_CITY, PROFILE_TRAVEL_STYLE, PROFILE_BUDGET,
) = range(19)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler."""
    user = update.effective_user
    
    async with get_session() as session:
        await get_or_create_user(
            session,
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or "ru",
            is_premium=user.is_premium or False,
        )
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я твой помощник для путешествий ✈️🏨🚂\n\n"
        "Что я умею:\n"
        "🔍 Находить авиабилеты и билеты на поезда\n"
        "🏨 Подбирать отели и апартаменты\n"
        "🗺️ Составлять индивидуальные маршруты\n"
        "⭐ Сохранять избранное и историю поисков\n"
        "👤 Хранить твои предпочтения\n\n"
        "Выбери действие в меню ниже:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
    
    return MAIN_MENU


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Help command handler."""
    help_text = (
        "📖 <b>Помощник по путешествиям</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать работу\n"
        "/help - Эта справка\n"
        "/menu - Главное меню\n"
        "/profile - Профиль\n"
        "/trips - Мои поездки\n"
        "/search - Быстрый поиск\n\n"
        "<b>Как пользоваться:</b>\n"
        "1. Нажми кнопку в меню для выбора типа поиска\n"
        "2. Введи параметры (город, даты, пассажиры)\n"
        "3. Посмотри результаты и выбери подходящий\n"
        "4. Сохрани в поездку или добавь в избранное\n\n"
        "<b>ИИ-планировщик:</b>\n"
        "Напиши в чате: «Хочу поехать в Санкт-Петербург на 3 дня в феврале, люблю музеи и вкусно поесть»\n"
        "И я составлю подробный маршрут!\n\n"
        "<b>Поддержка:</b> @travel_bot_support"
    )
    
    await update.message.reply_text(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())
    return MAIN_MENU


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show main menu."""
    await update.message.reply_text(
        "🏠 Главное меню:",
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu button presses."""
    text = update.message.text
    
    if text == "🔍 Найти билеты":
        await update.message.reply_text(
            "✈️ <b>Поиск авиабилетов</b>\n\nВыбери тип поиска:",
            parse_mode="HTML",
            reply_markup=get_flight_search_keyboard()
        )
        return MAIN_MENU
    
    elif text == "🏨 Отели":
        await update.message.reply_text(
            "🏨 <b>Поиск отелей</b>\n\nВыбери тип поиска:",
            parse_mode="HTML",
            reply_markup=get_hotel_search_keyboard()
        )
        return MAIN_MENU
    
    elif text == "🚂 Поезда":
        await update.message.reply_text(
            "🚂 <b>Поиск билетов на поезда</b>\n\nВыбери тип поиска:",
            parse_mode="HTML",
            reply_markup=get_train_search_keyboard()
        )
        return MAIN_MENU
    
    elif text == "🗺️ Маршруты":
        await update.message.reply_text(
            "🗺️ <b>Планировщик маршрутов</b>\n\nВыбери действие:",
            parse_mode="HTML",
            reply_markup=get_itinerary_keyboard()
        )
        return MAIN_MENU
    
    elif text == "⭐ Избранное":
        await show_bookmarks(update, context)
        return MAIN_MENU
    
    elif text == "👤 Профиль":
        await show_profile(update, context)
        return MAIN_MENU
    
    elif text == "❓ Помощь":
        await help_command(update, context)
        return MAIN_MENU
    
    elif text == "❌ Отмена":
        await update.message.reply_text(
            "❌ Действие отменено",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    else:
        # Try to process as natural language query for AI itinerary
        await process_natural_language(update, context)
        return MAIN_MENU


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user profile."""
    user = update.effective_user
    
    async with get_session() as session:
        from database import get_user
        db_user = await get_user(session, user.id)
        
        if not db_user:
            await update.message.reply_text("Профиль не найден. Нажми /start")
            return MAIN_MENU
        
        profile_text = (
            f"👤 <b>Твой профиль</b>\n\n"
            f"🆔 ID: <code>{db_user.id}</code>\n"
            f"👤 Имя: {db_user.first_name or '-'}\n"
            f"📛 Фамилия: {db_user.last_name or '-'}\n"
            f"🔗 Username: @{db_user.username or 'нет'}\n"
            f"🌐 Язык: {db_user.language_code}\n"
            f"💎 Premium: {'Да' if db_user.is_premium else 'Нет'}\n\n"
            f"⚙️ <b>Настройки:</b>\n"
            f"🏠 Домашний город: {db_user.home_city or 'не задан'}\n"
            f"🎒 Стиль путешествий: {db_user.travel_style or 'не задан'}\n"
            f"💰 Валюта: {db_user.preferred_currency}\n"
            f"🔔 Уведомления: {'Вкл' if db_user.notifications_enabled else 'Выкл'}\n"
        )
        
        await update.message.reply_text(
            profile_text,
            parse_mode="HTML",
            reply_markup=get_profile_keyboard()
        )
    
    return MAIN_MENU


async def show_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user bookmarks."""
    user = update.effective_user
    
    async with get_session() as session:
        from models import Bookmark
        result = await session.execute(
            select(Bookmark).where(Bookmark.user_id == user.id).order_by(Bookmark.created_at.desc())
        )
        bookmarks = result.scalars().all()
    
    if not bookmarks:
        await update.message.reply_text(
            "⭐ У тебя пока нет избранного.\n\n"
            "Добавляй отели, билеты или места через поиск!",
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU
    
    text = "⭐ <b>Твое избранное</b>\n\n"
    for i, bm in enumerate(bookmarks[:10], 1):
        text += f"{i}. <b>{bm.title}</b> ({bm.bookmark_type})\n"
        if bm.city:
            text += f"   📍 {bm.city}, {bm.country}\n"
        text += "\n"
    
    if len(bookmarks) > 10:
        text += f"... и ещё {len(bookmarks) - 10} записей"
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_main_keyboard())
    return MAIN_MENU


async def process_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process natural language query for AI itinerary."""
    from api_clients import openrouter_client
    
    user_text = update.message.text
    
    system_prompt = (
        "Ты - эксперт по путешествиям. Пользователь описывает желаемое путешествие на естественном языке. "
        "Извлеки ключевую информацию и предложи план. Отвечай на русском языке.\n\n"
        "Извлеки: город/страна, даты/длительность, бюджет, интересы (еда, музеи, природа, пляжи, ночная жизнь), "
        "состав туристов (один, пара, семья с детьми), предпочтения по транспорту и жилью.\n\n"
        "Формат ответа:\n"
        "🎯 <b>Понимание запроса:</b> краткое резюме\n"
        "📍 <b>Направление:</b> город, страна\n"
        "📅 <b>Даты:</b> предполагаемые даты или длительность\n"
        "💰 <b>Бюджет:</b> если указан\n"
        "🎒 <b>Интересы:</b> список\n"
        "👥 <b>Туристы:</b> состав\n\n"
        "🤖 <b>Предлагаю:</b> краткий план на каждый день\n"
        "\n"
        "В конце предложи: 'Хочешь, я сохраню этот маршрут и поищу билеты/отели?'"
    )
    
    await update.message.reply_text("🤔 Анализирую твой запрос...")
    
    try:
        response = await openrouter_client.chat_completion(
            messages=[{"role": "user", "content": user_text}],
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000,
        )
        
        await update.message.reply_text(
            response,
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        await update.message.reply_text(
            "❌ Не удалось обработать запрос. Попробуй еще раз или выбери действие из меню.",
            reply_markup=get_main_keyboard()
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation."""
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Попробуй еще раз или нажми /start",
            reply_markup=get_main_keyboard()
        )
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from datetime import datetime, date, timedelta
import logging
import json

from database import get_session
from models import User, Trip, ItineraryItem, SearchHistory
from keyboards import (
    get_main_keyboard, get_cancel_keyboard,
    get_itinerary_keyboard, get_trip_actions_keyboard,
    get_date_keyboard,
)
from api_clients import travel_api_client, openrouter_client

logger = logging.getLogger(__name__)

# Itinerary conversation states
ITINERARY_DESTINATION, ITINERARY_DATES, ITINERARY_PREFERENCES, ITINERARY_BUDGET = range(400, 404)


async def itinerary_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show itinerary menu."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🗺️ <b>Планировщик маршрутов</b>\n\nВыбери действие:",
            parse_mode="HTML",
            reply_markup=get_itinerary_keyboard()
        )
    else:
        await update.message.reply_text(
            "🗺️ <b>Планировщик маршрутов</b>\n\nВыбери действие:",
            parse_mode="HTML",
            reply_markup=get_itinerary_keyboard()
        )
    return ConversationHandler.END


async def create_itinerary_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start creating itinerary."""
    query = update.callback_query
    if query:
        await query.answer()
        # Send new message instead of editing (reply keyboard can't replace inline keyboard)
        await query.message.reply_text(
            "🗺️ <b>Создание маршрута</b>\n\n"
            "Куда хочешь поехать? Введи страну и/или город:\n"
            "Например: Таиланд, Пхукет или Италия, Рим, Флоренция",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    else:
        await update.message.reply_text(
            "🗺️ <b>Создание маршрута</b>\n\n"
            "Куда хочешь поехать? Введи страну и/или город:\n"
            "Например: Таиланд, Пхукет или Италия, Рим, Флоренция",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    return ITINERARY_DESTINATION


async def itinerary_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle itinerary destination."""
    context.user_data['itinerary_destination'] = update.message.text.strip()
    
    await update.message.reply_text(
        f"📍 Направление: <b>{context.user_data['itinerary_destination']}</b>\n\n"
        "На какие даты планируешь поездку?\n"
        "Введи: <b>ДД.ММ.ГГГГ ДД.ММ.ГГГГ</b> (заезд выезд)\n"
        "Или просто количество дней: <b>5</b>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    return ITINERARY_DATES


async def itinerary_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle itinerary dates."""
    text = update.message.text.strip()
    parts = text.split()
    
    try:
        if len(parts) == 1 and parts[0].isdigit():
            # Just number of days
            days = int(parts[0])
            start_date = date.today() + timedelta(days=7)  # Default to next week
            end_date = start_date + timedelta(days=days)
            context.user_data['itinerary_start'] = start_date.strftime("%d.%m.%Y")
            context.user_data['itinerary_end'] = end_date.strftime("%d.%m.%Y")
            context.user_data['itinerary_days'] = days
        elif len(parts) == 2:
            # Two dates
            start = datetime.strptime(parts[0], "%d.%m.%Y").date()
            end = datetime.strptime(parts[1], "%d.%m.%Y").date()
            context.user_data['itinerary_start'] = parts[0]
            context.user_data['itinerary_end'] = parts[1]
            context.user_data['itinerary_days'] = (end - start).days
        else:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Используй: ДД.ММ.ГГГГ ДД.ММ.ГГГГ или просто число дней",
            reply_markup=get_cancel_keyboard()
        )
        return ITINERARY_DATES
    
    await update.message.reply_text(
        f"📅 Даты: <b>{context.user_data['itinerary_start']} — {context.user_data['itinerary_end']}</b> ({context.user_data['itinerary_days']} дней)\n\n"
        "Расскажи о своих предпочтениях:\n"
        "• Что любишь: музеи, еда, природа, пляжи, шопинг, ночная жизнь\n"
        "• С кем едешь: один, пара, семья с детьми, друзья\n"
        "• Темп: расслабленный / насыщенный\n"
        "• Бюджет на развлечения/еду в день (примерно)\n\n"
        "Напиши свободным текстом:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    return ITINERARY_PREFERENCES


async def itinerary_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle itinerary preferences and generate with AI."""
    context.user_data['itinerary_preferences'] = update.message.text.strip()
    
    await update.message.reply_text("🤖 ИИ составляет твой идеальный маршрут...")
    
    return await generate_itinerary(update, context)


async def generate_itinerary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate itinerary using AI."""
    destination = context.user_data.get('itinerary_destination')
    start_date = context.user_data.get('itinerary_start')
    end_date = context.user_data.get('itinerary_end')
    days = context.user_data.get('itinerary_days')
    preferences = context.user_data.get('itinerary_preferences')
    
    system_prompt = (
        "Ты - эксперт по путешествиям. Составь подробный день-за-днём маршрут.\n\n"
        f"Направление: {destination}\n"
        f"Даты: {start_date} — {end_date} ({days} дней)\n"
        f"Предпочтения: {preferences}\n\n"
        "Создай маршрут в формате JSON:\n"
        "{\n"
        '  "title": "Название маршрута",\n'
        '  "description": "Краткое описание",\n'
        '  "days": [\n'
        '    {\n'
        '      "day": 1,\n'
        '      "date": "ДД.ММ.ГГГГ",\n'
        '      "title": "Название дня",\n'
        '      "items": [\n'
        '        {\n'
        '          "time": "09:00",\n'
        '          "title": "Название места/активности",\n'
        '          "description": "Описание",\n'
        '          "type": "sightseeing|restaurant|activity|transport|accommodation",\n'
        '          "address": "Адрес",\n'
        '          "estimated_cost": 1000,\n'
        '          "currency": "RUB"\n'
        '        }\n'
        '      ]\n'
        '    }\n'
        '  ],\n'
        '  "total_estimated_cost": 50000,\n'
        '  "currency": "RUB",\n'
        '  "tips": ["Совет 1", "Совет 2"]\n'
        "}\n\n"
        "Типы: sightseeing (достопримечательности), restaurant (еда), activity (активности), "
        "transport (транспорт), accommodation (проживание).\n"
        "Сделай маршрут реалистичным с учётом логистики, времени работы мест, перемещений."
    )
    
    try:
        response = await openrouter_client.chat_completion(
            messages=[{"role": "user", "content": "Составь маршрут"}],
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=3000,
        )
        
        # Parse JSON from response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            itinerary_data = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")
        
        # Save to database
        user = update.effective_user
        async with get_session() as session:
            trip = Trip(
                user_id=user.id,
                title=itinerary_data.get('title', f'Путешествие в {destination}'),
                description=itinerary_data.get('description', ''),
                start_date=datetime.strptime(start_date, "%d.%m.%Y"),
                end_date=datetime.strptime(end_date, "%d.%m.%Y"),
                destination_country=destination.split(',')[0].strip(),
                destination_city=destination.split(',')[1].strip() if ',' in destination else None,
                status="planning",
                budget=itinerary_data.get('total_estimated_cost'),
                currency=itinerary_data.get('currency', 'RUB'),
            )
            session.add(trip)
            await session.flush()
            
            # Add itinerary items
            for day_data in itinerary_data.get('days', []):
                day_num = day_data['day']
                for item_data in day_data.get('items', []):
                    item = ItineraryItem(
                        trip_id=trip.id,
                        day_number=day_num,
                        start_time=datetime.strptime(f"{day_data['date']} {item_data.get('time', '09:00')}", "%d.%m.%Y %H:%M"),
                        title=item_data['title'],
                        description=item_data.get('description'),
                        item_type=item_data.get('type', 'activity'),
                        address=item_data.get('address'),
                        estimated_cost=item_data.get('estimated_cost'),
                        currency=item_data.get('currency', 'RUB'),
                    )
                    session.add(item)
            
            # Save search history
            search = SearchHistory(
                user_id=user.id,
                search_type="itinerary",
                query_params={
                    "destination": destination,
                    "start": start_date,
                    "end": end_date,
                    "preferences": preferences,
                },
                results_count=1,
            )
            session.add(search)
        
        # Format response
        text = f"🗺️ <b>{itinerary_data.get('title', 'Маршрут')}</b>\n"
        text += f"{itinerary_data.get('description', '')}\n\n"
        
        for day_data in itinerary_data.get('days', []):
            text += f"\n📅 <b>День {day_data['day']} ({day_data['date']}) — {day_data['title']}</b>\n"
            for item in day_data.get('items', []):
                cost = f" — {item.get('estimated_cost', 0)} {item.get('currency', 'RUB')}" if item.get('estimated_cost') else ""
                text += f"  🕐 {item.get('time', '09:00')} — {item['title']}{cost}\n"
                if item.get('description'):
                    text += f"     {item['description']}\n"
        
        text += f"\n💰 <b>Примерная стоимость: {itinerary_data.get('total_estimated_cost', 0)} {itinerary_data.get('currency', 'RUB')}</b>\n"
        
        if itinerary_data.get('tips'):
            text += "\n💡 <b>Советы:</b>\n"
            for tip in itinerary_data['tips']:
                text += f"• {tip}\n"
        
        keyboard = get_trip_actions_keyboard(trip.id)
        
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Itinerary generation error: {e}")
        await update.message.reply_text(
            "❌ Не удалось составить маршрут. Попробуй еще раз.",
            reply_markup=get_main_keyboard()
        )
    
    return ConversationHandler.END


async def ai_itinerary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """AI itinerary from natural language."""
    query = update.callback_query
    if query:
        await query.answer()
        # Send new message instead of editing (reply keyboard can't replace inline keyboard)
        await query.message.reply_text(
            "🤖 <b>ИИ-планировщик</b>\n\n"
            "Опиши своё идеальное путешествие свободным текстом:\n\n"
            "Например:\n"
            "«Хочу поехать в Италию на 7 дней в мае. Люблю историю, вкусную еду и вино. "
            "Еду с женой, бюджет средний. Хочу увидеть Рим, Флоренцию и Тоскану.»",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
    
    # Next message will be processed by natural language handler in basic.py
    return ConversationHandler.END


async def my_itineraries(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show user's trips."""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = update.effective_user
    async with get_session() as session:
        result = await session.execute(
            select(Trip).where(Trip.user_id == user.id).order_by(Trip.created_at.desc())
        )
        trips = result.scalars().all()
    
    if not trips:
        text = "📋 У тебя пока нет сохранённых поездок.\nСоздай первый маршрут!"
        keyboard = get_itinerary_keyboard()
    else:
        text = "📋 <b>Твои поездки:</b>\n\n"
        keyboard = InlineKeyboardMarkup([])
        for trip in trips[:10]:
            status_emoji = {"planning": "📝", "booked": "✅", "completed": "🏁", "cancelled": "❌"}.get(trip.status, "📝")
            text += f"{status_emoji} <b>{trip.title}</b>\n"
            text += f"   📅 {trip.start_date.strftime('%d.%m.%Y')} — {trip.end_date.strftime('%d.%m.%Y')}\n"
            text += f"   📍 {trip.destination_city or ''}, {trip.destination_country}\n"
            if trip.budget:
                text += f"   💰 {trip.budget:,.0f} {trip.currency}\n"
            text += "\n"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(f"{status_emoji} {trip.title}", callback_data=f"view_trip_{trip.id}")
            ])
        keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="itinerary_menu")])
    
    if query:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    
    return ConversationHandler.END


async def view_trip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """View trip details."""
    query = update.callback_query
    await query.answer()
    
    trip_id = int(query.data.replace("view_trip_", ""))
    
    async with get_session() as session:
        trip = await session.get(Trip, trip_id)
        if not trip:
            await query.edit_message_text("Поездка не найдена")
            return ConversationHandler.END
        
        # Get itinerary items
        result = await session.execute(
            select(ItineraryItem).where(ItineraryItem.trip_id == trip_id).order_by(ItineraryItem.day_number, ItineraryItem.start_time)
        )
        items = result.scalars().all()
    
    text = f"🗺️ <b>{trip.title}</b>\n"
    if trip.description:
        text += f"{trip.description}\n\n"
    text += f"📅 {trip.start_date.strftime('%d.%m.%Y')} — {trip.end_date.strftime('%d.%m.%Y')}\n"
    text += f"📍 {trip.destination_city or ''}, {trip.destination_country}\n"
    if trip.budget:
        text += f"💰 Бюджет: {trip.budget:,.0f} {trip.currency}\n"
    text += f"📊 Статус: {trip.status}\n\n"
    
    current_day = None
    for item in items:
        if item.day_number != current_day:
            current_day = item.day_number
            text += f"\n📅 <b>День {current_day}</b>\n"
        
        time_str = item.start_time.strftime('%H:%M') if item.start_time else "—"
        cost_str = f" — {item.estimated_cost:,.0f} {item.currency}" if item.estimated_cost else ""
        text += f"  🕐 {time_str} — {item.title}{cost_str}\n"
        if item.description:
            text += f"     {item.description}\n"
    
    keyboard = get_trip_actions_keyboard(trip.id)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    return ConversationHandler.END


async def popular_destinations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show popular destinations."""
    query = update.callback_query
    if query:
        await query.answer()
    
    destinations = await travel_api_client.get_popular_destinations()
    
    text = "🌍 <b>Популярные направления</b>\n\n"
    keyboard_rows = []
    
    for dest in destinations:
        text += f"📍 <b>{dest['city']}</b>, {dest['country']} — {dest['description']}\n"
        keyboard_rows.append([
            InlineKeyboardButton(
                f"🗺️ Маршрут в {dest['city']}",
                callback_data=f"quick_itinerary_{dest['city']}_{dest['country']}"
            )
        ])
    
    keyboard_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="itinerary_menu")])
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    if query:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    
    return ConversationHandler.END


async def quick_itinerary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Quick itinerary for popular destination."""
    query = update.callback_query
    await query.answer()
    
    # Parse city and country from callback data
    _, _, city, country = query.data.split("_", 3)
    
    context.user_data['itinerary_destination'] = f"{city}, {country}"
    context.user_data['itinerary_start'] = (date.today() + timedelta(days=14)).strftime("%d.%m.%Y")
    context.user_data['itinerary_end'] = (date.today() + timedelta(days=21)).strftime("%d.%m.%Y")
    context.user_data['itinerary_days'] = 7
    context.user_data['itinerary_preferences'] = "Популярные достопримечательности, хорошая еда, комфортное проживание"
    
    await query.edit_message_text("🤖 ИИ составляет маршрут...")
    return await generate_itinerary(update, context)


async def cancel_itinerary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel itinerary creation."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Создание отменено", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("❌ Создание отменено", reply_markup=get_main_keyboard())
    return ConversationHandler.END
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Optional


# Main menu keyboard
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Get main reply keyboard."""
    keyboard = [
        [KeyboardButton("🔍 Найти билеты"), KeyboardButton("🏨 Отели")],
        [KeyboardButton("🚂 Поезда"), KeyboardButton("🗺️ Маршруты")],
        [KeyboardButton("⭐ Избранное"), KeyboardButton("👤 Профиль")],
        [KeyboardButton("❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Get cancel keyboard."""
    keyboard = [[KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


# Inline keyboards
def get_flight_search_keyboard() -> InlineKeyboardMarkup:
    """Get flight search options keyboard."""
    keyboard = [
        [InlineKeyboardButton("✈️ Авиабилеты", callback_data="search_flights")],
        [InlineKeyboardButton("🔄 Туда-обратно", callback_data="search_flights_round")],
        [InlineKeyboardButton("🔀 Многородковые", callback_data="search_flights_multi")],
        [InlineKeyboardButton("📅 Гибкие даты", callback_data="search_flights_flexible")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_hotel_search_keyboard() -> InlineKeyboardMarkup:
    """Get hotel search options keyboard."""
    keyboard = [
        [InlineKeyboardButton("🏨 Поиск отелей", callback_data="search_hotels")],
        [InlineKeyboardButton("🏠 Апартаменты", callback_data="search_apartments")],
        [InlineKeyboardButton("⭐ По рейтингу", callback_data="search_hotels_rating")],
        [InlineKeyboardButton("💰 По цене", callback_data="search_hotels_price")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_train_search_keyboard() -> InlineKeyboardMarkup:
    """Get train search options keyboard."""
    keyboard = [
        [InlineKeyboardButton("🚂 ЖД билеты (РЖД)", callback_data="search_trains")],
        [InlineKeyboardButton("🚄 Скоростные (Сапсан/Ласточка)", callback_data="search_trains_fast")],
        [InlineKeyboardButton("🌙 Ночные поезда", callback_data="search_trains_night")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_itinerary_keyboard() -> InlineKeyboardMarkup:
    """Get itinerary planning keyboard."""
    keyboard = [
        [InlineKeyboardButton("🗺️ Создать маршрут", callback_data="create_itinerary")],
        [InlineKeyboardButton("🤖 ИИ-планировщик", callback_data="ai_itinerary")],
        [InlineKeyboardButton("📋 Мои маршруты", callback_data="my_itineraries")],
        [InlineKeyboardButton("🌍 Популярные направления", callback_data="popular_destinations")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Get profile keyboard."""
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton("💰 Бюджет и валюта", callback_data="budget_settings")],
        [InlineKeyboardButton("🏠 Домашний город", callback_data="home_city")],
        [InlineKeyboardButton("🎒 Стиль путешествий", callback_data="travel_style")],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="notifications")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_flight_results_keyboard(flights: List[dict], page: int = 0, per_page: int = 3) -> InlineKeyboardMarkup:
    """Get keyboard for flight results with pagination."""
    keyboard = []
    start = page * per_page
    end = start + per_page
    
    for flight in flights[start:end]:
        keyboard.append([
            InlineKeyboardButton(
                f"{flight['airline']} {flight['flight_number']} - {flight['price']} {flight['currency']}",
                callback_data=f"flight_detail_{flight['id']}"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"🕐 {flight['departure_time'][:16]} → {flight['arrival_time'][:16]} | {flight['duration']}",
                callback_data="noop"
            )
        ])
    
    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"flights_page_{page-1}"))
    if end < len(flights):
        nav.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"flights_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("⬅️ К поиску", callback_data="search_flights")])
    return InlineKeyboardMarkup(keyboard)


def get_hotel_results_keyboard(hotels: List[dict], page: int = 0, per_page: int = 3) -> InlineKeyboardMarkup:
    """Get keyboard for hotel results with pagination."""
    keyboard = []
    start = page * per_page
    end = start + per_page
    
    for hotel in hotels[start:end]:
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ {hotel['rating']} {hotel['name']} - {hotel['price_per_night']} {hotel['currency']}/ночь",
                callback_data=f"hotel_detail_{hotel['id']}"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"📍 {hotel['address']} | {' | '.join(hotel['amenities'][:3])}",
                callback_data="noop"
            )
        ])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"hotels_page_{page-1}"))
    if end < len(hotels):
        nav.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"hotels_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("⬅️ К поиску", callback_data="search_hotels")])
    return InlineKeyboardMarkup(keyboard)


def get_trip_actions_keyboard(trip_id: int) -> InlineKeyboardMarkup:
    """Get keyboard for trip actions."""
    keyboard = [
        [InlineKeyboardButton("📋 Посмотреть маршрут", callback_data=f"view_itinerary_{trip_id}")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_trip_{trip_id}")],
        [InlineKeyboardButton("🎫 Бронирования", callback_data=f"trip_bookings_{trip_id}")],
        [InlineKeyboardButton("💰 Бюджет", callback_data=f"trip_budget_{trip_id}")],
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_trip_{trip_id}")],
        [InlineKeyboardButton("⬅️ К списку поездок", callback_data="my_itineraries")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    """Get confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{action}_{item_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_date_keyboard(year: int, month: int, callback_prefix: str) -> InlineKeyboardMarkup:
    """Generate calendar keyboard for date selection."""
    import calendar
    from datetime import date
    
    cal = calendar.monthcalendar(year, month)
    keyboard = []
    
    # Month/year header
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    keyboard.append([
        InlineKeyboardButton("⬅️", callback_data=f"{callback_prefix}_month_{year}_{month-1 if month > 1 else 12}"),
        InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="noop"),
        InlineKeyboardButton("➡️", callback_data=f"{callback_prefix}_month_{year}_{month+1 if month < 12 else 1}"),
    ])
    
    # Week days
    keyboard.append([
        InlineKeyboardButton(d, callback_data="noop") for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    ])
    
    # Days
    today = date.today()
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="noop"))
            else:
                callback_data = f"{callback_prefix}_day_{year}_{month}_{day}"
                if date(year, month, day) < today:
                    row.append(InlineKeyboardButton(f"·{day}·", callback_data="noop"))
                else:
                    row.append(InlineKeyboardButton(str(day), callback_data=callback_data))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)
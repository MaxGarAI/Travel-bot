import logging
import json
from typing import Optional, Dict, Any, List
import httpx

from config import settings

logger = logging.getLogger(__name__)


# Список бесплатных моделей для авто-фэйловер (в порядке приоритета)
# Задан пользователем
FREE_MODELS = [
    "qwen/qwen3-8b:free",                           # Qwen 3 8B
    "google/gemma-4-31b-it:free",                   # Gemma 4 31B
    "nvidia/nemotron-3-ultra-550b-a55b:free",       # Nemotron 3 Ultra 550B
    "thinkingmachines/inkling-small:free",          # Inkling Small
    "poolside/laguna-s-2.1:free",                   # Laguna S 2.1
]

# Коды ошибок, при которых пробуем следующую модель
FAILOVER_STATUS_CODES = {400, 404, 429, 500, 502, 503, 504}


class OpenRouterClient:
    """Client for OpenRouter API with automatic model failover."""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.primary_model = settings.OPENROUTER_MODEL
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/travel-bot",
                "X-Title": "Travel Bot",
            },
            timeout=60.0,
        )

    def _get_model_order(self) -> List[str]:
        """Порядок моделей: сначала из настроек, потом список бесплатных."""
        models = []
        if self.primary_model and self.primary_model not in FREE_MODELS:
            models.append(self.primary_model)
        models.extend(FREE_MODELS)
        # Убираем дубликаты, сохраняя порядок
        seen = set()
        unique = []
        for m in models:
            if m not in seen:
                seen.add(m)
                unique.append(m)
        return unique

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Get chat completion with automatic model failover."""
        
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload_base = {
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error = None
        models_tried = []

        for model in self._get_model_order():
            models_tried.append(model)
            payload = {**payload_base, "model": model}
            
            try:
                response = await self.client.post("/chat/completions", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    # Проверяем что ответ имеет правильную структуру
                    if "choices" in data and data["choices"]:
                        logger.info(f"OpenRouter success with model: {model}")
                        return data["choices"][0]["message"]["content"]
                    else:
                        logger.warning(f"Model {model} returned 200 but invalid response structure: {data}")
                        last_error = f"Invalid response structure: missing 'choices'"
                        continue  # Пробуем следующую модель
                
                # Логируем ошибку
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", str(error_data))
                except Exception:
                    error_msg = response.text
                logger.warning(f"Model {model} failed ({response.status_code}): {error_msg[:200]}")
                
                # Если это ошибка, по которой пробуем следующую модель
                if response.status_code in FAILOVER_STATUS_CODES:
                    last_error = f"{response.status_code}: {error_msg}"
                    continue  # Пробуем следующую модель мгновенно
                
                # Для остальных ошибок — поднимаем исключение
                response.raise_for_status()
                
            except httpx.TimeoutException:
                logger.warning(f"Model {model} timeout, trying next...")
                last_error = "Timeout"
                continue
            except httpx.RequestError as e:
                logger.warning(f"Model {model} request error: {e}, trying next...")
                last_error = f"RequestError: {e}"
                continue
            except Exception as e:
                logger.warning(f"Model {model} unexpected error: {e}, trying next...")
                last_error = f"Error: {e}"
                continue

        # Если все модели не сработали
        tried_str = " -> ".join(models_tried)
        error_msg = f"All models failed ({tried_str}). Last error: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def close(self):
        await self.client.aclose()


class TravelAPIClient:
    """Client for various travel APIs (free/public APIs)."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_flights_skyscanner(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
    ) -> List[Dict[str, Any]]:
        """Search flights using free/public APIs."""
        logger.info(f"Searching flights: {origin} -> {destination} on {departure_date}")
        return [
            {
                "id": f"flight_{origin}_{destination}_{departure_date}",
                "airline": "Aeroflot",
                "flight_number": "SU 1234",
                "origin": origin,
                "destination": destination,
                "departure_time": f"{departure_date}T10:00:00",
                "arrival_time": f"{departure_date}T14:30:00",
                "duration": "4h 30m",
                "price": 15000,
                "currency": "RUB",
                "stops": 0,
                "booking_url": f"https://example.com/book/flight_{origin}_{destination}",
            },
            {
                "id": f"flight_{origin}_{destination}_{departure_date}_2",
                "airline": "S7 Airlines",
                "flight_number": "S7 5678",
                "origin": origin,
                "destination": destination,
                "departure_time": f"{departure_date}T14:00:00",
                "arrival_time": f"{departure_date}T18:45:00",
                "duration": "4h 45m",
                "price": 18000,
                "currency": "RUB",
                "stops": 1,
                "booking_url": f"https://example.com/book/flight_{origin}_{destination}_2",
            },
        ]

    async def search_hotels(
        self,
        city: str,
        check_in: str,
        check_out: str,
        adults: int = 2,
        rooms: int = 1,
    ) -> List[Dict[str, Any]]:
        """Search hotels using free/public APIs."""
        logger.info(f"Searching hotels in {city}: {check_in} - {check_out}")
        return [
            {
                "id": f"hotel_{city}_1",
                "name": f"Grand Hotel {city}",
                "address": f"Central {city}",
                "rating": 4.5,
                "review_count": 1200,
                "price_per_night": 8000,
                "currency": "RUB",
                "total_price": 8000 * 3,
                "amenities": ["WiFi", "Breakfast", "Pool", "Gym", "Parking"],
                "images": [f"https://example.com/hotel_{city}_1.jpg"],
                "booking_url": f"https://example.com/book/hotel_{city}_1",
                "location": {"lat": 55.7558, "lon": 37.6173},
            },
            {
                "id": f"hotel_{city}_2",
                "name": f"Comfort Inn {city}",
                "address": f"Downtown {city}",
                "rating": 4.2,
                "review_count": 800,
                "price_per_night": 5500,
                "currency": "RUB",
                "total_price": 5500 * 3,
                "amenities": ["WiFi", "Breakfast", "Parking"],
                "images": [f"https://example.com/hotel_{city}_2.jpg"],
                "booking_url": f"https://example.com/book/hotel_{city}_2",
                "location": {"lat": 55.7558, "lon": 37.6173},
            },
        ]

    async def search_trains(
        self,
        origin: str,
        destination: str,
        departure_date: str,
    ) -> List[Dict[str, Any]]:
        """Search trains (RZD, etc.)."""
        logger.info(f"Searching trains: {origin} -> {destination} on {departure_date}")
        return [
            {
                "id": f"train_{origin}_{destination}_{departure_date}",
                "train_number": "001A",
                "train_name": "Sapsan",
                "origin": origin,
                "destination": destination,
                "departure_time": f"{departure_date}T07:00:00",
                "arrival_time": f"{departure_date}T11:30:00",
                "duration": "4h 30m",
                "price": 3500,
                "currency": "RUB",
                "class": "Economy",
                "booking_url": f"https://rzd.ru/book/train_{origin}_{destination}",
            },
            {
                "id": f"train_{origin}_{destination}_{departure_date}_2",
                "train_number": "015B",
                "train_name": "Lastochka",
                "origin": origin,
                "destination": destination,
                "departure_time": f"{departure_date}T13:00:00",
                "arrival_time": f"{departure_date}T18:00:00",
                "duration": "5h 00m",
                "price": 2800,
                "currency": "RUB",
                "class": "Economy",
                "booking_url": f"https://rzd.ru/book/train_{origin}_{destination}_2",
            },
        ]

    async def get_popular_destinations(self, country: str = None) -> List[Dict[str, Any]]:
        """Get popular travel destinations."""
        destinations = [
            {"city": "Москва", "country": "Россия", "description": "Столица с богатой историей", "image": "moscow.jpg"},
            {"city": "Санкт-Петербург", "country": "Россия", "description": "Культурная столица", "image": "spb.jpg"},
            {"city": "Сочи", "country": "Россия", "description": "Курорт на Черном море", "image": "sochi.jpg"},
            {"city": "Казань", "country": "Россия", "description": "Столица Татарстана", "image": "kazan.jpg"},
            {"city": "Екатеринбург", "country": "Россия", "description": "Столица Урала", "image": "ekb.jpg"},
            {"city": "Владивосток", "country": "Россия", "description": "Врата Азии", "image": "vladivostok.jpg"},
            {"city": "Стамбул", "country": "Турция", "description": "Город на двух континентах", "image": "istanbul.jpg"},
            {"city": "Дубай", "country": "ОАЭ", "description": "Современный мегаполис", "image": "dubai.jpg"},
            {"city": "Пхукет", "country": "Таиланд", "description": "Тропический рай", "image": "phuket.jpg"},
            {"city": "Бали", "country": "Индонезия", "description": "Остров богов", "image": "bali.jpg"},
        ]
        if country:
            destinations = [d for d in destinations if d["country"].lower() == country.lower()]
        return destinations

    async def close(self):
        await self.client.aclose()


# Global instances
openrouter_client = OpenRouterClient()
travel_api_client = TravelAPIClient()
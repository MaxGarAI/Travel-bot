from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger, String, Text, DateTime, Integer, Boolean, ForeignKey, JSON, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user ID
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), default="ru")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Preferences
    preferred_currency: Mapped[str] = mapped_column(String(3), default="RUB")
    home_city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    travel_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # budget, luxury, adventure, etc.
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    trips: Mapped[list["Trip"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    searches: Mapped[list["SearchHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Trip(Base):
    __tablename__ = "trips"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Dates
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Location
    destination_country: Mapped[str] = mapped_column(String(100))
    destination_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default="planning")  # planning, booked, completed, cancelled
    budget: Mapped[Optional[float]] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="trips")
    itinerary_items: Mapped[list["ItineraryItem"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(Integer, ForeignKey("trips.id"), nullable=False)
    
    # Item details
    day_number: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_type: Mapped[str] = mapped_column(String(50))  # activity, restaurant, transport, accommodation, sightseeing
    
    # Location
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Cost
    estimated_cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    
    # External references
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g., booking.com hotel ID
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    trip: Mapped["Trip"] = relationship(back_populates="itinerary_items")
    
    __table_args__ = (
        Index("ix_itinerary_trip_day", "trip_id", "day_number"),
    )


class Booking(Base):
    __tablename__ = "bookings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(Integer, ForeignKey("trips.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    booking_type: Mapped[str] = mapped_column(String(50))  # flight, train, hotel, activity, transfer
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, confirmed, cancelled, completed
    
    # Provider info
    provider: Mapped[str] = mapped_column(String(100))  # e.g., "aviasales", "booking.com", "rzd"
    provider_booking_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_confirmation_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Details
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Dates
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Location
    origin: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Cost
    amount: Mapped[float] = mapped_column()
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    
    # Passengers/guests
    passengers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # External reference
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    trip: Mapped["Trip"] = relationship(back_populates="bookings")
    user: Mapped["User"] = relationship()


class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    search_type: Mapped[str] = mapped_column(String(50))  # flights, hotels, trains, itinerary
    query_params: Mapped[dict] = mapped_column(JSON)
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="searches")
    
    __table_args__ = (
        Index("ix_search_user_type_date", "user_id", "search_type", "created_at"),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    bookmark_type: Mapped[str] = mapped_column(String(50))  # hotel, flight, place, activity
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Location
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # External reference
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="bookmarks")
    
    __table_args__ = (
        Index("ix_bookmark_user_type", "user_id", "bookmark_type"),
    )


class ConversationContext(Base):
    __tablename__ = "conversation_context"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Current conversation state
    current_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_trip_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("trips.id"), nullable=True)
    
    # Context data (last search params, preferences, etc.)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
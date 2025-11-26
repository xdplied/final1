"""
Database Models - SQLAlchemy ORM
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Time, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email_hash = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'client' or 'provider'
    phone_hash = Column(String)
    anonymous_id = Column(String, unique=True, nullable=False)
    vaccination_status = Column(String)
    health_status = Column(String, default="healthy")
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    
    # Relationships
    services = relationship("Service", back_populates="provider", foreign_keys="Service.provider_id")
    client_bookings = relationship("Booking", back_populates="client", foreign_keys="Booking.client_id")
    provider_bookings = relationship("Booking", back_populates="provider", foreign_keys="Booking.provider_id")
    health_declarations = relationship("HealthDeclaration", back_populates="user")
    privacy_logs = relationship("PrivacyLog", back_populates="user")

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    location_area = Column(String)
    covid_safe = Column(Boolean, default=True)
    max_distance = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    provider = relationship("User", back_populates="services", foreign_keys=[provider_id])
    bookings = relationship("Booking", back_populates="service")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booking_date = Column(Date, nullable=False)
    booking_time = Column(String, nullable=False)
    status = Column(String, default="pending")
    location_hash = Column(String, nullable=False)
    contact_trace_token = Column(String, unique=True, nullable=False)
    privacy_level = Column(String, default="standard")
    otp_code = Column(String)
    otp_verified = Column(Boolean, default=False)
    otp_generated_at = Column(DateTime)
    payment_status = Column(String, default="pending")
    amount = Column(Float)
    platform_fee = Column(Float)
    provider_amount = Column(Float)
    card_last4 = Column(String)
    card_type = Column(String)
    payment_reference = Column(String)
    paid_at = Column(DateTime)
    transferred_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    
    # Relationships
    service = relationship("Service", back_populates="bookings")
    client = relationship("User", back_populates="client_bookings", foreign_keys=[client_id])
    provider = relationship("User", back_populates="provider_bookings", foreign_keys=[provider_id])
    transactions = relationship("PaymentTransaction", back_populates="booking")
    reviews = relationship("Review", back_populates="booking")

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    transaction_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    payment_reference = Column(String)
    status = Column(String, default="pending")
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    
    # Relationships
    booking = relationship("Booking", back_populates="transactions")

class ContactEvent(Base):
    __tablename__ = "contact_events"
    
    id = Column(Integer, primary_key=True, index=True)
    anonymous_id_1 = Column(String, nullable=False)
    anonymous_id_2 = Column(String, nullable=False)
    encounter_token = Column(String, unique=True, nullable=False)
    encounter_date = Column(Date, nullable=False)
    duration_minutes = Column(Integer, default=30)
    proximity_level = Column(String, default="close")
    location_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class HealthDeclaration(Base):
    __tablename__ = "health_declarations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    declaration_date = Column(Date, nullable=False)
    symptoms = Column(String)
    temperature = Column(Float)
    covid_test_result = Column(String)
    declaration_hash = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="health_declarations")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    reviewer_anonymous_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    is_anonymous = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    booking = relationship("Booking", back_populates="reviews")

class PrivacyLog(Base):
    __tablename__ = "privacy_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    resource = Column(String)
    ip_hash = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="privacy_logs")

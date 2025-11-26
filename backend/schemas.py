"""
Pydantic Schemas for Request/Response validation
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

# ============================================================================
# USER SCHEMAS
# ============================================================================

class UserBase(BaseModel):
    username: str
    role: str
    
class UserCreate(UserBase):
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    vaccination_status: Optional[str] = None

class UserResponse(UserBase):
    id: int
    anonymous_id: str
    health_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# ============================================================================
# SERVICE SCHEMAS
# ============================================================================

class ServiceBase(BaseModel):
    service_type: str
    title: str
    description: str
    price: float
    location_area: str
    covid_safe: bool = True
    max_distance: int = 10

class ServiceCreate(ServiceBase):
    pass

class ServiceResponse(ServiceBase):
    id: int
    provider_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# BOOKING SCHEMAS
# ============================================================================

class BookingBase(BaseModel):
    service_id: int
    booking_date: date
    booking_time: str
    location: str
    privacy_level: str = "standard"

class BookingCreate(BookingBase):
    card_number: str
    card_name: str
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    service_id: int
    client_id: int
    provider_id: int
    booking_date: date
    booking_time: str
    status: str
    otp_code: Optional[str] = None
    otp_verified: bool
    payment_status: str
    amount: Optional[float] = None
    platform_fee: Optional[float] = None
    provider_amount: Optional[float] = None
    card_last4: Optional[str] = None
    card_type: Optional[str] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class OTPVerify(BaseModel):
    otp_code: str

# ============================================================================
# HEALTH DECLARATION SCHEMAS
# ============================================================================

class HealthDeclarationBase(BaseModel):
    declaration_date: date
    symptoms: Optional[str] = None
    temperature: Optional[float] = None
    covid_test_result: str

class HealthDeclarationCreate(HealthDeclarationBase):
    pass

# ============================================================================
# PAYMENT TRANSACTION SCHEMAS
# ============================================================================

class PaymentTransactionResponse(BaseModel):
    id: int
    booking_id: int
    transaction_type: str
    amount: float
    payment_reference: Optional[str] = None
    status: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

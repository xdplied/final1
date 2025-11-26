"""
COVID-Safe Home Services - FastAPI Backend
Main application file
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import secrets
import hashlib

from database import engine, SessionLocal, Base
import models
import schemas
from auth import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    get_current_user,
    SECRET_KEY,
    ALGORITHM
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="COVID-Safe Home Services API",
    description="Privacy-by-design home services platform with contact tracing",
    version="3.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def hash_data(data: str) -> str:
    """Hash sensitive data using SHA-256"""
    return hashlib.sha256(data.encode()).hexdigest()

def generate_anonymous_id() -> str:
    """Generate unique anonymous ID"""
    return f"ANON-{secrets.token_hex(16)}"

def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return str(secrets.randbelow(900000) + 100000)

def generate_payment_reference() -> str:
    """Generate payment reference"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = secrets.token_hex(4).upper()
    return f"PAY-{timestamp}-{random_part}"

def calculate_payment_amounts(price: float):
    """Calculate payment breakdown with 5% platform fee"""
    platform_fee = round(price * 0.05, 2)
    provider_amount = round(price - platform_fee, 2)
    return {
        'total': price,
        'platform_fee': platform_fee,
        'provider_amount': provider_amount
    }

def get_card_type(card_number: str) -> str:
    """Determine card type from number"""
    if card_number.startswith('4'):
        return 'Visa'
    elif card_number.startswith('5'):
        return 'Mastercard'
    elif card_number.startswith('3'):
        return 'American Express'
    return 'Unknown'

def log_privacy_action(db: Session, user_id: int, action: str, resource: str = None):
    """Log privacy-related actions"""
    log = models.PrivacyLog(
        user_id=user_id,
        action=action,
        resource=resource,
        ip_hash=hash_data("127.0.0.1"),  # In production, get real IP
        timestamp=datetime.now()
    )
    db.add(log)
    db.commit()

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username exists
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    email_hash = hash_data(user.email) if user.email else None
    phone_hash = hash_data(user.phone) if user.phone else None
    
    db_user = models.User(
        username=user.username,
        email_hash=email_hash,
        password_hash=hashed_password,
        role=user.role,
        phone_hash=phone_hash,
        anonymous_id=generate_anonymous_id(),
        vaccination_status=user.vaccination_status,
        health_status="healthy"
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    log_privacy_action(db, db_user.id, "USER_REGISTERED")
    
    return db_user

@app.post("/api/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.now()
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    log_privacy_action(db, user.id, "USER_LOGIN")
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

# ============================================================================
# SERVICE ENDPOINTS
# ============================================================================

@app.get("/api/services", response_model=List[schemas.ServiceResponse])
def get_services(
    service_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all services with optional filtering"""
    query = db.query(models.Service)
    
    if service_type:
        query = query.filter(models.Service.service_type == service_type)
    
    services = query.offset(skip).limit(limit).all()
    return services

@app.get("/api/services/{service_id}", response_model=schemas.ServiceResponse)
def get_service(service_id: int, db: Session = Depends(get_db)):
    """Get specific service by ID"""
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@app.post("/api/services", response_model=schemas.ServiceResponse)
def create_service(
    service: schemas.ServiceCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new service (providers only)"""
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can create services")
    
    db_service = models.Service(
        provider_id=current_user.id,
        service_type=service.service_type,
        title=service.title,
        description=service.description,
        price=service.price,
        location_area=service.location_area,
        covid_safe=service.covid_safe,
        max_distance=service.max_distance
    )
    
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    log_privacy_action(db, current_user.id, "SERVICE_CREATED")
    
    return db_service

@app.put("/api/services/{service_id}", response_model=schemas.ServiceResponse)
def update_service(
    service_id: int,
    service: schemas.ServiceCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a service"""
    db_service = db.query(models.Service).filter(models.Service.id == service_id).first()
    
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if db_service.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_service.service_type = service.service_type
    db_service.title = service.title
    db_service.description = service.description
    db_service.price = service.price
    db_service.location_area = service.location_area
    db_service.covid_safe = service.covid_safe
    db_service.max_distance = service.max_distance
    
    db.commit()
    db.refresh(db_service)
    
    return db_service

@app.delete("/api/services/{service_id}")
def delete_service(
    service_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a service"""
    db_service = db.query(models.Service).filter(models.Service.id == service_id).first()
    
    if not db_service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if db_service.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(db_service)
    db.commit()
    
    return {"message": "Service deleted successfully"}

# ============================================================================
# BOOKING ENDPOINTS
# ============================================================================

@app.post("/api/bookings", response_model=schemas.BookingResponse)
def create_booking(
    booking: schemas.BookingCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new booking with payment"""
    # Get service
    service = db.query(models.Service).filter(models.Service.id == booking.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Calculate payment
    payment_details = calculate_payment_amounts(service.price)
    
    # Get card info
    card_last4 = booking.card_number[-4:]
    card_type = get_card_type(booking.card_number)
    
    # Generate OTP and payment reference
    otp_code = generate_otp()
    payment_reference = generate_payment_reference()
    
    # Create booking
    db_booking = models.Booking(
        service_id=service.id,
        client_id=current_user.id,
        provider_id=service.provider_id,
        booking_date=booking.booking_date,
        booking_time=booking.booking_time,
        location_hash=hash_data(booking.location),
        contact_trace_token=secrets.token_hex(16),
        privacy_level=booking.privacy_level,
        otp_code=otp_code,
        otp_generated_at=datetime.now(),
        payment_status="paid_held",
        amount=payment_details['total'],
        platform_fee=payment_details['platform_fee'],
        provider_amount=payment_details['provider_amount'],
        card_last4=card_last4,
        card_type=card_type,
        payment_reference=payment_reference,
        paid_at=datetime.now()
    )
    
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    # Create contact event
    provider = db.query(models.User).filter(models.User.id == service.provider_id).first()
    contact_event = models.ContactEvent(
        anonymous_id_1=current_user.anonymous_id,
        anonymous_id_2=provider.anonymous_id,
        encounter_token=db_booking.contact_trace_token,
        encounter_date=booking.booking_date,
        location_hash=db_booking.location_hash,
        proximity_level="close"
    )
    db.add(contact_event)
    
    # Log payment transaction
    transaction = models.PaymentTransaction(
        booking_id=db_booking.id,
        transaction_type="payment_held",
        amount=payment_details['total'],
        payment_reference=payment_reference,
        status="held",
        description=f"Payment of ${payment_details['total']:.2f} held in escrow",
        completed_at=datetime.now()
    )
    db.add(transaction)
    
    db.commit()
    
    log_privacy_action(db, current_user.id, "BOOKING_CREATED", f"booking_{db_booking.id}")
    
    return db_booking

@app.get("/api/bookings", response_model=List[schemas.BookingResponse])
def get_bookings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bookings for current user"""
    if current_user.role == "client":
        bookings = db.query(models.Booking).filter(
            models.Booking.client_id == current_user.id
        ).all()
    else:  # provider
        bookings = db.query(models.Booking).filter(
            models.Booking.provider_id == current_user.id
        ).all()
    
    return bookings

@app.get("/api/bookings/{booking_id}", response_model=schemas.BookingResponse)
def get_booking(
    booking_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific booking"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.client_id != current_user.id and booking.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return booking

@app.post("/api/bookings/{booking_id}/verify-otp")
def verify_otp(
    booking_id: int,
    otp_data: schemas.OTPVerify,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify OTP code"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only provider can verify OTP")
    
    if booking.otp_code != otp_data.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    
    booking.otp_verified = True
    booking.status = "confirmed"
    db.commit()
    
    log_privacy_action(db, current_user.id, "OTP_VERIFIED", f"booking_{booking_id}")
    
    return {"message": "OTP verified successfully"}

@app.post("/api/bookings/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete booking and transfer payment"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only provider can complete booking")
    
    booking.status = "completed"
    booking.completed_at = datetime.now()
    
    # Transfer payment
    if booking.payment_status == "paid_held":
        booking.payment_status = "transferred"
        booking.transferred_at = datetime.now()
        
        # Log transfer transaction
        transaction = models.PaymentTransaction(
            booking_id=booking.id,
            transaction_type="transfer_to_provider",
            amount=booking.provider_amount,
            payment_reference=f"TRANSFER-{booking.id}",
            status="completed",
            description=f"${booking.provider_amount:.2f} transferred to provider (Platform fee: ${booking.platform_fee:.2f})",
            completed_at=datetime.now()
        )
        db.add(transaction)
        
        log_privacy_action(db, current_user.id, "PAYMENT_TRANSFERRED", f"booking_{booking_id}")
    
    db.commit()
    
    return {
        "message": "Booking completed",
        "payment_transferred": booking.provider_amount,
        "platform_fee": booking.platform_fee
    }

# ============================================================================
# HEALTH DECLARATION ENDPOINTS
# ============================================================================

@app.post("/api/health-declarations")
def create_health_declaration(
    declaration: schemas.HealthDeclarationCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit health declaration"""
    db_declaration = models.HealthDeclaration(
        user_id=current_user.id,
        declaration_date=declaration.declaration_date,
        symptoms=declaration.symptoms,
        temperature=declaration.temperature,
        covid_test_result=declaration.covid_test_result,
        declaration_hash=secrets.token_hex(16)
    )
    
    db.add(db_declaration)
    db.commit()
    
    # If positive, trigger contact tracing
    if declaration.covid_test_result == "positive":
        contacts = db.query(models.ContactEvent).filter(
            (models.ContactEvent.anonymous_id_1 == current_user.anonymous_id) |
            (models.ContactEvent.anonymous_id_2 == current_user.anonymous_id)
        ).all()
        
        # Update user health status
        current_user.health_status = "positive"
        db.commit()
        
        log_privacy_action(db, current_user.id, "COVID_POSITIVE_REPORTED")
    
    return {"message": "Health declaration submitted", "contacts_traced": len(contacts) if declaration.covid_test_result == "positive" else 0}

# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@app.get("/api/stats/dashboard")
def get_dashboard_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    if current_user.role == "client":
        total_bookings = db.query(models.Booking).filter(
            models.Booking.client_id == current_user.id
        ).count()
        
        pending_bookings = db.query(models.Booking).filter(
            models.Booking.client_id == current_user.id,
            models.Booking.status.in_(["pending", "confirmed"])
        ).count()
        
        return {
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "role": "client"
        }
    else:  # provider
        total_services = db.query(models.Service).filter(
            models.Service.provider_id == current_user.id
        ).count()
        
        total_bookings = db.query(models.Booking).filter(
            models.Booking.provider_id == current_user.id
        ).count()
        
        completed_bookings = db.query(models.Booking).filter(
            models.Booking.provider_id == current_user.id,
            models.Booking.status == "completed"
        ).count()
        
        total_earnings = db.query(models.Booking).filter(
            models.Booking.provider_id == current_user.id,
            models.Booking.payment_status == "transferred"
        ).with_entities(models.Booking.provider_amount).all()
        
        earnings_sum = sum([e[0] for e in total_earnings if e[0]])
        
        return {
            "total_services": total_services,
            "total_bookings": total_bookings,
            "completed_bookings": completed_bookings,
            "total_earnings": earnings_sum,
            "role": "provider"
        }

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/")
def root():
    """API health check"""
    return {
        "message": "COVID-Safe Home Services API",
        "version": "3.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

try:
    from .database import SessionLocal
    from .models import Order, OrderItem, Product, User
except ImportError:
    from database import SessionLocal
    from models import Order, OrderItem, Product, User

router = APIRouter(prefix="/api")
TOKEN_SECRET = os.getenv("SESSION_SECRET", "change-this-session-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: str
    phone: str = Field(min_length=7, max_length=30)
    address: str = Field(min_length=8, max_length=500)
    password: str = Field(min_length=8, max_length=128)

class VerifyIn(BaseModel):
    email: str
    code: str = Field(min_length=4, max_length=20)

class LoginIn(BaseModel):
    email: str
    password: str

class CartLineIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=20)

class OrderIn(BaseModel):
    items: list[CartLineIn]
    shipping_name: str = Field(min_length=2, max_length=160)
    shipping_phone: str = Field(min_length=7, max_length=30)
    shipping_address: str = Field(min_length=8, max_length=500)

class PaymentIn(BaseModel):
    payment_method: str
    payment_reference: str = Field(min_length=4, max_length=120)

class StatusIn(BaseModel):
    status: str


def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 160_000)
    return base64.urlsafe_b64encode(salt + digest).decode()


def check_password(password: str, encoded: str) -> bool:
    raw = base64.urlsafe_b64decode(encoded.encode())
    salt, expected = raw[:16], raw[16:]
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 160_000)
    return hmac.compare_digest(actual, expected)


def make_token(subject: str, role: str = "customer") -> str:
    payload = {"sub": subject, "role": role, "exp": int(datetime.now(timezone.utc).timestamp()) + 60 * 60 * 24}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def read_token(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    try:
        encoded, signature = authorization[7:].split(".", 1)
        expected = hmac.new(TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if not hmac.compare_digest(signature, expected) or payload["exp"] < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError
        return payload
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(401, "Invalid or expired session")


def current_user(authorization: Optional[str] = Header(default=None), session: Session = Depends(db)):
    payload = read_token(authorization)
    if payload["role"] == "admin":
        return payload
    user = session.get(User, int(payload["sub"]))
    if not user or not user.is_verified:
        raise HTTPException(403, "Verified customer account required")
    return user


def admin_user(authorization: Optional[str] = Header(default=None)):
    payload = read_token(authorization)
    if payload["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return payload


def order_json(order: Order, session: Session) -> dict:
    items = session.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    return {
        "id": order.id, "status": order.status, "payment_status": order.payment_status,
        "payment_method": order.payment_method, "total": order.total,
        "shipping_name": order.shipping_name, "shipping_phone": order.shipping_phone,
        "shipping_address": order.shipping_address, "created_at": order.created_at.isoformat(),
        "items": [{"name": item.product_name, "quantity": item.quantity, "unit_price": item.unit_price} for item in items],
    }


@router.post("/auth/register")
def register(body: RegisterIn, session: Session = Depends(db)):
    email = body.email.strip().lower()
    if session.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    code = str(secrets.randbelow(900000) + 100000)
    user = User(full_name=body.full_name.strip(), email=email, phone=body.phone.strip(), address=body.address.strip(), password_hash=hash_password(body.password), verification_code=code)
    session.add(user)
    session.commit()
    return {"message": "Account created. Verify your account to continue.", "verification_code": code}


@router.post("/auth/verify")
def verify(body: VerifyIn, session: Session = Depends(db)):
    user = session.query(User).filter(User.email == body.email.strip().lower()).first()
    if not user or not hmac.compare_digest(user.verification_code, body.code.strip()):
        raise HTTPException(400, "Invalid verification code")
    user.is_verified = True
    user.verification_code = "verified"
    session.commit()
    return {"message": "Account verified. You can now log in."}


@router.post("/auth/login")
def login(body: LoginIn, session: Session = Depends(db)):
    identity = body.email.strip().lower()
    if identity == ADMIN_USERNAME.lower() and hmac.compare_digest(body.password, ADMIN_PASSWORD):
        return {"token": make_token(ADMIN_USERNAME, "admin"), "role": "admin", "name": "Store admin"}
    user = session.query(User).filter(User.email == identity).first()
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_verified:
        raise HTTPException(403, "Verify your account before logging in")
    return {"token": make_token(str(user.id)), "role": "customer", "name": user.full_name}


@router.get("/auth/me")
def me(user=Depends(current_user), session: Session = Depends(db)):
    if isinstance(user, dict):
        return {"role": "admin", "name": "Store admin"}
    return {"role": "customer", "name": user.full_name, "email": user.email, "phone": user.phone, "address": user.address}


@router.post("/orders")
def create_order(body: OrderIn, user=Depends(current_user), session: Session = Depends(db)):
    if isinstance(user, dict):
        raise HTTPException(403, "Customer login required to place an order")
    if not body.items:
        raise HTTPException(400, "Your cart is empty")
    total = 0.0
    line_items = []
    for line in body.items:
        product = session.get(Product, line.product_id)
        if not product or product.stock < line.quantity:
            raise HTTPException(400, "A selected product is unavailable in the requested quantity")
        total += product.price * line.quantity
        line_items.append((product, line.quantity))
    order = Order(user_id=user.id, total=total, shipping_name=body.shipping_name.strip(), shipping_phone=body.shipping_phone.strip(), shipping_address=body.shipping_address.strip())
    session.add(order)
    session.flush()
    for product, quantity in line_items:
        product.stock -= quantity
        session.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name, quantity=quantity, unit_price=product.price))
    session.commit()
    return order_json(order, session)


@router.post("/orders/{order_id}/pay")
def pay_order(order_id: int, body: PaymentIn, user=Depends(current_user), session: Session = Depends(db)):
    order = session.get(Order, order_id)
    if not order or (not isinstance(user, dict) and order.user_id != user.id):
        raise HTTPException(404, "Order not found")
    method = body.payment_method.lower()
    if method not in {"card", "upi"}:
        raise HTTPException(400, "Only card and UPI online payments are supported")
    if order.payment_status == "paid":
        return order_json(order, session)
    order.payment_method = method
    order.payment_reference = body.payment_reference.strip()
    order.payment_status = "paid"
    order.status = "confirmed"
    session.commit()
    return order_json(order, session)


@router.get("/orders")
def my_orders(user=Depends(current_user), session: Session = Depends(db)):
    if isinstance(user, dict):
        return [order_json(order, session) for order in session.query(Order).order_by(Order.created_at.desc()).all()]
    return [order_json(order, session) for order in session.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()]


@router.patch("/admin/orders/{order_id}")
def update_order(order_id: int, body: StatusIn, user=Depends(admin_user), session: Session = Depends(db)):
    allowed = {"confirmed", "processing", "shipped", "delivered", "cancelled"}
    if body.status not in allowed:
        raise HTTPException(400, "Unsupported order status")
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    order.status = body.status
    session.commit()
    return order_json(order, session)

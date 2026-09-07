from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float, Boolean
from datetime import datetime
from .database import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    festival = Column(String(120), default="All Auspicious Occasions")
    stock = Column(Integer, default=0)
    featured = Column(Boolean, default=True)

class ProductItem(Base):
    __tablename__ = "product_items"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False, index=True)
    item_no = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    bengali = Column(String(200))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(160), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=False)
    address = Column(Text, nullable=False)
    password_hash = Column(String(300), nullable=False)
    verification_code = Column(String(20), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(40), default="pending_payment", nullable=False)
    payment_status = Column(String(40), default="unpaid", nullable=False)
    payment_method = Column(String(20))
    payment_reference = Column(String(120))
    total = Column(Float, nullable=False)
    shipping_name = Column(String(160), nullable=False)
    shipping_phone = Column(String(30), nullable=False)
    shipping_address = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

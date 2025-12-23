# /app/models.py

"""
The Contract: Define what our data looks like
"""

# app/models.py
from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship

# --- 1. Enums ---
# Enums restrict data to specific values. This prevents "typo" bugs in your data.
class OrderStatus(str, Enum):
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURNED = "returned"

class TicketStatus(str, Enum):
    OPEN = "open"
    PENDING_APPROVAL = "pending_approval" # The HITL trigger state
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"

# --- 2. Database Tables ---

class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True) # Index makes searching by email fast
    is_vip: bool = Field(default=False)
    
    # "Relationship" allows us to do customer.orders later
    orders: List["Order"] = Relationship(back_populates="customer")

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    price: float
    stock_level: int
    category: str

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Foreign Keys link tables together
    customer_id: int = Field(foreign_key="customer.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int
    total_price: float
    status: OrderStatus = Field(default=OrderStatus.PROCESSING)
    order_date: datetime = Field(default_factory=datetime.utcnow)
    
    customer: Customer = Relationship(back_populates="orders")
    
class RefundTicket(SQLModel, table=True):
    """
    This table acts as our 'State Machine' for Human-in-the-Loop.
    When the Agent hits a threshold, it creates a row here instead of refunding money.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    order_id: int = Field(foreign_key="order.id")
    amount: float
    reason: str
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
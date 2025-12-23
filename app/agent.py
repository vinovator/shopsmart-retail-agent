# app/agent.py
"""
The "brain" of our retail agent.
This does 3 things
1. Defines the Context: Tells the agent "Here is the database connection you can use"
2. Defines the Tools: Python functions the agents can use e.g. "Look up Order"
3. Defines the System Prompt: The Personality and Rules (e.g. "Be polite, don't refund > $50")

The "Glue":
- The agent is just a static object, it doesn't have a DB connection
- Our tools (e.g. get_order_status) needs a Database Session to run a SQL query.
- A class (SupportDeps) holds the DB session. that is passed into the agent every time
- This is Dependency Injection (DI)
"""

from datetime import datetime
from pydantic import BaseModel
from sqlmodel import Session, select
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv


# Load the environment variables
load_dotenv()

# Import our models
from app.models import Order, Customer, Product, OrderStatus, RefundTicket, TicketStatus

# For Vector Search
import os
from google import genai
from qdrant_client import QdrantClient

# The Context - Dependency Injection
class SupportDeps(BaseModel):
    """
    This class holds the "Context" that the agent needs to function.
    FastAPI will create this and pass it to the agent every time it is called.
    This is a container. Notice DB is not initialized here. It is passed in runtime
    """
    user_id: int # Who is the agent speaking to?
    db: Session # Database connection

    class Config:
        arbitrary_types_allowed = True # Allow Session to be used as a type


# Agent Definition
agent = Agent(
    "gemini-2.5-flash",
    deps_type=SupportDeps,
    system_prompt=(
        "You are a helpful customer support assistant from 'ShopSmart'. "
        "You have access to the customer's order history and product catalog. "
        "Always be polite and professional. "
        "Use the provided tools to lookup information before answering the customer. "
        "Today's date is" + datetime.now().strftime("%Y-%m-%d")
    )
)


# Tools Definition

@agent.tool
def get_customer_profile(ctx: RunContext[SupportDeps]) -> str:
    """
    Fetch the profile of the CURRENT user talking to the agent
    Returns thier name and VIP status
    """
    
    # 1. Access the database session from the context (ctx.deps)
    session = ctx.deps.db
    user_id = ctx.deps.user_id

    # 2. Query the database for the user
    customer = session.get(Customer, user_id)

    if not customer:
        return "Error: Customer not found"

    return f"Customer Name: {customer.name}, VIP Status: {customer.is_vip}, Email: {customer.email}"


@agent.tool
def list_recent_orders(ctx: RunContext[SupportDeps]) -> str:
    """
    Get a list of the customer's most recent orders.
    Use this when the user asks "Where is my stuff?" or "Show my history"
    """
    session = ctx.deps.db
    user_id = ctx.deps.user_id

    # Select orders for THIS customer
    statement = select(Order).where(Order.customer_id == user_id).order_by(Order.order_date.desc()).limit(5)
    orders = session.exec(statement).all()

    if not orders:
        return "No recent orders found"

    # Format the output for the LLM (It reads text better than raw JSON sometimes)
    report = []
    for order in orders:
        report.append(f"Order ID: {order.id}, Date: {order.order_date}, Total: {order.total_price}, Status: {order.status}")
    
    return "\n".join(report)


@agent.tool
def get_order_details(ctx: RunContext[SupportDeps], order_id: int) -> str:
    """
    Get the details of a specific order.
    Use this when the user asks "What's the status of my order?"
    """
    session = ctx.deps.db

    # Security Check: We must ensure the order belongs to the current user
    # This prevents User A from looking up User B's orders
    order = session.get(Order, order_id)

    if not order:
        return "Error: Order not found"

    if order.customer_id != ctx.deps.user_id:
        return "Security Alert: You do not have access to this order"

    return f"Order {order.id} details: Status: {order.status}, Items Qty: {order.quantity}, Total: {order.total_price}, Order Date: {order.order_date}"



@agent.tool
def check_refund_status(ctx: RunContext[SupportDeps], order_id: int | None = None) -> str:
    """
    Check the status of refund requests.
    - If order_id is provided, checks that specific order.
    - If no order_id is provided, lists ALL pending refunds for the user.
    """
    session = ctx.deps.db
    user_id = ctx.deps.user_id
    
    query = select(RefundTicket).where(RefundTicket.customer_id == user_id)
    
    # If the user specified an order, filter by it
    if order_id:
        query = query.where(RefundTicket.order_id == order_id)
        
    tickets = session.exec(query).all()
    
    if not tickets:
        return "No active refund tickets found."
    
    report = []
    for t in tickets:
        report.append(f"Ticket #{t.id} for Order {t.order_id}: Status = {t.status.value}")
        
    return "\n".join(report)


# All above tools are GET operations
# Now let's define some tools that can modify the database 

@agent.tool
def request_refund(
    ctx: RunContext[SupportDeps], 
    order_id: int,
    reason: str) -> str:
    """
    Submit a refund requst for an order
    - if the amount is < $50, automatically approve the refund
    - if the amount is > $50, it requires admin approval
    """
    session = ctx.deps.db
    user_id = ctx.deps.user_id

    # 1. Validate Order
    order = session.get(Order, order_id)

    if not order:
        return "Error: Order not found"

    if order.customer_id != user_id:
        return "Security Alert: You do not have access to this order"

    if order.status == OrderStatus.RETURNED:
        return "Order is already returned"


    # 2. Business Logic: Threshold check

    # Scenario A: Auto-Approve (Low Risk)
    if order.total_price < 50:
        order.status = OrderStatus.RETURNED
        session.add(order)
        session.commit()
        return f"Refund of ${order.total_price} for order {order.id} has been processed immediately."
        
    # Scenario B: Human-in-the-Loop (High Risk)
    else:
        # Create a ticket instead of refunding
        ticket = RefundTicket(
            customer_id=user_id,
            order_id=order_id,
            amount=order.total_price,
            reason=reason,
            status=TicketStatus.PENDING_APPROVAL
        )
        session.add(ticket)
        session.commit()
        return (
            f"Request Received: Since the amount ${order.total_price} is greater than $50, "
            f"Refund of ${order.total_price} for order {order.id} has been submitted for approval."
        )



# --- VECTOR DB & AI CLIENT SETUP ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
qdrant_path = os.path.join(base_dir, "qdrant_data")
qdrant = QdrantClient(path=qdrant_path)

# Initialize the new Client
# Note: PydanticAI might handle the Agent chat, but WE handle the embeddings manually here.
ai_client = None
if os.getenv("GOOGLE_API_KEY"):
    ai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@agent.tool
def search_products(ctx: RunContext[SupportDeps], query: str) -> str:
    """
    Search for products based on concepts (Semantic Search).
    Use for: 'recommendations', 'winter clothes', 'gift ideas', or vague descriptions.
    """
    if not ai_client:
        return "Error: AI Client not initialized."

    print(f"🔍 Vector Search Query: {query}")
    
    try:
        # 1. Convert Query to Vector (New SDK)
        response = ai_client.models.embed_content(
            model="text-embedding-004",
            contents=query
        )
        user_vector = response.embeddings[0].values
        
        # 2. Search Qdrant
        hits = qdrant.search(
            collection_name="shop_products",
            query_vector=user_vector,
            limit=3
        )
        
        if not hits:
            return "No relevant products found."
        
        # 3. Format Results
        report = []
        for hit in hits:
            info = hit.payload
            if hit.score > 0.4:
                report.append(f"Product: {info['name']} (${info['price']}) - {info['description']}")
        
        return "\n".join(report) if report else "No relevant matches found."
        
    except Exception as e:
        return f"Search Error: {str(e)}"
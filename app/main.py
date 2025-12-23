# app/main.py

"""
Used by FastAPI to handle the Trffic (API endpoints)
This is the entry point for the API
It receives the JSON request, runs the agent, and sends the responses
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

from app.agent import agent, SupportDeps
from app.dependencies import get_agent_deps
from app.models import RefundTicket, TicketStatus, Order, OrderStatus
from app.utils.db import get_session
from sqlmodel import Session, select

# Tell FastAPI to serve the static folder
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# For Middleware block so browser can access the API
from fastapi.middleware.cors import CORSMiddleware


import uvicorn

app = FastAPI(title="ShopSmart Customer Support Agent")

# --- 2. ADD THIS MIDDLEWARE BLOCK ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (browser, postman, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Mount the STATIC FILES
# This serves style.css, script.js, or images if we had them
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the index.html at root
app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# Define the Request Body
class ChatRequest(BaseModel):
    message: str

# Define the Response Body
class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    deps: SupportDeps = Depends(get_agent_deps)
    ):
    """
    This is the main endpoint for the chat
    1. FastAPI calls get_agent_deps to get the database session and user ID
    2. The context is passed to Agent
    3. The response is returned to the user
    """

    try:
        # we use run() for async/ await support in FastAPI
        result = await agent.run(request.message, deps=deps)

        return ChatResponse(response=result.output)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Admin Request Model
class AdminDecision(BaseModel):
    decision: str # "approve" or "reject"


@app.post("/admin/refunds/{ticket_id}/decision")
def admin_review_refund(
    ticket_id: int,
    body: AdminDecision,
    session: Session = Depends(get_session)
    ):
    """
    Simulates a Manager Dashboard
    A human reviews the ticket and sends "approve" or "reject"
    """
    
    # 1. Get the Ticket
    ticket = session.get(RefundTicket, ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status != TicketStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Ticket is already processed")

    # 2. Process Decision
    if body.decision == "approve":
        # A. Update Ticket
        ticket.status = TicketStatus.APPROVED

        # B. Update the actual order (The "Action")
        order = session.get(Order, ticket.order_id)
        if order:   
            order.status = OrderStatus.RETURNED
            session.add(order)

        session.add(ticket)
        session.commit()

        # --- NEW: Simulate Sending an Email ---
        print(f"📧 [MOCK EMAIL SENT] To User {ticket.customer_id}: 'Your refund for Order {ticket.order_id} is APPROVED.'")

        return {"status": "approved", "message": f"Refund for Order {ticket.order_id} processed"}

    elif body.decision == "reject":
        ticket.status = TicketStatus.REJECTED
        session.add(ticket)
        session.commit()
        return {"status": "rejected", "message": f"Refund request for Order {ticket.order_id} denied"}
    else:
        raise HTTPException(status_code=400, detail="Invalid decision. Use 'approve' or 'reject'")


@app.get("/admin/tickets")
def list_pending_tickets(session: Session = Depends(get_session)):
    """
    Fetch all tickets that are waiting for approvals
    """
    statement = select(RefundTicket).where(RefundTicket.status == TicketStatus.PENDING_APPROVAL)
    tickets = session.exec(statement).all()
    return tickets


if __name__ == "__main__":
    # If running directly, this allows 'python app/main.py' to work
    # BUT standard usage is 'uvicorn app.main:app --reload' from terminal
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
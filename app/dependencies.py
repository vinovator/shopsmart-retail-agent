# app/dependencies.py
"""
Used by FastAPI for dependency injection - Database & Auth
This file is the bridge between FastAPI and our agent
It verfies who the user is and sets up the database session for the request
"""

from fastapi import HTTPException, Header, Depends
from sqlmodel import Session, select
from typing import Annotated

from app.utils.db import get_session
from app.models import Customer
from app.agent import SupportDeps

# 1. Simulate Authentication
# In a real app, this would be a JWT token or something
# For this project, we simply trust the user ID  header
async def get_current_user(
    user_id: Annotated[int | None, Header()] = None,
    session: Session = Depends(get_session) # get_session is defined in utils.db
) -> Customer:
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID is Missing")

    customer = session.get(Customer, user_id)
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid User ID")

    return customer

# 2. Build the Agent Dependencies
# This function builds the USER + DB into the object the agent needs
async def get_agent_deps(
    user: Customer = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> SupportDeps:
    return SupportDeps(user_id=user.id, db=session)

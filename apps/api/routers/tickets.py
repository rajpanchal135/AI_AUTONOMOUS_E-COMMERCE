import uuid
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.database import get_db
from apps.api.models import SupportTicket, Customer
from apps.api.schemas import SupportTicketItem
from apps.api.config import settings
from brain.shared.rag_engine import rag_engine

router = APIRouter(prefix="/tickets", tags=["Support"])


class ChatRequest(BaseModel):
    message: str
    order_id: Optional[str] = None
    customer_email: Optional[str] = None
    language: Optional[str] = "en"


@router.get("", response_model=List[SupportTicketItem])
async def list_tickets(db: AsyncSession = Depends(get_db)):
    query = (
        select(SupportTicket, Customer)
        .outerjoin(Customer, SupportTicket.customer_id == Customer.id)
        .order_by(SupportTicket.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for tck, cust in rows:
        items.append(
            SupportTicketItem(
                ticket_id=tck.id,
                external_id=tck.external_id,
                customer_email=cust.email if cust else "customer@example.com",
                subject=tck.subject,
                message=tck.message,
                status=tck.status,
                priority=tck.priority,
                intent=tck.intent,
                sentiment=tck.sentiment,
                draft_reply=tck.draft_reply,
                confidence=float(tck.confidence or 0.94),
                created_at=tck.created_at
            )
        )
    return items


@router.post("/chat")
async def chat_with_support_agent(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Live AI Support Assistant: Answers customer inquiries using the real RAG Engine
    backed by TF-IDF Vector Knowledge Base, live SQLite order retrieval,
    and Google Gemini 3.6 Flash in-context generation.
    """
    # ── 1. EXECUTE RAG RETRIEVAL & GENERATION ────────────────────────────────
    rag_res = await rag_engine.answer(
        query=payload.message,
        db=db,
        order_id_hint=payload.order_id,
        customer_email=payload.customer_email,
        language=payload.language or "en"
    )

    ticket_ext_id = f"TCK-{uuid.uuid4().hex[:6].upper()}"

    # ── 2. PERSIST SUPPORT TICKET TO SQLITE ───────────────────────────────────
    subject = f"Inquiry on Order #{rag_res.order_id}" if rag_res.order_found else f"Customer Support: {rag_res.intent.replace('_', ' ').title()}"
    new_ticket = SupportTicket(
        id=str(uuid.uuid4()),
        tenant_id=settings.DEFAULT_TENANT_ID,
        external_id=ticket_ext_id,
        subject=subject,
        message=payload.message,
        status="open",
        priority="high" if rag_res.sentiment == "negative" else "medium",
        intent=rag_res.intent,
        sentiment=rag_res.sentiment,
        draft_reply=rag_res.answer,
        confidence=rag_res.confidence,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_ticket)
    await db.commit()

    return {
        "ticket_id": new_ticket.id,
        "external_id": new_ticket.external_id,
        "reply": rag_res.answer,
        "intent": rag_res.intent,
        "sentiment": rag_res.sentiment,
        "confidence": rag_res.confidence,
        "order_found": rag_res.order_found,
        "order_external_id": rag_res.order_id,
        "carrier_tracking": rag_res.tracking_number,
        "carrier_name": rag_res.carrier,
        "model_id": rag_res.model_id,
        "evidence": [
            {
                "chunk_id": ev.chunk_id,
                "source_type": ev.source_type,
                "title": ev.title,
                "content": ev.content,
                "relevance_score": ev.relevance_score,
                "metadata": ev.metadata
            }
            for ev in rag_res.evidence
        ]
    }

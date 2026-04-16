"""Export conversation as PDF."""

import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.conversation_state import ConversationState

router = APIRouter()


@router.get("/conversations/{conversation_id}/export-pdf")
async def export_conversation_pdf(conversation_id: str, db: AsyncSession = Depends(get_db)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import mm

    result = await db.execute(
        select(ConversationState).where(ConversationState.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=HexColor("#6b7280"), spaceAfter=12)
    user_style = ParagraphStyle("User", parent=styles["Normal"], fontSize=10, backColor=HexColor("#f3f4f6"), borderPadding=6, spaceAfter=6, leftIndent=0)
    ai_style = ParagraphStyle("AI", parent=styles["Normal"], fontSize=10, backColor=HexColor("#eff6ff"), borderPadding=6, spaceAfter=6, leftIndent=0)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=8, textColor=HexColor("#6b7280"), spaceAfter=2)

    elements = []
    elements.append(Paragraph("Conversation Export", title_style))
    elements.append(Paragraph(
        f"Channel: {conv.channel} | Score: {conv.intent_score} | Stage: {conv.stage} | "
        f"Messages: {conv.message_count} | "
        f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        meta_style
    ))
    elements.append(Spacer(1, 6))

    for msg in (conv.messages or []):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        ts = msg.get("timestamp", "")

        label = "CUSTOMER" if role == "user" else "AI ASSISTANT"
        time_str = f" — {ts}" if ts else ""
        elements.append(Paragraph(f"{label}{time_str}", label_style))

        safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        style = user_style if role == "user" else ai_style
        elements.append(Paragraph(safe_content, style))

    doc.build(elements)
    buffer.seek(0)

    filename = f"conversation_{conv.sender_id[:8]}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

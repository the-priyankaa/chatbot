from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from ..models import Conversation, Feedback, Message, User
from ..schemas.knowledge import FeedbackCreate
from ..services.auth import CurrentUser, DbDep

router = APIRouter(tags=["feedback"])


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    message_id: str, payload: FeedbackCreate, user: CurrentUser, db: DbDep
) -> dict:
    msg = await db.get(Message, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")

    conv = await db.get(Conversation, msg.conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")

    if payload.rating not in (1, 2):
        raise HTTPException(status_code=400, detail="Rating must be 1 or 2")

    existing = (
        await db.execute(
            select(Feedback).where(Feedback.message_id == message_id)
        )
    ).scalar_one_or_none()
    if existing:
        existing.rating = payload.rating
        existing.comment = payload.comment
    else:
        db.add(Feedback(message_id=message_id, rating=payload.rating, comment=payload.comment))
    await db.commit()
    return {"status": "ok"}


@router.get("/stats")
async def get_stats(user: CurrentUser, db: DbDep) -> dict:
    conv_count = (
        await db.execute(
            select(func.count(Conversation.id)).where(Conversation.user_id == user.id)
        )
    ).scalar_one()
    msg_count = (
        await db.execute(
            select(func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.user_id == user.id)
        )
    ).scalar_one()
    fb_rows = (
        await db.execute(
            select(Feedback.rating, func.count(Feedback.id))
            .join(Message, Message.id == Feedback.message_id)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.user_id == user.id)
            .group_by(Feedback.rating)
        )
    ).all()
    ratings = {r: c for r, c in fb_rows}
    total_fb = sum(ratings.values())
    satisfaction = (
        round(ratings.get(2, 0) / total_fb * 100, 1) if total_fb else None
    )
    return {
        "conversations": conv_count,
        "messages": msg_count,
        "feedback_count": total_fb,
        "satisfaction_percent": satisfaction,
    }


@router.get("/admin/stats")
async def get_global_stats(user: CurrentUser, db: DbDep) -> dict:
    users = (await db.execute(select(func.count(User.id)))).scalar_one()
    convs = (await db.execute(select(func.count(Conversation.id)))).scalar_one()
    msgs = (await db.execute(select(func.count(Message.id)))).scalar_one()
    return {"users": users, "conversations": convs, "messages": msgs}

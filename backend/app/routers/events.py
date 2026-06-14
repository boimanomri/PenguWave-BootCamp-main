from fastapi import APIRouter, Depends, HTTPException, status

from app.database import events_col
from app.dependencies import get_current_user, validate_api_key
from app.models.event import EventResponse
from app.models.user import UserResponse

router = APIRouter()


@router.get("", response_model=list[EventResponse])
async def get_events(
    _api: None = Depends(validate_api_key),
    _user: UserResponse = Depends(get_current_user),
):
    cursor = events_col().find({}, {"_id": 0}).sort("timestamp", -1)
    return await cursor.to_list(length=None)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    _api: None = Depends(validate_api_key),
    _user: UserResponse = Depends(get_current_user),
):
    event = await events_col().find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event

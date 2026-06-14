from datetime import datetime
from typing import Literal

from pydantic import BaseModel


Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class EventResponse(BaseModel):
    id: str
    timestamp: datetime
    severity: Severity
    title: str
    description: str
    assetHostname: str
    assetIp: str
    sourceIp: str | None = None
    tags: list[str]
    userId: str | None = None

    model_config = {"populate_by_name": True}

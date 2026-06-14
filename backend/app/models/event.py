from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class EventResponse(BaseModel):
    id: str
    timestamp: datetime
    severity: Severity
    title: str
    description: str
    assetHostname: str
    assetIp: str
    sourceIp: str
    tags: list[str]
    userId: str

    model_config = {"populate_by_name": True}

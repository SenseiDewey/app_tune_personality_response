from typing import Literal, Optional

from pydantic import BaseModel, Field


class MemoryCandidate(BaseModel):
    memory_type: Literal["preference", "profile", "project", "fact"]
    text: str = Field(min_length=3)
    importance: int = Field(default=3, ge=1, le=5)


class MemoryDecision(BaseModel):
    should_store: bool
    memory: Optional[MemoryCandidate] = None

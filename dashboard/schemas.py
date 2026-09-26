from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    brief: str = Field(min_length=10, max_length=10000)


class RunResponse(BaseModel):
    id: int
    state: str
    result: dict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

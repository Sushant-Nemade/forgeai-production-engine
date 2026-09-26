from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class FactoryRun(Base):
    __tablename__ = "factory_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    brief: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(32), index=True)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

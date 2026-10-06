from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SensorReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_id: str = Field(min_length=1, max_length=120)
    timestamp: datetime | None = None
    source_type: Literal["sensor", "historical_replay"] = "sensor"
    source_timestamp: datetime | None = None
    values: dict[str, float] = Field(min_length=1, max_length=50)

    @field_validator("sensor_id")
    @classmethod
    def sensor_id_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("sensor_id must not be blank")
        return value

    @field_validator("values")
    @classmethod
    def values_must_be_finite(cls, values: dict[str, float]) -> dict[str, float]:
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError("Readings must be finite numeric values")
        return values

    def observed_at(self) -> datetime:
        value = self.timestamp or datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def source_observed_at(self) -> datetime | None:
        if self.source_timestamp is None:
            return None
        if self.source_timestamp.tzinfo is None:
            return self.source_timestamp.replace(tzinfo=timezone.utc)
        return self.source_timestamp

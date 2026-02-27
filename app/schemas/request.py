"""Экспорт схем, используемых во входных запросах API."""

from __future__ import annotations

from app.schemas.models import CalculateRequest, CrimeIn, PersonIn

__all__ = ["PersonIn", "CrimeIn", "CalculateRequest"]

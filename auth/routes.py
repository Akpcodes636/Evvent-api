"""Backward-compatible router import.

All FastAPI authentication endpoints are defined in :mod:`auth.controller`.
"""

from auth.controller import router

__all__ = ["router"]

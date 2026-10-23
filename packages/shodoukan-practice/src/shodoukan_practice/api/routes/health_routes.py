"""Liveness check for Docker healthchecks and the deploy smoke test."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Answers without touching the database or the identity provider."""
    return {"status": "ok"}

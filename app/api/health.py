from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.connection import open_connection

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Process-level liveness check used by Docker."""
    return {"status": "ok"}


@router.get("/health/ready", response_model=None)
def readiness() -> JSONResponse:
    """Verify the application can open and query its configured data source."""
    try:
        connection = open_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            connection.close()
    except (RuntimeError, OSError):
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )
    return JSONResponse(content={"status": "ready", "database": "ok"})

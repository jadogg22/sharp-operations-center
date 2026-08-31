from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_report_error_handlers
from app.api.router import router
from app.config import get_settings
from app.observability import configure_logging, register_request_logging

configure_logging()
app = FastAPI(title="Sharp Operations Center — Demo", version="1.0.0")
register_request_logging(app)
register_report_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=[
        "Content-Disposition",
        "X-Invoice-Total",
        "X-Invoice-Variance",
        "X-Request-ID",
    ],
)
app.include_router(router)

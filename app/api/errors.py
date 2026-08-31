from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.errors import (
    DataSourceQueryError,
    InvalidReportError,
    ReportNotFoundError,
)


def register_report_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DataSourceQueryError)
    async def data_source_query_error(
        _request: Request, error: DataSourceQueryError
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(error)})

    @app.exception_handler(ReportNotFoundError)
    async def report_not_found(
        _request: Request, error: ReportNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(InvalidReportError)
    async def invalid_report(
        _request: Request, error: InvalidReportError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

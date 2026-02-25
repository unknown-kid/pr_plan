from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500, detail: dict = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}


def setup_exception_handlers(app):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.error(f"AppException: {exc.message}", extra=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "请求数据验证失败", "detail": exc.errors()},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "数据库操作失败", "detail": "系统内部错误，请稍后重试"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "服务器内部错误",
                "detail": str(exc)
                if hasattr(app, "debug") and app.debug
                else "请联系管理员",
            },
        )

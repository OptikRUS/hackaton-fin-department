from src.core.exceptions import BaseExceptionError


class ParentReportNotFoundError(BaseExceptionError):
    detail: str = "PARENT_REPORT_NOT_FOUND"

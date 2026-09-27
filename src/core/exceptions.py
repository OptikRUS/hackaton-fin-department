class BaseExceptionError(Exception):
    detail: str = ""

    def __init__(self, detail: str = "") -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)

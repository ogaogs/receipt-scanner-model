class ErrorResponse(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


# 400系でクライアントに返す
class S3BadRequest(ErrorResponse):
    pass


class S3NotFound(ErrorResponse):
    pass


# 500系でクライアントに返す
class S3Forbidden(ErrorResponse):
    pass


class S3ServiceUnavailable(ErrorResponse):
    pass


class S3InternalServiceError(ErrorResponse):
    pass

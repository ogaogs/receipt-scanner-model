from enum import Enum


class ErrorCode(Enum):
    """エラータイプ：SIZE_ERROR, INVALID_TYPEは400系に含まれるが、細かく分類するために分けている"""

    SIZE_ERROR = "size_error"  # 画像サイズエラー
    INVALID_TYPE = "invalid_type"  # 画像タイプエラー
    CLIENT_ERROR = "client_error"  # 400系
    SERVER_ERROR = "server_error"  # 500系


class CustomHTTPException(Exception):
    """カスタムHTTPException：構造化されたエラーレスポンスを返すため"""

    def __init__(self, http_status_code: int, error_type_code: ErrorCode, message: str):
        self.http_status_code = http_status_code
        self.error_type_code = error_type_code
        self.message = message
        super().__init__(message)


class ContentSizeError(Exception):
    pass


class InvalidContentTypeError(Exception):
    pass


class S3BadRequest(Exception):
    pass


class S3NotFound(Exception):
    pass


# 500系でクライアントに返す
class S3Forbidden(Exception):
    pass


class S3ServiceUnavailable(Exception):
    pass


class S3InternalServerError(Exception):
    pass


class S3UnexpectedError(Exception):
    pass


class OpenAIAuthenticationError(Exception):
    pass


class OpenAIServiceUnavailable(Exception):
    pass


class OpenAIUnexpectedError(Exception):
    pass


class OpenAIResponseFormatError(Exception):
    pass
